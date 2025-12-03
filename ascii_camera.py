import sys
import os
import time
import cv2
import numpy as np
from PIL import Image

from PySide6 import QtCore, QtWidgets, QtGui


# ══════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION & ASCII CHAR SETS
# ══════════════════════════════════════════════════════════════

# Char sets for different styles
CHAR_SETS = {
    "Detailed": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "Newspaper": "@#%+=-:. ",
    "Block": "█▒░ ",  # Unicode block elements (may render as squares on some devices)
}

DEFAULTS = {
    'width': 60,
    'height': 34,
    'contrast': 1.2,
    'font_size': 10,
    'use_color': True,
    'invert': False,
    'auto_contrast': False,
    'char_set': "Detailed",  # "Detailed", "Newspaper", "Block"
}

CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
SAVE_PATH_PNG = "/storage/emulated/0/Download/ascii_camera.png"
SAVE_PATH_TXT = "/storage/emulated/0/Download/ascii_camera.txt"
# ===============================================================


class ASCIIRenderer:
    def __init__(self):
        self.chars = None
        self.n = 0

    def set_chars(self, char_string):
        self.chars = np.array(list(char_string))
        self.n = len(self.chars)

    def render(self, frame_rgb, out_w, out_h, contrast=1.0, auto_contrast=False):
        if self.chars is None:
            raise ValueError("Char set not initialized")

        pil_img = Image.fromarray(frame_rgb)
        resized = pil_img.resize((out_w, out_h), Image.Resampling.LANCZOS)
        img = np.array(resized)

        gray = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]

        if auto_contrast and gray.size > 0:
            g_min, g_max = gray.min(), gray.max()
            if g_max > g_min:
                gray = 255 * (gray - g_min) / (g_max - g_min)
        else:
            gray = np.clip(128 + (gray - 128) * contrast, 0, 255)

        indices = np.clip((gray / 255.0) * (self.n - 1), 0, self.n - 1).astype(int)
        symbols = self.chars[indices]

        return symbols, img.astype(np.uint8), gray.astype(np.uint8)


class ASCIICameraWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = ASCIIRenderer()
        self.renderer.set_chars(CHAR_SETS[DEFAULTS['char_set']])

        # Parameters
        self.ascii_w = DEFAULTS['width']
        self.ascii_h = DEFAULTS['height']
        self.contrast = DEFAULTS['contrast']
        self.font_size = DEFAULTS['font_size']
        self.use_color = DEFAULTS['use_color']
        self.invert = DEFAULTS['invert']
        self.auto_contrast = DEFAULTS['auto_contrast']
        self.char_set_name = DEFAULTS['char_set']

        # Metrics cache
        self.char_w = 8
        self.line_h = 14
        self.ascii_symbols = None
        self.colors = None
        self.gray = None
        self.last_frame_time = time.time()
        self.fps = 0.0

        # Camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_params(self, **kwargs):
        changed = False
        redraw_needed = False

        for k, v in kwargs.items():
            if hasattr(self, k):
                old = getattr(self, k)
                if old != v:
                    setattr(self, k, v)
                    changed = True
                    if k in ('char_set_name',):
                        redraw_needed = True

        if 'char_set_name' in kwargs:
            self.renderer.set_chars(CHAR_SETS[kwargs['char_set_name']])

        if changed:
            self.update_metrics()
        if redraw_needed:
            self.update()

    def update_metrics(self):
        font = QtGui.QFont("Courier New", self.font_size)
        fm = QtGui.QFontMetrics(font)
        self.char_w = fm.horizontalAdvance("W")
        self.line_h = fm.height() + 2
        self.update()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        now = time.time()
        self.fps = 0.9 * self.fps + 0.1 * (1.0 / max(0.001, now - self.last_frame_time))
        self.last_frame_time = now

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            symbols, colors, gray = self.renderer.render(
                frame_rgb,
                self.ascii_w, self.ascii_h,
                self.contrast,
                self.auto_contrast
            )
            self.ascii_symbols = symbols
            self.colors = colors
            self.gray = gray
        except Exception as e:
            print("Render error:", e)
        self.update()

    def paintEvent(self, event):
        if self.ascii_symbols is None:
            return

        painter = QtGui.QPainter(self)
        font = QtGui.QFont("Courier New", self.font_size)
        painter.setFont(font)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)

        bg = QtCore.Qt.white if self.invert else QtCore.Qt.black
        painter.fillRect(self.rect(), bg)

        H, W = self.ascii_symbols.shape
        for y in range(H):
            for x in range(W):
                ch = self.ascii_symbols[y, x]
                if self.use_color:
                    color_arr = self.colors[y, x]
                else:
                    val = int(self.gray[y, x])
                    color_arr = (val, val, val)

                r, g, b = color_arr
                if self.invert:
                    r, g, b = 255 - r, 255 - g, 255 - b
                painter.setPen(QtGui.QColor(r, g, b))

                painter.drawText(
                    x * self.char_w,
                    y * self.line_h + self.font_size,
                    ch
                )

    def save_current_frame_png(self):
        if self.ascii_symbols is None:
            return False

        img_w = self.ascii_w * self.char_w
        img_h = self.ascii_h * self.line_h
        qimg = QtGui.QImage(img_w, img_h, QtGui.QImage.Format_RGB888)
        qimg.fill(QtCore.Qt.black if not self.invert else QtCore.Qt.white)

        painter = QtGui.QPainter(qimg)
        font = QtGui.QFont("Courier New", self.font_size)
        painter.setFont(font)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)

        H, W = self.ascii_symbols.shape
        for y in range(H):
            for x in range(W):
                ch = self.ascii_symbols[y, x]
                if self.use_color:
                    color_arr = self.colors[y, x]
                else:
                    val = int(self.gray[y, x])
                    color_arr = (val, val, val)

                r, g, b = color_arr
                if self.invert:
                    r, g, b = 255 - r, 255 - g, 255 - b
                painter.setPen(QtGui.QColor(r, g, b))

                painter.drawText(
                    x * self.char_w,
                    y * self.line_h + self.font_size,
                    ch
                )
        painter.end()

        os.makedirs(os.path.dirname(SAVE_PATH_PNG), exist_ok=True)
        return qimg.save(SAVE_PATH_PNG, "PNG")

    def save_current_frame_txt(self):
        if self.ascii_symbols is None:
            return False

        lines = []
        for row in self.ascii_symbols:
            lines.append("".join(row))
        text = "\n".join(lines)

        os.makedirs(os.path.dirname(SAVE_PATH_TXT), exist_ok=True)
        try:
            with open(SAVE_PATH_TXT, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            print("TXT save error:", e)
            return False

    def get_text_ascii(self):
        """Returns current frame as pure ASCII text (for copy/export)"""
        if self.ascii_symbols is None:
            return ""
        return "\n".join("".join(row) for row in self.ascii_symbols)

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


class ControlPanel(QtWidgets.QWidget):
    params_changed = QtCore.Signal(dict)
    save_png = QtCore.Signal()
    save_txt = QtCore.Signal()
    copy_text = QtCore.Signal()
    fullscreen_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Sliders
        self.width_slider = self._make_slider("Width", 20, 120, DEFAULTS['width'], "chars")
        self.height_slider = self._make_slider("Height", 10, 70, DEFAULTS['height'], "chars")
        self.contrast_slider = self._make_slider("Contrast", 0.5, 3.0, DEFAULTS['contrast'], "", factor=100)
        self.font_slider = self._make_slider("Font size", 6, 20, DEFAULTS['font_size'], "pt")

        # Char set combo
        char_layout = QtWidgets.QHBoxLayout()
        char_layout.addWidget(QtWidgets.QLabel("Char set:"))
        self.char_combo = QtWidgets.QComboBox()
        self.char_combo.addItems(["Detailed", "Newspaper", "Block"])
        self.char_combo.setCurrentText(DEFAULTS['char_set'])
        char_layout.addWidget(self.char_combo)
        char_layout.addStretch()

        # Toggles
        toggle_layout = QtWidgets.QHBoxLayout()
        self.color_cb = QtWidgets.QCheckBox("Color")
        self.color_cb.setChecked(DEFAULTS['use_color'])
        self.invert_cb = QtWidgets.QCheckBox("Invert")
        self.invert_cb.setChecked(DEFAULTS['invert'])
        self.auto_contrast_cb = QtWidgets.QCheckBox("Auto-contrast")
        self.auto_contrast_cb.setChecked(DEFAULTS['auto_contrast'])

        toggle_layout.addWidget(self.color_cb)
        toggle_layout.addWidget(self.invert_cb)
        toggle_layout.addWidget(self.auto_contrast_cb)
        toggle_layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.save_png_btn = QtWidgets.QPushButton("💾 Save PNG")
        self.save_txt_btn = QtWidgets.QPushButton("📄 Save TXT")
        self.copy_btn = QtWidgets.QPushButton("📋 Copy text")
        self.fullscreen_btn = QtWidgets.QPushButton("⛶ Fullscreen")
        btn_layout.addWidget(self.save_png_btn)
        btn_layout.addWidget(self.save_txt_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.fullscreen_btn)

        # Assemble
        layout.addLayout(self.width_slider['layout'])
        layout.addLayout(self.height_slider['layout'])
        layout.addLayout(self.contrast_slider['layout'])
        layout.addLayout(self.font_slider['layout'])
        layout.addLayout(char_layout)
        layout.addLayout(toggle_layout)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Signals
        self.width_slider['slider'].valueChanged.connect(self._on_change)
        self.height_slider['slider'].valueChanged.connect(self._on_change)
        self.contrast_slider['slider'].valueChanged.connect(self._on_change)
        self.font_slider['slider'].valueChanged.connect(self._on_change)
        self.char_combo.currentTextChanged.connect(self._on_change)
        self.color_cb.stateChanged.connect(self._on_change)
        self.invert_cb.stateChanged.connect(self._on_change)
        self.auto_contrast_cb.stateChanged.connect(self._on_change)

        self.save_png_btn.clicked.connect(self.save_png)
        self.save_txt_btn.clicked.connect(self.save_txt)
        self.copy_btn.clicked.connect(self.copy_text)
        self.fullscreen_btn.clicked.connect(self.fullscreen_requested)

    def _make_slider(self, name, min_v, max_v, default, suffix="", factor=1):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(int(min_v * factor))
        slider.setMaximum(int(max_v * factor))
        slider.setValue(int(default * factor))
        slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        slider.setTickInterval(int((max_v - min_v) * factor / 5))

        label = QtWidgets.QLabel(f"{default}{suffix}")
        slider.valueChanged.connect(lambda v: label.setText(f"{v/factor:.1f}{suffix}"))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(name + ":"))
        layout.addWidget(slider)
        layout.addWidget(label)

        return {'slider': slider, 'label': label, 'layout': layout, 'factor': factor}

    def _on_change(self):
        data = {
            'ascii_w': self.width_slider['slider'].value(),
            'ascii_h': self.height_slider['slider'].value(),
            'contrast': self.contrast_slider['slider'].value() / self.contrast_slider['factor'],
            'font_size': self.font_slider['slider'].value(),
            'use_color': self.color_cb.isChecked(),
            'invert': self.invert_cb.isChecked(),
            'auto_contrast': self.auto_contrast_cb.isChecked(),
            'char_set_name': self.char_combo.currentText(),
        }
        self.params_changed.emit(data)

    def update_from_defaults(self):
        self.width_slider['slider'].setValue(DEFAULTS['width'])
        self.height_slider['slider'].setValue(DEFAULTS['height'])
        self.contrast_slider['slider'].setValue(int(DEFAULTS['contrast'] * 100))
        self.font_slider['slider'].setValue(DEFAULTS['font_size'])
        self.char_combo.setCurrentText(DEFAULTS['char_set'])
        self.color_cb.setChecked(DEFAULTS['use_color'])
        self.invert_cb.setChecked(DEFAULTS['invert'])
        self.auto_contrast_cb.setChecked(DEFAULTS['auto_contrast'])


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📺 ASCII Camera Pro")
        self.resize(800, 600)

        self.camera_widget = ASCIICameraWidget()
        self.control_panel = ControlPanel()

        self.status_label = QtWidgets.QLabel("FPS: 0.0 | Camera: ?×? | Orientation: —")
        self.statusBar().addWidget(self.status_label)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.camera_widget)
        splitter.addWidget(self.control_panel)
        splitter.setSizes([700, 200])

        layout.addWidget(splitter)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Connections
        self.control_panel.params_changed.connect(self.camera_widget.update_params)
        self.control_panel.save_png.connect(self.save_png)
        self.control_panel.save_txt.connect(self.save_txt)
        self.control_panel.copy_text.connect(self.copy_text)
        self.control_panel.fullscreen_requested.connect(self.toggle_fullscreen)

        # Status & auto-orientation
        self.status_timer = QtCore.QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(500)

        self.orientation_timer = QtCore.QTimer()
        self.orientation_timer.timeout.connect(self.check_orientation)
        self.orientation_timer.start(1000)  # check every second

        # Shortcuts
        self.shortcut_fullscreen = QtGui.QShortcut(QtGui.QKeySequence("F11"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        self.shortcut_save_png = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+P"), self)
        self.shortcut_save_png.activated.connect(self.save_png)
        self.shortcut_save_txt = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), self)
        self.shortcut_save_txt.activated.connect(self.save_txt)

    def check_orientation(self):
        """Auto-adjust ASCII size based on screen orientation (rough estimation)"""
        screen = self.screen()
        geo = screen.geometry()
        w, h = geo.width(), geo.height()
        is_landscape = w > h

        # Heuristic: adjust default ratio
        if is_landscape:
            target_ratio = 2.0  # e.g. 80x40
        else:
            target_ratio = 1.4  # e.g. 50x36

        # Keep height ~30-40, adjust width
        new_h = min(40, max(20, self.camera_widget.ascii_h))
        new_w = int(new_h * target_ratio)
        new_w = max(20, min(120, new_w))

        # Apply only if significantly different
        if abs(new_w - self.camera_widget.ascii_w) > 5 or abs(new_h - self.camera_widget.ascii_h) > 3:
            self.camera_widget.update_params(ascii_w=new_w, ascii_h=new_h)
            self.control_panel.width_slider['slider'].setValue(new_w)
            self.control_panel.height_slider['slider'].setValue(new_h)

    def update_status(self):
        w, h = -1, -1
        orient = "Landscape" if self.width() > self.height() else "Portrait"
        if self.camera_widget.cap.isOpened():
            w = int(self.camera_widget.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.camera_widget.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.status_label.setText(
            f"FPS: {self.camera_widget.fps:.1f} | "
            f"ASCII: {self.camera_widget.ascii_w}×{self.camera_widget.ascii_h} | "
            f"Camera: {w}×{h} | "
            f"Orientation: {orient}"
        )

    def save_png(self):
        success = self.camera_widget.save_current_frame_png()
        path = SAVE_PATH_PNG
        self._show_save_result(success, "PNG", path)

    def save_txt(self):
        success = self.camera_widget.save_current_frame_txt()
        path = SAVE_PATH_TXT
        self._show_save_result(success, "TXT", path)

    def copy_text(self):
        text = self.camera_widget.get_text_ascii()
        if text:
            cb = QtWidgets.QApplication.clipboard()
            cb.setText(text)
            QtWidgets.QMessageBox.information(self, "📋 Copied", "ASCII text copied to clipboard!")
        else:
            QtWidgets.QMessageBox.warning(self, "⚠️ Empty", "No frame available to copy.")

    def _show_save_result(self, success, fmt, path):
        if success:
            QtWidgets.QMessageBox.information(
                self, f"✅ {fmt} Saved", f"Saved to:\n{path}"
            )
        else:
            QtWidgets.QMessageBox.critical(
                self, f"❌ {fmt} Error", f"Failed to save {fmt} file!"
            )

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.control_panel.setVisible(True)
        else:
            self.showFullScreen()
            self.control_panel.setVisible(False)

    def closeEvent(self, event):
        self.status_timer.stop()
        self.orientation_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    # Dark theme
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
    palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(50, 50, 50))
    palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(20, 20, 20))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(40, 40, 40))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())