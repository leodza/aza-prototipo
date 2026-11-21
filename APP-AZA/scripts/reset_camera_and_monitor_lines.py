#!/usr/bin/env python3
"""Reset suave de camara y monitoreo de LineStatus."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import GENTL_DIR_DEFAULT
from scripts.monitor_camera_lines import read_line, set_string

os.environ.setdefault("GENICAM_GENTL64_PATH", GENTL_DIR_DEFAULT)

try:
    import neoapi
except ImportError as exc:
    raise SystemExit("neoapi no esta instalado en este entorno") from exc


def connect(device: str | None):
    cam = neoapi.Cam()
    if device:
        cam.Connect(device)
    else:
        cam.Connect()
    return cam


def soft_cleanup(cam) -> None:
    try:
        cam.f.AcquisitionStop.Execute()
    except Exception:
        pass
    if hasattr(cam.f, "SequencerMode"):
        set_string(cam.f.SequencerMode, "Off")
    if hasattr(cam.f, "SequencerConfigurationMode"):
        set_string(cam.f.SequencerConfigurationMode, "Off")
    if hasattr(cam.f, "TriggerMode"):
        set_string(cam.f.TriggerMode, "Off")


def try_device_reset(cam) -> bool:
    reset = getattr(cam.f, "DeviceReset", None)
    if reset is None:
        print("DeviceReset no esta disponible.", flush=True)
        return False
    try:
        print("Ejecutando DeviceReset...", flush=True)
        reset.Execute()
        return True
    except Exception as exc:
        print(f"DeviceReset fallo/no permitido: {exc}", flush=True)
        return False


def monitor(cam, lines: list[str], duration: float, interval: float) -> None:
    states = {}
    available = []
    for line in lines:
        info = read_line(cam, line)
        if info is None:
            print(f"{line}: no disponible", flush=True)
            continue
        available.append(line)
        states[line] = info["status"]
        print(
            f"{line}: {'ALTA' if info['status'] else 'BAJA'} | "
            f"Mode={info['mode']} | Inverter={info['inverter']}",
            flush=True,
        )

    rising = {line: 0 for line in available}
    falling = {line: 0 for line in available}
    start = time.monotonic()
    print(f"Monitoreando {', '.join(available)} durante {duration:.1f}s...", flush=True)
    while time.monotonic() - start < duration:
        elapsed = time.monotonic() - start
        for line in available:
            info = read_line(cam, line)
            if info is None:
                continue
            current = info["status"]
            if current == states[line]:
                continue
            if current:
                rising[line] += 1
                edge = "SUBIDA"
            else:
                falling[line] += 1
                edge = "BAJADA"
            states[line] = current
            print(
                f"{elapsed:8.3f}s | {line} {'ALTA' if current else 'BAJA'} | "
                f"flanco {edge} | subidas={rising[line]} bajadas={falling[line]}",
                flush=True,
            )
        time.sleep(interval)

    print("Resumen:", flush=True)
    for line in available:
        print(
            f"{line}: subidas={rising[line]} bajadas={falling[line]} "
            f"estado_final={'ALTA' if states[line] else 'BAJA'}",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset suave de camara y monitor de Line0/Line1.")
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=0.01)
    parser.add_argument("--device", default=None)
    parser.add_argument("--device-reset", action="store_true", help="Intentar DeviceReset antes de reconectar")
    parser.add_argument("--lines", nargs="*", default=["Line0", "Line1"])
    args = parser.parse_args()

    cam = None
    try:
        print("Conectando camara...", flush=True)
        cam = connect(args.device)
        print("Camara conectada.", flush=True)
        soft_cleanup(cam)

        if args.device_reset:
            did_reset = try_device_reset(cam)
            try:
                cam.Disconnect()
            except Exception:
                pass
            cam = None
            wait_s = 10.0 if did_reset else 2.0
            print(f"Esperando {wait_s:.0f}s antes de reconectar...", flush=True)
            time.sleep(wait_s)

        if cam is None:
            print("Reconectando camara...", flush=True)
            cam = connect(args.device)
            print("Camara reconectada.", flush=True)
            soft_cleanup(cam)

        monitor(cam, args.lines, args.duration, args.interval)
        return 0
    finally:
        if cam is not None:
            try:
                cam.Disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
