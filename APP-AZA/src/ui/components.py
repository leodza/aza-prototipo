# ui/components.py — HMIOverlay, ResultViewer, WelcomeScreen
import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QMainWindow, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect

from src.utils import resource_path


class HMIOverlay(QWidget):
    confirmed = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setVisible(False)

        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(180)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setAlignment(Qt.AlignCenter)

        self.panel = QWidget()
        self.panel.setStyleSheet("background-color: rgb(40,40,40); border-radius: 24px;")
        self.panel.setMinimumWidth(1000)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(50, 50, 50, 50)
        panel_layout.setSpacing(20)
        panel_layout.setAlignment(Qt.AlignCenter)

        self.lbl_status = QLabel("", alignment=Qt.AlignCenter)
        f1 = QFont()
        f1.setPointSize(64)
        f1.setBold(True)
        self.lbl_status.setFont(f1)

        self.lbl_angle = QLabel("--.-°", alignment=Qt.AlignCenter)
        fA = QFont()
        fA.setPointSize(150)
        fA.setBold(True)
        self.lbl_angle.setFont(fA)

        self.lbl_instr = QLabel("", alignment=Qt.AlignCenter)
        f2 = QFont()
        f2.setPointSize(34)
        f2.setBold(True)
        self.lbl_instr.setFont(f2)

        self.lbl_meta = QLabel("", alignment=Qt.AlignCenter)
        f3 = QFont()
        f3.setPointSize(18)
        self.lbl_meta.setFont(f3)

        panel_layout.addWidget(self.lbl_status)
        panel_layout.addWidget(self.lbl_angle)
        panel_layout.addWidget(self.lbl_instr)
        panel_layout.addWidget(self.lbl_meta)

        row = QHBoxLayout()
        self.btn_close = QPushButton("Cerrar")
        self.btn_view = QPushButton("Ver analisis")
        self.btn_close.setFixedHeight(56)
        self.btn_view.setFixedHeight(56)
        self.btn_close.setStyleSheet("background:#333; color:white; font-weight:bold; border-radius:10px; padding:12px 22px;")
        self.btn_view.setStyleSheet("background:#000; color:white; font-weight:bold; border-radius:10px; padding:12px 22px;")
        self.btn_close.clicked.connect(self._on_close)
        self.btn_view.clicked.connect(self._on_view)
        row.addWidget(self.btn_close)
        row.addSpacing(20)
        row.addWidget(self.btn_view)
        panel_layout.addLayout(row)
        root.addWidget(self.panel)

    def resize_to_parent(self):
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())

    def show_result(self, ok: bool, instr: str, meta: str = "", angle=None):
        self.setStyleSheet("background-color: rgba(0,0,0,220);")
        if ok:
            self.panel.setStyleSheet("background-color: rgb(0,120,0); border-radius: 24px;")
            self.lbl_status.setText("APROBADO")
            self.lbl_angle.setStyleSheet("color: white;")
        else:
            self.panel.setStyleSheet("background-color: rgb(160,0,0); border-radius: 24px;")
            self.lbl_status.setText("RECHAZADO")
            self.lbl_angle.setStyleSheet("color: yellow;")

        self.lbl_angle.setText("--.-°" if angle is None else f"{float(angle):.2f}°")
        self.lbl_instr.setText(instr)
        self.lbl_meta.setText(meta)

        self.resize_to_parent()
        self.setWindowOpacity(0.0)
        self.setVisible(True)
        self.raise_()
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def _on_view(self):
        self.setVisible(False)
        self.confirmed.emit()

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._on_view()
        elif event.key() == Qt.Key_Escape:
            self._on_close()


class ResultViewer(QMainWindow):
    def __init__(self, images, start_index=None):
        super().__init__()
        self.images = [self._normalize_item(item) for item in images]
        self.idx = (
            max(0, min(int(start_index), len(images) - 1))
            if start_index is not None and images
            else max(0, len(images) - 1)
        )
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        btn_prev = QPushButton("<")
        btn_next = QPushButton(">")
        for button in (btn_prev, btn_next):
            button.setFixedWidth(76)
            button.setStyleSheet(
                "background-color:#1B5E20; color:white; border:none; "
                "font-size:42px; font-weight:bold;"
            )
        btn_prev.clicked.connect(self.prev)
        btn_next.clicked.connect(self.next)

        image_area = QWidget()
        image_layout = QHBoxLayout(image_area)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        self.label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        for label in (self.label, self.frame_label):
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            label.setStyleSheet("background-color: black;")
        image_layout.addWidget(self.label, 1)
        image_layout.addWidget(self.frame_label, 1)

        body.addWidget(btn_prev)
        body.addWidget(image_area, 1)
        body.addWidget(btn_next)
        layout.addLayout(body, 1)

        nav = QHBoxLayout()
        btn_exit = QPushButton(" Volver al Menu")
        btn_exit.setStyleSheet("background-color:#C62828; color:white; padding: 10px; font-weight: bold;")
        btn_exit.clicked.connect(self.close)
        nav.addStretch()
        nav.addWidget(btn_exit)
        nav.addStretch()
        layout.addLayout(nav)

    @staticmethod
    def _normalize_item(item):
        if isinstance(item, dict):
            return {
                "result": item.get("result") or item.get("path") or "",
                "frame": item.get("frame"),
            }
        return {"result": str(item), "frame": None}

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.show_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.show_image)

    def show_image(self):
        if not self.images:
            return
        item = self.images[self.idx]
        self._set_label_pixmap(self.label, item["result"])
        if item.get("frame"):
            self.frame_label.show()
            self._set_label_pixmap(self.frame_label, item["frame"])
        else:
            self.frame_label.hide()
            self.frame_label.clear()

    def _set_label_pixmap(self, label, image_path):
        pix = QPixmap(image_path)
        if pix.isNull():
            label.clear()
            return
        target = label.contentsRect().size()
        if target.width() <= 1 or target.height() <= 1:
            target = self.size()
        label.setPixmap(
            pix.scaled(
                target,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def next(self):
        if self.idx < len(self.images) - 1:
            self.idx += 1
            self.show_image()

    def prev(self):
        if self.idx > 0:
            self.idx -= 1
            self.show_image()


class WelcomeScreen(QWidget):
    def __init__(self, on_finish):
        super().__init__()
        self.on_finish = on_finish
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #121212;")
        self.showFullScreen()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.logo = QLabel()
        logo_path = resource_path(os.path.join("assets", "logo.png"))
        pix = QPixmap(logo_path).scaled(
            320, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.logo.setPixmap(pix)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text = QLabel("Bienvenido a AZA Analyzer")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.text.setStyleSheet("color: white;")

        layout.addWidget(self.logo)
        layout.addSpacing(20)
        layout.addWidget(self.text)

        self.logo_fx = QGraphicsOpacityEffect(self.logo)
        self.text_fx = QGraphicsOpacityEffect(self.text)
        self.logo.setGraphicsEffect(self.logo_fx)
        self.text.setGraphicsEffect(self.text_fx)
        self.logo_fx.setOpacity(0)
        self.text_fx.setOpacity(0)

        self.anim_group = None
        QTimer.singleShot(150, self.start_animation)

    def start_animation(self):
        logo_anim = QPropertyAnimation(self.logo_fx, b"opacity")
        logo_anim.setDuration(1200)
        logo_anim.setStartValue(0)
        logo_anim.setEndValue(1)

        text_anim = QPropertyAnimation(self.text_fx, b"opacity")
        text_anim.setDuration(1000)
        text_anim.setStartValue(0)
        text_anim.setEndValue(1)

        self.anim_group = QParallelAnimationGroup(self)
        self.anim_group.addAnimation(logo_anim)
        self.anim_group.addAnimation(text_anim)
        self.anim_group.start()

        QTimer.singleShot(2300, self.finish)

    def finish(self):
        self.close()
        self.on_finish()
