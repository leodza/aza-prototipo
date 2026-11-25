# -*- coding: utf-8 -*-
"""Agrega historial de demostración repartido en 12 semanas, sin borrar datos.

No elimina nada: sólo inserta registros si todavía no hay historial antiguo.
Uso:  python herramientas/sembrar_historico.py [--dias 84] [--registros 140]
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app import db


def main(dias: int = 84, registros: int = 140) -> int:
    with db.SesionLocal() as s:
        recetas = s.scalars(select(db.Receta)).all()
        lotes = s.scalars(select(db.Lote)).all()
        usuarios = s.scalars(select(db.Usuario)).all()
        if not recetas or not lotes or not usuarios:
            print("La base no está sembrada: ejecutá la app una vez.")
            return 1

        limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dias)
        ya_hay = s.scalar(select(func.count()).select_from(db.Inspeccion)
                          .where(db.Inspeccion.fecha_hora < limite)) or 0
        if ya_hay > 10:
            print(f"Ya existen {ya_hay} registros anteriores a {dias} días: no se agrega nada.")
            return 0

        azar = random.Random(7)
        creados = 0
        for _ in range(registros):
            lote = azar.choice(lotes)
            rec = s.get(db.Receta, lote.receta_id) or azar.choice(recetas)
            batch = s.scalar(select(db.Batch).where(db.Batch.lote_id == lote.id))
            minimo, maximo = float(rec.min_tol), float(rec.max_tol)
            centro = (minimo + maximo) / 2
            azar_pct = azar.random()
            if azar_pct < 0.14:
                angulo = round(azar.uniform(max(0, minimo - 15), minimo - 1), 1)
            elif azar_pct < 0.22:
                angulo = None
            else:
                angulo = round(min(180, max(1, azar.gauss(centro, (maximo - minimo) / 5))), 2)
            if angulo is None:
                estado = "sin_receta"
            elif minimo <= angulo <= maximo:
                estado = "aprobado"
            else:
                estado = "rechazado"
            fecha = (datetime.now(timezone.utc).replace(tzinfo=None)
                     - timedelta(days=azar.randint(1, dias),
                                 minutes=azar.randint(0, 900)))
            insp = db.Inspeccion(
                fecha_hora=fecha, receta_id=rec.id, lote_id=lote.id,
                batch_id=batch.id if batch else None,
                operador_id=azar.choice(usuarios).id, material=rec.materialidad,
                angulo=angulo, limite_min=minimo, limite_max=maximo, estado=estado,
                origen="historico_demo", confianza="ALTA",
                duracion_ms=azar.randint(1500, 2600))
            s.add(insp)
            s.flush()
            if estado == "rechazado":
                s.add(db.Alarma(inspeccion_id=insp.id, tipo="fuera_tolerancia",
                                severidad="alta",
                                mensaje=f"Ángulo {angulo}° fuera del rango "
                                        f"{minimo}–{maximo}°",
                                creada_en=fecha))
            creados += 1
        s.commit()
    print(f"Listo: {creados} inspecciones históricas en {dias} días.")
    return 0


if __name__ == "__main__":
    dias = 84
    registros = 140
    args = sys.argv[1:]
    if "--dias" in args:
        dias = int(args[args.index("--dias") + 1])
    if "--registros" in args:
        registros = int(args[args.index("--registros") + 1])
    raise SystemExit(main(dias, registros))
