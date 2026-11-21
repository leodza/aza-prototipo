# ui/login.py — Dialogo de login
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit,
    QPushButton, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut

from src.database.auth import validar_login, listar_usuarios_activos
from src.utils import resource_path


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.operador = None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: #121212; color: white;")

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)
        root.addStretch(1)

        card = QWidget()
        card.setFixedWidth(420)
        card.setStyleSheet("QWidget { background-color: #1E1E1E; border-radius: 12px; }")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        logo = QLabel(alignment=Qt.AlignCenter)
        logo_path = resource_path(os.path.join("assets", "logo.png"))
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo.setPixmap(pix.scaled(260, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        card_layout.addWidget(logo)

        title = QLabel("Ingreso Operador", alignment=Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4CAF50;")
        card_layout.addWidget(title)

        lbl_user = QLabel("Operador:")
        lbl_user.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(lbl_user)

        self.cmb = QComboBox()
        self.cmb.addItems(listar_usuarios_activos())
        self.cmb.setStyleSheet("QComboBox { background: #2E7D32; color: white; padding: 8px; border-radius: 6px; }")
        card_layout.addWidget(self.cmb)

        lbl_pin = QLabel("PIN:")
        lbl_pin.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(lbl_pin)

        self.pin = QLineEdit()
        self.pin.setEchoMode(QLineEdit.Password)
        self.pin.setPlaceholderText("Ingrese PIN")
        self.pin.setStyleSheet("QLineEdit { background: #2E2E2E; color: white; padding: 8px; border-radius: 6px; }")
        self.pin.returnPressed.connect(self._do_login)
        card_layout.addWidget(self.pin)

        btn_row = QHBoxLayout()
        btn_exit = QPushButton("Salir")
        btn_exit.setStyleSheet("QPushButton { background-color: #C62828; color: white; padding: 10px; border-radius: 6px; font-weight: bold; }")
        btn_exit.clicked.connect(self.reject)

        btn_minimize = QPushButton("Minimizar")
        btn_minimize.setStyleSheet(
            "QPushButton { background-color: #424242; color: white; padding: 10px; "
            "border-radius: 6px; font-weight: bold; }"
            "QPushButton:hover { background-color: #616161; }"
        )
        btn_minimize.clicked.connect(self.minimizar_ventana)

        btn_login = QPushButton("Ingresar")
        btn_login.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        btn_login.clicked.connect(self._do_login)

        btn_row.addWidget(btn_exit)
        btn_row.addStretch()
        btn_row.addWidget(btn_minimize)
        btn_row.addWidget(btn_login)
        card_layout.addLayout(btn_row)

        center_row = QHBoxLayout()
        center_row.addStretch()
        center_row.addWidget(card)
        center_row.addStretch()
        root.addLayout(center_row)
        root.addStretch(1)

        self.shortcut_minimize = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_minimize.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_minimize.activated.connect(self.minimizar_ventana)

    def minimizar_ventana(self):
        if self.isMinimized():
            return

        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
            self.showNormal()

        QTimer.singleShot(120, self._aplicar_minimizado)

    def _aplicar_minimizado(self):
        self.setWindowState(Qt.WindowState.WindowMinimized)
        self.showMinimized()

    def _do_login(self):
        user = self.cmb.currentText().strip()
        pin = self.pin.text().strip()

        if not user or not pin:
            QMessageBox.warning(self, "Error", "Ingrese usuario y PIN.")
            return

        if validar_login(user, pin):
            self.operador = user
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "PIN incorrecto.")
            self.pin.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
