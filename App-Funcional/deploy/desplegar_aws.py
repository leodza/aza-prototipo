"""Despliegue del prototipo AZA en AWS Academy Learner Lab (o cualquier cuenta AWS).

Uso:
    python deploy/desplegar_aws.py inventario     # solo lectura: qué hay en la cuenta
    python deploy/desplegar_aws.py crear --si     # crea instancia + security group + llave
    python deploy/desplegar_aws.py estado         # estado de la instancia AZA

Credenciales: se leen de las variables de entorno
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
(el Learner Lab las entrega en «AWS Details → Show»).
"""
from __future__ import annotations

import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")
NOMBRE = "aza-prototipo"
TIPO = os.getenv("AZA_TIPO_INSTANCIA", "t3.micro")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LLAVE = os.path.join(BASE, "deploy", "aza-llave.pem")
SG_NOMBRE = "aza-prototipo-sg"
PUERTOS = [8000, 9001, 8081]          # app, consola MinIO, pgweb


def cliente(servicio):
    return boto3.client(servicio, region_name=REGION)


def quien_soy():
    sts = cliente("sts")
    ident = sts.get_caller_identity()
    print(f"  cuenta : {ident['Account']}")
    print(f"  usuario: {ident['Arn'].split('/')[-1]}")
    return ident


def mi_ip() -> str:
    import urllib.request
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10) as r:
        return r.read().decode().strip()


def inventario():
    print("\n=== INVENTARIO (solo lectura) ===")
    ec2 = cliente("ec2")
    print("\n-- Instancias EC2 --")
    reservas = ec2.describe_instances().get("Reservations", [])
    if not reservas:
        print("  (ninguna)")
    for r in reservas:
        for i in r["Instances"]:
            nombre = next((t["Value"] for t in i.get("Tags", []) if t["Key"] == "Name"), "-")
            print(f"  {i['InstanceId']}  {i['State']['Name']:<10} {i['InstanceType']:<10} "
                  f"{nombre:<22} IP={i.get('PublicIpAddress', '-')}")

    print("\n-- Bases RDS --")
    try:
        for db in cliente("rds").describe_db_instances()["DBInstances"]:
            print(f"  {db['DBInstanceIdentifier']:<24} {db['DBInstanceClass']:<14} "
                  f"{db['Engine']} {db.get('EngineVersion','')} "
                  f"estado={db['DBInstanceStatus']} público={db.get('PubliclyAccessible')}")
    except ClientError as exc:
        print("  (sin permiso o sin bases):", exc.response["Error"]["Code"])

    print("\n-- Buckets S3 --")
    try:
        for b in cliente("s3").list_buckets().get("Buckets", []):
            print(f"  {b['Name']}")
    except ClientError as exc:
        print("  (sin permiso):", exc.response["Error"]["Code"])

    print("\n-- Grupos de seguridad --")
    for sg in ec2.describe_security_groups()["SecurityGroups"]:
        if sg["GroupName"] == "default":
            continue
        print(f"  {sg['GroupId']}  {sg['GroupName']:<28} {sg.get('Description','')[:40]}")


def imagen_ubuntu():
    ec2 = cliente("ec2")
    r = ec2.describe_images(
        Owners=["099720109477"],
        Filters=[{"Name": "name", "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
                 {"Name": "state", "Values": ["available"]}],
    )["Images"]
    if not r:
        raise SystemExit("No se encontró una AMI de Ubuntu 24.04")
    return sorted(r, key=lambda x: x["CreationDate"])[-1]["ImageId"]


def crear():
    ec2 = cliente("ec2")
    print("\n=== CREANDO RECURSOS ===")

    # 1) Llave SSH
    if os.path.exists(LLAVE):
        print(f"  llave: ya existe {LLAVE}")
        nombre_llave = "aza-llave"
    else:
        nombre_llave = "aza-llave"
        try:
            kp = ec2.create_key_pair(KeyName=nombre_llave)
            os.makedirs(os.path.dirname(LLAVE), exist_ok=True)
            with open(LLAVE, "w", encoding="utf-8") as fh:
                fh.write(kp["KeyMaterial"])
            os.chmod(LLAVE, 0o600)
            print(f"  llave: creada y guardada en {LLAVE}")
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "InvalidKeyPair.Duplicate":
                raise SystemExit("La llave 'aza-llave' ya existe en AWS pero no localmente. "
                                 "Bórrala en la consola o cambia el nombre en el script.")
            raise

    # 2) Red por defecto
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        raise SystemExit("No hay VPC por defecto en esta cuenta/región")
    vpc_id = vpcs[0]["VpcId"]
    subredes = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    subred = subredes[0]["SubnetId"]
    print(f"  red: VPC {vpc_id} · subred {subred}")

    # 3) Security group
    ip = mi_ip()
    print(f"  mi IP pública: {ip}")
    try:
        sg = ec2.create_security_group(
            GroupName=SG_NOMBRE, Description="AZA prototipo: app, MinIO y pgweb",
            VpcId=vpc_id)["GroupId"]
        print(f"  security group: {sg} creado")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "InvalidGroup.Duplicate":
            raise
        sg = ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [SG_NOMBRE]}])["SecurityGroups"][0]["GroupId"]
        print(f"  security group: {sg} ya existía")

    permisos = [{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": f"{ip}/32"}]}]
    for p in PUERTOS:
        permisos.append({"IpProtocol": "tcp", "FromPort": p, "ToPort": p,
                         "IpRanges": [{"CidrIp": "0.0.0.0/0"}]})
    try:
        ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=permisos)
        print(f"  puertos abiertos: 22 (solo {ip}), {', '.join(map(str, PUERTOS))}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
            raise
        print("  puertos: ya estaban abiertos")

    # 4) Instancia
    ami = imagen_ubuntu()
    with open(os.path.join(BASE, "deploy", "user-data.sh"), encoding="utf-8") as fh:
        user_data = fh.read()
    print(f"  AMI: {ami} · tipo: {TIPO}")
    inst = ec2.run_instances(
        ImageId=ami, InstanceType=TIPO, MinCount=1, MaxCount=1,
        KeyName=nombre_llave, UserData=user_data,
        NetworkInterfaces=[{"DeviceIndex": 0, "AssociatePublicIpAddress": True,
                            "SubnetId": subred, "Groups": [sg]}],
        TagSpecifications=[{"ResourceType": "instance",
                            "Tags": [{"Key": "Name", "Value": NOMBRE},
                                     {"Key": "Proyecto", "Value": "Aceros AZA - ES3"}]}],
    )["Instances"][0]
    iid = inst["InstanceId"]
    print(f"  instancia: {iid} creada · esperando a que esté disponible…")

    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    datos = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
    ip_pub = datos.get("PublicIpAddress")
    print(f"\n=== LISTO ===")
    print(f"  ID        : {iid}")
    print(f"  IP pública: {ip_pub}")
    print(f"  SSH       : ssh -i {LLAVE} ubuntu@{ip_pub}")
    print("\n  (la instalación de Docker tarda 2-3 minutos después del arranque)")
    with open(os.path.join(BASE, "deploy", "instancia.json"), "w", encoding="utf-8") as fh:
        json.dump({"instance_id": iid, "ip": ip_pub, "key": LLAVE, "sg": sg}, fh, indent=2)


def estado():
    ec2 = cliente("ec2")
    r = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [NOMBRE]}])
    for res in r.get("Reservations", []):
        for i in res["Instances"]:
            print(f"  {i['InstanceId']} {i['State']['Name']} IP={i.get('PublicIpAddress','-')}")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "inventario"
    try:
        print("Conectando con AWS…")
        quien_soy()
    except Exception as exc:
        raise SystemExit(f"No se pudo autenticar: {exc}")
    if accion == "inventario":
        inventario()
    elif accion == "crear":
        if "--si" not in sys.argv:
            inventario()
            print("\nSe crearían: llave SSH, security group y una instancia "
                  f"{TIPO}. Volvé a ejecutar con --si para confirmar.")
        else:
            crear()
    elif accion == "estado":
        estado()
    else:
        print(__doc__)
