import sys
import os
import time
import cv2
import numpy as np
from PIL import Image

from PySide6 import QtCore, QtWidgets, QtGui


# ══════════════════════════════════════════════════════════════
CHAR_SETS = {
    "Detailed": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "Newspaper": "@#%+=-:. ",
    "Block": "█▒░ ",
    "Dot": ".",
}

DEFAULTS = {
    'width': 60,
    'height': 34,
    'contrast': 1.2,
    'font_size': 10,
    'use_color': True,
    'invert': False,
    'auto_contrast': False,
    'char_set': "Detailed",
}

CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
SAVE_PATH_PNG = "/storage/emulated/0/Download/ascii_camera.png"
SAVE_PATH_TXT = "/storage/emulated/0/Download/ascii_camera.txt"
# ===============================================================


class ASCIIRenderer:
    def __init__(self):
        self.chars = None
        self.n = 0
        self.mode = "normal"

    def set_chars(self, char_string):
        if char_string == ".":
            self.mode = "dot"
            self.chars = np.array(['.'])
            self.n = 1
        else:
            self.mode = "normal"
            self.chars = np.array(list(char_string))
            self.n = len(self.chars)

    def render(self, frame_rgb, out_w, out_h, contrast=1.0, auto_contrast=False):
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

        if self.mode == "dot":
            symbols = np.full(gray.shape, '.', dtype='<U1')
            return symbols, img.astype(np.uint8), gray.astype(np.uint8)
        else:
            indices = np.clip((gray / 255.0) * (self.n - 1), 0, self.n - 1).astype(int)
            symbols = self.chars[indices]
            return symbols, img.astype(np.uint8), gray.astype(np.uint8)


class ASCIICameraWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = ASCIIRenderer()
        self.renderer.set_chars(CHAR_SETS[DEFAULTS['char_set']])

        # ВСЕ параметры хранятся ВНУТРИ и обновляются напрямую
        self.params = {
            'ascii_w': DEFAULTS['width'],
            'ascii_h': DEFAULTS['height'],
            'contrast': DEFAULTS['contrast'],
            'font_size': DEFAULTS['font_size'],
            'use_color': DEFAULTS['use_color'],
            'invert': DEFAULTS['invert'],
            'auto_contrast': DEFAULTS['auto_contrast'],
            'char_set_name': DEFAULTS['char_set'],
        }

        self.char_w = 8
        self.line_h = 14
        self.ascii_symbols = None
        self.colors = None
        self.gray = None
        self.last_frame_time = time.time()
        self.fps = 0.0

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

        self.update_metrics()

    def update_params(self,
                      ascii_w=None, ascii_h=None, contrast=None,
                      font_size=None, use_color=None, invert=None,
                      auto_contrast=None, char_set_name=None):
        # Обновляем параметры поименно
        changed = False
        redraw_needed = False

        if ascii_w is not None and self.params['ascii_w'] != ascii_w:
            self.params['ascii_w'] = ascii_w
            changed = True
        if ascii_h is not None and self.params['ascii_h'] != ascii_h:
            self.params['ascii_h'] = ascii_h
            changed = True
        if contrast is not None and abs(self.params['contrast'] - contrast) > 1e-3:
            self.params['contrast'] = contrast
            changed = True
        if font_size is not None and self.params['font_size'] != font_size:
            self.params['font_size'] = font_size
            changed = True
        if use_color is not None and self.params['use_color'] != use_color:
            self.params['use_color'] = use_color
            changed = True
        if invert is not None and self.params['invert'] != invert:
            self.params['invert'] = invert
            changed = True
        if auto_contrast is not None and self.params['auto_contrast'] != auto_contrast:
            self.params['auto_contrast'] = auto_contrast
            changed = True
        if char_set_name is not None and self.params['char_set_name'] != char_set_name:
            self.params['char_set_name'] = char_set_name
            self.renderer.set_chars(CHAR_SETS[char_set_name])
            redraw_needed = True
            changed = True

        if changed:
            self.update_metrics()
            # Принудительно обновляем кадр в следующем цикле
        if redraw_needed:
            self.update()  # немедленная перерисовка UI

        # Debug (можно закомментировать)
        # print("Params updated:", {k: v for k, v in locals().items() if k != 'self' and v is not None})

    def update_metrics(self):
        font = QtGui.QFont("Courier New", self.params['font_size'])
        fm = QtGui.QFontMetrics(font)
        self.char_w = fm.horizontalAdvance("W") or 8
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
                self.params['ascii_w'],
                self.params['ascii_h'],
                self.params['contrast'],
                self.params['auto_contrast']
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
        font = QtGui.QFont("Courier New", self.params['font_size'])
        painter.setFont(font)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)

        bg = QtCore.Qt.white if self.params['invert'] else QtCore.Qt.black
        painter.fillRect(self.rect(), bg)

        H, W = self.ascii_symbols.shape
        for y in range(H):
            for x in range(W):
                ch = self.ascii_symbols[y, x]

                if self.params['use_color']:
                    color_arr = self.colors[y, x]
                else:
                    val = int(self.gray[y, x])
                    color_arr = (val, val, val)

                r, g, b = color_arr

                # Dot mode brightness modulation
                if self.params['char_set_name'] == "Dot":
                    brightness = self.gray[y, x] / 255.0
                    if self.params['invert']:
                        r = int(r * (1 - brightness) + 255 * brightness)
                        g = int(g * (1 - brightness) + 255 * brightness)
                        b = int(b * (1 - brightness) + 255 * brightness)
                    else:
                        r = int(r * brightness)
                        g = int(g * brightness)
                        b = int(b * brightness)

                if self.params['invert']:
                    r, g, b = 255 - r, 255 - g, 255 - b

                painter.setPen(QtGui.QColor(r, g, b))
                painter.drawText(
                    x * self.char_w,
                    y * self.line_h + self.params['font_size'],
                    ch
                )

    def save_current_frame_png(self):
        if self.ascii_symbols is None:
            return False

        img_w = self.params['ascii_w'] * self.char_w
        img_h = self.params['ascii_h'] * self.line_h
        qimg = QtGui.QImage(img_w, img_h, QtGui.QImage.Format_RGB888)
        qimg.fill(QtCore.Qt.black if not self.params['invert'] else QtCore.Qt.white)

        painter = QtGui.QPainter(qimg)
        font = QtGui.QFont("Courier New", self.params['font_size'])
        painter.setFont(font)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)

        H, W = self.ascii_symbols.shape
        for y in range(H):
            for x in range(W):
                ch = self.ascii_symbols[y, x]

                if self.params['use_color']:
                    color_arr = self.colors[y, x]
                else:
                    val = int(self.gray[y, x])
                    color_arr = (val, val, val)

                r, g, b = color_arr

                if self.params['char_set_name'] == "Dot":
                    brightness = self.gray[y, x] / 255.0
                    if self.params['invert']:
                        r = int(r * (1 - brightness) + 255 * brightness)
                        g = int(g * (1 - brightness) + 255 * brightness)
                        b = int(b * (1 - brightness) + 255 * brightness)
                    else:
                        r = int(r * brightness)
                        g = int(g * brightness)
                        b = int(b * brightness)

                if self.params['invert']:
                    r, g, b = 255 - r, 255 - g, 255 - b

                painter.setPen(QtGui.QColor(r, g, b))
                painter.drawText(
                    x * self.char_w,
                    y * self.line_h + self.params['font_size'],
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
        if self.ascii_symbols is None:
            return ""
        return "\n".join("".join(row) for row in self.ascii_symbols)

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


class ControlPanel(QtWidgets.QWidget):
    params_changed = QtCore.Signal(
        int, int, float, int, bool, bool, bool, str
    )  # ascii_w, ascii_h, contrast, font_size, use_color, invert, auto_contrast, char_set_name

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

        self.width_slider = self._make_slider("Width", 20, 120, DEFAULTS['width'], "chars")
        self.height_slider = self._make_slider("Height", 10, 70, DEFAULTS['height'], "chars")
        self.contrast_slider = self._make_slider("Contrast", 0.5, 3.0, DEFAULTS['contrast'], "", factor=100)
        self.font_slider = self._make_slider("Font size", 6, 20, DEFAULTS['font_size'], "pt")

        char_layout = QtWidgets.QHBoxLayout()
        char_layout.addWidget(QtWidgets.QLabel("Char set:"))
        self.char_combo = QtWidgets.QComboBox()
        self.char_combo.addItems(["Detailed", "Newspaper", "Block", "Dot"])
        self.char_combo.setCurrentText(DEFAULTS['char_set'])
        char_layout.addWidget(self.char_combo)
        char_layout.addStretch()

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

        btn_layout = QtWidgets.QHBoxLayout()
        self.save_png_btn = QtWidgets.QPushButton("💾 Save PNG")
        self.save_txt_btn = QtWidgets.QPushButton("📄 Save TXT")
        self.copy_btn = QtWidgets.QPushButton("📋 Copy text")
        self.fullscreen_btn = QtWidgets.QPushButton("⛶ Fullscreen")
        btn_layout.addWidget(self.save_png_btn)
        btn_layout.addWidget(self.save_txt_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.fullscreen_btn)

        layout.addLayout(self.width_slider['layout'])
        layout.addLayout(self.height_slider['layout'])
        layout.addLayout(self.contrast_slider['layout'])
        layout.addLayout(self.font_slider['layout'])
        layout.addLayout(char_layout)
        layout.addLayout(toggle_layout)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 🔥 КРИТИЧЕСКИ ВАЖНО: подключаем КАЖДОЕ изменение ОТДЕЛЬНО
        self.width_slider['slider'].valueChanged.connect(self._emit_params)
        self.height_slider['slider'].valueChanged.connect(self._emit_params)
        self.contrast_slider['slider'].valueChanged.connect(self._emit_params)
        self.font_slider['slider'].valueChanged.connect(self._emit_params)
        self.char_combo.currentTextChanged.connect(self._emit_params)
        self.color_cb.stateChanged.connect(self._emit_params)
        self.invert_cb.stateChanged.connect(self._emit_params)
        self.auto_contrast_cb.stateChanged.connect(self._emit_params)

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

        label = QtWidgets.QLabel(f"{default}{suffix}")
        slider.valueChanged.connect(lambda v: label.setText(f"{v/factor:.1f}{suffix}"))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(name + ":"))
        layout.addWidget(slider)
        layout.addWidget(label)

        return {'slider': slider, 'label': label, 'layout': layout, 'factor': factor}

    def _emit_params(self):
        """Emit all current values as separate args (robust for Android)"""
        w = self.width_slider['slider'].value()
        h = self.height_slider['slider'].value()
        contrast = self.contrast_slider['slider'].value() / 100.0
        font = self.font_slider['slider'].value()
        use_color = self.color_cb.isChecked()
        invert = self.invert_cb.isChecked()
        auto_contrast = self.auto_contrast_cb.isChecked()
        char_set = self.char_combo.currentText()

        self.params_changed.emit(w, h, contrast, font, use_color, invert, auto_contrast, char_set)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📺 ASCII Camera Pro")
        self.resize(800, 600)

        self.camera_widget = ASCIICameraWidget()
        self.control_panel = ControlPanel()

        self.status_label = QtWidgets.QLabel("FPS: 0.0 | Camera: ?×? | Mode: —")
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

        # 🔥 ПРАВИЛЬНОЕ ПОДКЛЮЧЕНИЕ СЛОТА:
        self.control_panel.params_changed.connect(
            self.on_params_changed,
            type=QtCore.Qt.DirectConnection  # ← гарантирует мгновенное выполнение на Android
        )

        self.control_panel.save_png.connect(self.save_png)
        self.control_panel.save_txt.connect(self.save_txt)
        self.control_panel.copy_text.connect(self.copy_text)
        self.control_panel.fullscreen_requested.connect(self.toggle_fullscreen)

        self.status_timer = QtCore.QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(500)

        self.orientation_timer = QtCore.QTimer()
        self.orientation_timer.timeout.connect(self.check_orientation)
        self.orientation_timer.start(2000)

        self.shortcut_fullscreen = QtGui.QShortcut(QtGui.QKeySequence("F11"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        self.shortcut_save_png = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+P"), self)
        self.shortcut_save_png.activated.connect(self.save_png)
        self.shortcut_save_txt = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), self)
        self.shortcut_save_txt.activated.connect(self.save_txt)

    def on_params_changed(self, w, h, contrast, font_size, use_color, invert, auto_contrast, char_set_name):
        """Direct slot — no dict unpacking issues"""
        self.camera_widget.update_params(
            ascii_w=w,
            ascii_h=h,
            contrast=contrast,
            font_size=font_size,
            use_color=use_color,
            invert=invert,
            auto_contrast=auto_contrast,
            char_set_name=char_set_name
        )

    def check_orientation(self):
        screen = self.screen()
        geo = screen.geometry()
        w, h = geo.width(), geo.height()
        is_landscape = w > h

        target_ratio = 2.0 if is_landscape else 1.4
        new_h = min(45, max(20, self.camera_widget.params['ascii_h']))
        new_w = int(new_h * target_ratio)
        new_w = max(20, min(120, new_w))

        if abs(new_w - self.camera_widget.params['ascii_w']) > 5 or abs(new_h - self.camera_widget.params['ascii_h']) > 3:
            self.camera_widget.update_params(ascii_w=new_w, ascii_h=new_h)
            self.control_panel.width_slider['slider'].setValue(new_w)
            self.control_panel.height_slider['slider'].setValue(new_h)

    def update_status(self):
        w, h = -1, -1
        if self.camera_widget.cap.isOpened():
            w = int(self.camera_widget.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.camera_widget.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        mode = self.camera_widget.params['char_set_name']
        self.status_label.setText(
            f"FPS: {self.camera_widget.fps:.1f} | ASCII: {self.camera_widget.params['ascii_w']}×{self.camera_widget.params['ascii_h']} | "
            f"Camera: {w}×{h} | Mode: {mode}"
        )

    def save_png(self):
        success = self.camera_widget.save_current_frame_png()
        self._show_save_result(success, "PNG", SAVE_PATH_PNG)

    def save_txt(self):
        success = self.camera_widget.save_current_frame_txt()
        self._show_save_result(success, "TXT", SAVE_PATH_TXT)

    def copy_text(self):
        text = self.camera_widget.get_text_ascii()
        if text:
            cb = QtWidgets.QApplication.clipboard()
            cb.setText(text)
            QtWidgets.QMessageBox.information(self, "📋 Copied", "ASCII text copied to clipboard!")
        else:
            QtWidgets.QMessageBox.warning(self, "⚠️ Empty", "No frame available.")

    def _show_save_result(self, success, fmt, path):
        if success:
            QtWidgets.QMessageBox.information(self, f"✅ {fmt} Saved", f"Saved to:\n{path}")
        else:
            QtWidgets.QMessageBox.critical(self, f"❌ {fmt} Error", f"Failed to save {fmt} file!")

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

    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(50, 50, 50))
    palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(20, 20, 20))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(35, 35, 35))
    app.setPalette(palette)

    # Force high-DPI font smoothing (helps on Android)
    font = app.font()
    font.setPointSize(9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
