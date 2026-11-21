# ui/users.py — Gestión de usuarios
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QDialog, QLabel, QLineEdit, QFormLayout
)
from PySide6.QtCore import Qt

from src.database.auth import (
    listar_usuarios, crear_usuario, set_usuario_activo, reset_pin, es_admin, borrar_usuario
)


class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear usuario")
        self.setModal(True)
        self.username = None
        self.pin = None

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.in_user = QLineEdit()
        self.in_pin = QLineEdit()
        self.in_pin.setEchoMode(QLineEdit.Password)
        form.addRow(QLabel("Usuario:"), self.in_user)
        form.addRow(QLabel("PIN:"), self.in_pin)
        lay.addLayout(form)

        btns = QHBoxLayout()
        b_ok = QPushButton("Crear")
        b_cancel = QPushButton("Cancelar")
        b_ok.clicked.connect(self._ok)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        self.setFixedWidth(360)

    def _ok(self):
        u = self.in_user.text().strip()
        p = self.in_pin.text().strip()
        if not u or not p:
            QMessageBox.warning(self, "Error", "Usuario y PIN son obligatorios.")
            return
        self.username = u
        self.pin = p
        self.accept()


class ResetPinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset PIN")
        self.setModal(True)
        self.pin = None

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Nuevo PIN:"))
        self.in_pin = QLineEdit()
        self.in_pin.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.in_pin)

        btns = QHBoxLayout()
        b_ok = QPushButton("Guardar")
        b_cancel = QPushButton("Cancelar")
        b_ok.clicked.connect(self._ok)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        self.setFixedWidth(320)

    def _ok(self):
        p = self.in_pin.text().strip()
        if not p:
            QMessageBox.warning(self, "Error", "PIN no puede ser vacío.")
            return
        self.pin = p
        self.accept()


class UsersWindow(QMainWindow):
    def __init__(self, operador_actual: str):
        super().__init__()
        self.operador_actual = operador_actual
        self._is_admin = es_admin(self.operador_actual)
        self.setWindowTitle("Usuarios")
        self.resize(720, 420)
        self.setStyleSheet("background-color: #121212; color: white;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Usuario", "Activo", "Admin"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setStyleSheet("QTableWidget { background-color: #1E1E1E; gridline-color: #333; }")
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabla)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_create = QPushButton("Crear usuario")
        self.btn_toggle = QPushButton("Activar/Desactivar")
        self.btn_reset = QPushButton("Reset PIN")
        self.btn_delete = QPushButton(" Borrar usuario")

        for b in (self.btn_refresh, self.btn_create, self.btn_toggle, self.btn_reset, self.btn_delete):
            b.setStyleSheet("background-color:#4CAF50; padding: 10px; font-weight: bold; border-radius: 6px;")

        self.btn_toggle.setStyleSheet("background-color:#1565C0; padding: 10px; font-weight: bold; border-radius: 6px;")
        self.btn_reset.setStyleSheet("background-color:#6A1B9A; padding: 10px; font-weight: bold; border-radius: 6px;")
        self.btn_delete.setStyleSheet("background-color:#C62828; padding: 10px; font-weight: bold; border-radius: 6px;")

        self.btn_refresh.clicked.connect(self.cargar)
        self.btn_create.clicked.connect(self.crear)
        self.btn_toggle.clicked.connect(self.toggle_activo)
        self.btn_reset.clicked.connect(self.resetear_pin)
        self.btn_delete.clicked.connect(self.borrar)

        btns.addWidget(self.btn_refresh)
        btns.addWidget(self.btn_create)
        btns.addWidget(self.btn_toggle)
        btns.addWidget(self.btn_reset)
        btns.addWidget(self.btn_delete)
        btns.addStretch()
        layout.addLayout(btns)

        if not self._is_admin:
            self.btn_toggle.setEnabled(False)
            self.btn_reset.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_toggle.setToolTip("Solo admin puede activar/desactivar usuarios.")
            self.btn_reset.setToolTip("Solo admin puede resetear PIN.")
            self.btn_delete.setToolTip("Solo admin puede borrar usuarios.")

        self.cargar()

    def _selected_user(self):
        row = self.tabla.currentRow()
        if row < 0:
            return None
        user_id = int(self.tabla.item(row, 0).text())
        username = self.tabla.item(row, 1).text()
        activo = self.tabla.item(row, 2).text().strip() == "1"
        is_admin = self.tabla.item(row, 3).text().strip() == "1"
        return user_id, username, activo, is_admin

    def cargar(self):
        data = listar_usuarios()
        self.tabla.setRowCount(len(data))
        for i, (uid, uname, activo, is_admin) in enumerate(data):
            it0 = QTableWidgetItem(str(uid))
            it1 = QTableWidgetItem(uname)
            it2 = QTableWidgetItem(str(int(activo)))
            it3 = QTableWidgetItem(str(int(is_admin)))
            it0.setForeground(Qt.white)
            it1.setForeground(Qt.white)
            it2.setForeground(Qt.green if int(activo) == 1 else Qt.red)
            it3.setForeground(Qt.yellow if int(is_admin) == 1 else Qt.white)
            self.tabla.setItem(i, 0, it0)
            self.tabla.setItem(i, 1, it1)
            self.tabla.setItem(i, 2, it2)
            self.tabla.setItem(i, 3, it3)

    def crear(self):
        dlg = CreateUserDialog(self)
        if not dlg.exec():
            return
        try:
            crear_usuario(dlg.username, dlg.pin)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo crear usuario:\n{e}")
            return
        self.cargar()

    def toggle_activo(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo el admin puede realizar esta accion.")
            return
        sel = self._selected_user()
        if not sel:
            QMessageBox.information(self, "Info", "Selecciona un usuario.")
            return
        uid, uname, activo, _is_admin = sel
        nuevo = not activo
        try:
            set_usuario_activo(uid, nuevo)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo actualizar:\n{e}")
            return
        self.cargar()

    def resetear_pin(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo el admin puede realizar esta accion.")
            return
        sel = self._selected_user()
        if not sel:
            QMessageBox.information(self, "Info", "Selecciona un usuario.")
            return
        uid, uname, _activo, _is_admin = sel
        dlg = ResetPinDialog(self)
        if not dlg.exec():
            return
        try:
            reset_pin(uid, dlg.pin)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo resetear PIN:\n{e}")
            return
        QMessageBox.information(self, "OK", f"PIN actualizado para {uname}.")

    def borrar(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo el admin puede borrar usuarios.")
            return
        sel = self._selected_user()
        if not sel:
            QMessageBox.information(self, "Info", "Selecciona un usuario.")
            return
        uid, uname, _activo, is_admin = sel
        if uname.strip() == self.operador_actual.strip():
            QMessageBox.warning(self, "Error", "No puedes borrarte a ti mismo (sesion actual).")
            return
        if is_admin:
            QMessageBox.warning(self, "Error", "No se permite borrar un usuario admin.")
            return
        resp = QMessageBox.question(
            self, "Confirmar borrado",
            f"¿Seguro que quieres borrar el usuario '{uname}'?\n\nEsta accion no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return
        try:
            borrar_usuario(uid)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo borrar:\n{e}")
            return
        QMessageBox.information(self, "OK", f"Usuario '{uname}' borrado.")
        self.cargar()
