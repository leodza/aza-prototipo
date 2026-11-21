#!/usr/bin/env python3
"""Diagnostico simple de Line0 sin video ni captura."""

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


def read_line_status(cam) -> bool:
    try:
        return bool(cam.f.LineStatus.Get())
    except Exception:
        return bool(cam.f.LineStatus.value)


def set_string(feature, value: str) -> None:
    if hasattr(feature, "SetString"):
        feature.SetString(value)
    else:
        feature.Set(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitorea Line0 y cuenta flancos.")
    parser.add_argument("--duration", type=float, default=90.0, help="Segundos de monitoreo")
    parser.add_argument("--interval", type=float, default=0.005, help="Periodo de polling")
    parser.add_argument("--device", default=None, help="Device ID/IP opcional")
    parser.add_argument("--line", default="Line0", help="Linea a monitorear, por ejemplo Line0")
    args = parser.parse_args()

    cam = neoapi.Cam()
    try:
        print("Conectando camara...")
        if args.device:
            cam.Connect(args.device)
        else:
            cam.Connect()
        print("Camara conectada")

        try:
            cam.f.AcquisitionStop.Execute()
        except Exception:
            pass
        if hasattr(cam.f, "SequencerMode"):
            try:
                set_string(cam.f.SequencerMode, "Off")
            except Exception:
                pass
        if hasattr(cam.f, "SequencerConfigurationMode"):
            try:
                set_string(cam.f.SequencerConfigurationMode, "Off")
            except Exception:
                pass
        if hasattr(cam.f, "TriggerMode"):
            try:
                set_string(cam.f.TriggerMode, "Off")
            except Exception:
                pass

        cam.f.LineSelector.SetString(args.line)
        if hasattr(cam.f, "LineMode"):
            try:
                set_string(cam.f.LineMode, "Input")
            except Exception:
                pass
        if hasattr(cam.f, "LineInverter"):
            try:
                cam.f.LineInverter.Set(False)
            except Exception:
                try:
                    cam.f.LineInverter.value = False
                except Exception:
                    pass

        previous = read_line_status(cam)
        rising = 0
        falling = 0
        start = time.monotonic()
        print(f"{args.line} inicial: {'ALTA' if previous else 'BAJA'}", flush=True)
        print(f"Monitoreando {args.duration:.1f}s. Active el sensor durante esta ventana.")

        while time.monotonic() - start < args.duration:
            current = read_line_status(cam)
            if current != previous:
                elapsed = time.monotonic() - start
                if current:
                    rising += 1
                    edge = "SUBIDA"
                else:
                    falling += 1
                    edge = "BAJADA"
                print(
                    f"{elapsed:8.3f}s | {args.line} {'ALTA' if current else 'BAJA'} | "
                    f"flanco {edge} | subidas={rising} bajadas={falling}",
                    flush=True,
                )
                previous = current
            time.sleep(args.interval)

        print(
            f"Resumen: subidas={rising}, bajadas={falling}, "
            f"estado_final={'ALTA' if previous else 'BAJA'}"
        )
        return 0
    finally:
        try:
            cam.Disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
