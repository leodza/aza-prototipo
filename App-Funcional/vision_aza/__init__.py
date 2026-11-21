"""Copia del pipeline de visión de la app de planta (APP-AZA), para que el
contenedor sea autocontenido. El original vive en APP-AZA/src/vision/."""
from .sequence_analysis import analyze_sequence  # noqa: F401
