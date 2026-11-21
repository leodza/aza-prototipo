import numpy as np
from src.vision.detection import calcular_angulo


def test_calcular_angulo_derecha():
    assert calcular_angulo(0, 0, 10, 0) == 0.0


def test_calcular_angulo_arriba():
    assert calcular_angulo(0, 0, 0, 10) == 270.0


def test_calcular_angulo_izquierda():
    assert calcular_angulo(0, 0, -10, 0) == 180.0


def test_calcular_angulo_abajo():
    assert calcular_angulo(0, 0, 0, -10) == 90.0


def test_calcular_angulo_centro_desplazado():
    ang = calcular_angulo(50, 50, 60, 50)
    assert ang == 0.0


def test_calcular_angulo_rango_0_360():
    for px in [-10, 0, 10]:
        for py in [-10, 0, 10]:
            if px == 0 and py == 0:
                continue
            ang = calcular_angulo(0, 0, px, py)
            assert 0 <= ang < 360
