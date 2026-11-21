# ui/dashboard.py — Panel de control de calidad
import sqlite3
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
)
from PySide6.QtCore import Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from src.core.config import DB_PATH

logger = logging.getLogger(__name__)


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(" Panel de Control de Calidad")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #121212; color: white;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.figure, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.figure.patch.set_facecolor("#1E1E1E")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha", "Operador", "Receta", "Lote", "angulo (deg)", "Estado"]
        )
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setStyleSheet(
            "QTableWidget { background-color: #1E1E1E; gridline-color: #333; }"
        )
        layout.addWidget(self.tabla)

        btns_layout = QHBoxLayout()
        btn_refresh = QPushButton(" ACTUALIZAR DATOS")
        btn_refresh.setStyleSheet("background-color: #4CAF50; padding: 10px; font-weight: bold;")
        btn_refresh.clicked.connect(self.cargar_datos)
        btns_layout.addWidget(btn_refresh)
        layout.addLayout(btns_layout)

        self.cargar_datos()

    def cargar_datos(self):
        logger.debug("DB PATH (dashboard.py) = %s", DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT fecha, operador, receta, lote, angulo, estado
            FROM registros
            ORDER BY id DESC
            LIMIT 20
        """)
        datos = cursor.fetchall()

        self.tabla.setRowCount(len(datos))

        angulos = []
        for i, fila in enumerate(datos):
            for j, valor in enumerate(fila):
                item = QTableWidgetItem("" if valor is None else str(valor))

                if j == 5:
                    if valor == "RECHAZADO":
                        item.setForeground(Qt.red)
                    elif valor == "APROBADO":
                        item.setForeground(Qt.green)
                    else:
                        item.setForeground(Qt.white)
                else:
                    item.setForeground(Qt.white)

                self.tabla.setItem(i, j, item)

            angulos.append(fila[4] if fila[4] is not None else 0.0)

        recetas_unicas = list(dict.fromkeys(f[2] for f in datos if f[2]))
        min_tol, max_tol = None, None
        if recetas_unicas:
            cursor.execute(
                "SELECT min_tol, max_tol FROM configuracion_recetas WHERE nombre = ?",
                (recetas_unicas[0],)
            )
            tol_row = cursor.fetchone()
            if tol_row:
                min_tol, max_tol = tol_row

        conn.close()

        self.ax.clear()
        self.ax.set_facecolor("#1E1E1E")
        rev_angulos = list(reversed(angulos))
        self.ax.plot(rev_angulos, marker="o", linestyle="-", linewidth=2)

        if min_tol is not None:
            self.ax.axhline(min_tol, color="orange", linestyle="--", linewidth=1.5, label=f"Min: {min_tol}")
        if max_tol is not None:
            self.ax.axhline(max_tol, color="red", linestyle="--", linewidth=1.5, label=f"Max: {max_tol}")
        if min_tol is not None or max_tol is not None:
            self.ax.legend(facecolor="#1E1E1E", edgecolor="white", labelcolor="white")

        self.ax.set_title("TENDENCIA DE ÁNGULOS (Ultimos registros)", color="white")
        self.ax.tick_params(colors="white")
        self.ax.yaxis.label.set_color("white")
        self.ax.xaxis.label.set_color("white")
        self.figure.tight_layout()
        self.canvas.draw()
