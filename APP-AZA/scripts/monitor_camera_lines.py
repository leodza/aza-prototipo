#!/usr/bin/env python3
"""Monitorea LineStatus en varias lineas de la camara, sin video."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import GENTL_DIR_DEFAULT

os.environ.setdefault("GENICAM_GENTL64_PATH", GENTL_DIR_DEFAULT)

try:
    import neoapi
except ImportError as exc:
    raise SystemExit("neoapi no esta instalado en este entorno") from exc


DEFAULT_LINES = ("Line0", "Line1", "Line2", "Line3")


def set_string(feature, value: str) -> bool:
    try:
        if hasattr(feature, "SetString"):
            feature.SetString(value)
        else:
            feature.Set(value)
        return True
    except Exception:
        return False


def read_text(feature) -> str:
    try:
        if hasattr(feature, "GetString"):
            return str(feature.GetString())
        if hasattr(feature, "Get"):
            return str(feature.Get())
        return str(feature.value)
    except Exception:
        return "N/A"


def read_bool(feature) -> bool:
    try:
        if hasattr(feature, "Get"):
            return bool(feature.Get())
        return bool(feature.value)
    except Exception:
        return False


def read_line(cam, line: str):
    if not set_string(cam.f.LineSelector, line):
        return None
    return {
        "status": read_bool(cam.f.LineStatus),
        "mode": read_text(getattr(cam.f, "LineMode", None)),
        "inverter": read_text(getattr(cam.f, "LineInverter", None)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitorea LineStatus en todas las lineas disponibles.")
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--interval", type=float, default=0.01)
    parser.add_argument("--device", default=None)
    parser.add_argument("--lines", nargs="*", default=list(DEFAULT_LINES))
    args = parser.parse_args()

    cam = neoapi.Cam()
    try:
        print("Conectando camara...", flush=True)
        if args.device:
            cam.Connect(args.device)
        else:
            cam.Connect()
        print("Camara conectada", flush=True)

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

        available = []
        states = {}
        for line in args.lines:
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

        if not available:
            print("No se pudo leer ninguna linea.", flush=True)
            return 2

        rising = {line: 0 for line in available}
        falling = {line: 0 for line in available}
        start = time.monotonic()
        print(f"Monitoreando {', '.join(available)} durante {args.duration:.1f}s...", flush=True)

        while time.monotonic() - start < args.duration:
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
            time.sleep(args.interval)

        print("Resumen:", flush=True)
        for line in available:
            print(
                f"{line}: subidas={rising[line]} bajadas={falling[line]} "
                f"estado_final={'ALTA' if states[line] else 'BAJA'}",
                flush=True,
            )
        return 0
    finally:
        try:
            cam.Disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
