import sys
import os
import time
import datetime
import traceback
import io
import cv2
import numpy as np
from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# ══════════════════════════════════════════════════════════════
CHAR_SETS = {
    "Detailed": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "Newspaper": "@#%+=-:. ",
    "Block": "█▒░ ",
    "Dot": ".",
    "LightSmooth": " _.,:;i1tfLCG08@",  # ← НОВЫЙ: 16 символов, равномерная плотность
}
DEFAULTS = {
    'width': 80,          # ↑ увеличено для чёткости
    'height': 44,         # = 80 * 0.55 → идеальное соотношение для Courier New
    'contrast': 1.3,
    'font_size': 10,
    'use_color': True,
    'invert': False,
    'auto_contrast': True,  # ↑ включено по умолчанию для деталей
    'char_set': "LightSmooth",  # ← рекомендуемый по умолчанию
    'lock_aspect': True,   # ← новая опция: привязка H к W
}
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480

# ✅ Рабочий путь для Pydroid 3 и кросс-платформенный fallback
if sys.platform == "win32":
    SAVE_DIR = os.path.expanduser("~/ASCII_Camera/")
elif sys.platform == "linux" and "ANDROID_ROOT" in os.environ:
    candidates = [
        "/storage/emulated/0/Download/ASCII_Camera/",
        "/sdcard/Download/ASCII_Camera/",
        os.path.expanduser("~/ASCII_Camera/"),
    ]
    for cand in candidates:
        try:
            os.makedirs(cand, exist_ok=True)
            with open(os.path.join(cand, ".test_write"), "w") as f:
                f.write("ok")
            os.remove(os.path.join(cand, ".test_write"))
            SAVE_DIR = cand
            break
        except (OSError, PermissionError, IOError):
            continue
    else:
        SAVE_DIR = os.path.expanduser("~/ASCII_Camera/")
else:
    SAVE_DIR = os.path.expanduser("~/ASCII_Camera/")

# ===============================================================

class ThemeManager(QtCore.QObject):
    theme_changed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QtCore.QSettings("ASCII_Camera", "Pro")
        self._current_mode = self.settings.value("theme_mode", "auto")
        self._applied_theme = "light"

    def detect_system_theme(self):
        app_name = QtWidgets.QApplication.applicationDisplayName()
        if "dark" in app_name.lower() or "black" in app_name.lower():
            return "dark"
        try:
            palette = QtWidgets.QApplication.palette()
            window_color = palette.color(QtGui.QPalette.Window)
            brightness = (0.299 * window_color.red() +
                          0.587 * window_color.green() +
                          0.114 * window_color.blue())
            return "dark" if brightness < 128 else "light"
        except:
            return "light"

    def get_effective_theme(self):
        if self._current_mode == "auto":
            return self.detect_system_theme()
        return self._current_mode

    def get_palette_and_stylesheet(self, theme_name):
        if theme_name == "dark":
            return self._create_dark_palette(), self._dark_stylesheet()
        else:
            return self._create_light_palette(), self._light_stylesheet()

    def _create_light_palette(self):
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Window, QtGui.QColor(240, 240, 240))
        p.setColor(QtGui.QPalette.WindowText, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.Base, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(245, 245, 245))
        p.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.Button, QtGui.QColor(230, 230, 230))
        p.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        p.setColor(QtGui.QPalette.Link, QtGui.QColor(0, 100, 200))
        p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(0, 120, 215))
        p.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtCore.Qt.gray)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, QtCore.Qt.gray)
        return p

    def _create_dark_palette(self):
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Window, QtGui.QColor(25, 25, 25))
        p.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.Base, QtGui.QColor(35, 35, 35))
        p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        p.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        p.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        p.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        p.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        p.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtCore.Qt.darkGray)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, QtCore.Qt.darkGray)
        return p

    def _light_stylesheet(self):
        return """
            QLabel, QComboBox, QCheckBox, QRadioButton {
                color: black;
                font-size: 10pt;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999;
                background: #ddd;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078D7;
                border: 1px solid #555;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked,
            QRadioButton::indicator:unchecked {
                border: 2px solid #888;
                background: white;
            }
            QCheckBox::indicator:checked {
                image: url(none);
                background: white;
                border: 2px solid #0078D7;
            }
            QCheckBox::indicator:checked::after {
                content: "";
                position: absolute;
                top: 2px;
                left: 5px;
                width: 4px;
                height: 8px;
                border: solid black;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
            }
            QRadioButton::indicator:checked {
                image: url(none);
                background: white;
                border: 2px solid #0078D7;
            }
            QRadioButton::indicator:checked::after {
                content: "";
                position: absolute;
                top: 4px;
                left: 4px;
                width: 8px;
                height: 8px;
                background: #0078D7;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: black;
                border: 1px solid #aaa;
                padding: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QComboBox {
                color: black;
                background: white;
                selection-background-color: #0078D7;
                selection-color: white;
            }
            QToolTip {
                color: black;
                background-color: #ffffc0;
                border: 1px solid black;
            }
            QStatusBar QLabel {
                color: black;
                font-weight: bold;
            }
        """

    def _dark_stylesheet(self):
        return """
            QLabel, QComboBox, QCheckBox, QRadioButton {
                color: white;
                font-size: 10pt;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                background: #333;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #444;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked,
            QRadioButton::indicator:unchecked {
                border: 2px solid #aaa;
                background: #222;
            }
            QCheckBox::indicator:checked {
                image: url(none);
                background: #222;
                border: 2px solid #4CAF50;
            }
            QCheckBox::indicator:checked::after {
                content: "";
                position: absolute;
                top: 2px;
                left: 5px;
                width: 4px;
                height: 8px;
                border: solid white;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
            }
            QRadioButton::indicator:checked {
                image: url(none);
                background: #222;
                border: 2px solid #4CAF50;
            }
            QRadioButton::indicator:checked::after {
                content: "";
                position: absolute;
                top: 4px;
                left: 4px;
                width: 8px;
                height: 8px;
                background: #4CAF50;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                padding: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QComboBox {
                color: white;
                background: #333;
                selection-background-color: #4CAF50;
                selection-color: black;
            }
            QToolTip {
                color: white;
                background-color: #2a82da;
                border: 1px solid white;
            }
            QStatusBar QLabel {
                color: white;
                font-weight: bold;
            }
        """

    def set_theme_mode(self, mode):
        if mode not in ("auto", "dark", "light"):
            return
        self._current_mode = mode
        self.settings.setValue("theme_mode", mode)
        self.apply_current_theme()
        self.theme_changed.emit(mode)

    def apply_current_theme(self):
        app = QtWidgets.QApplication.instance()
        theme_name = self.get_effective_theme()
        palette, stylesheet = self.get_palette_and_stylesheet(theme_name)
        app.setStyle("Fusion")
        app.setPalette(palette)
        app.setStyleSheet(stylesheet)
        self._applied_theme = theme_name

    def get_icon_for_mode(self, mode):
        if mode == "auto":
            return "🌓"
        elif mode == "dark":
            return "🌑"
        else:
            return "🌞"

    def cycle_mode(self):
        order = ["auto", "dark", "light"]
        idx = order.index(self._current_mode)
        self.set_theme_mode(order[(idx + 1) % len(order)])

# ───────────────────────────────────────────────────────────────

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

# ───────────────────────────────────────────────────────────────

class ASCIICameraWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = ASCIIRenderer()
        self.renderer.set_chars(CHAR_SETS[DEFAULTS['char_set']])
        self.params = {k: v for k, v in DEFAULTS.items()}
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
                      auto_contrast=None, char_set_name=None, lock_aspect=None):
        # Сохраняем текущее состояние
        old_w = self.params['ascii_w']
        old_h = self.params['ascii_h']
        old_lock = self.params['lock_aspect']

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
        if lock_aspect is not None and self.params['lock_aspect'] != lock_aspect:
            self.params['lock_aspect'] = lock_aspect
            changed = True

        # 🔑 АВТОМАТИЧЕСКАЯ КОРРЕКЦИЯ ВЫСОТЫ ПРИ LOCK
        if self.params['lock_aspect'] and changed:
            # Фиксированное соотношение для Courier New: H = W * 0.55
            ideal_h = int(self.params['ascii_w'] * 0.55)
            # Округляем до ближайшего чётного / кратного 2 для плавности
            ideal_h = max(10, min(70, ideal_h))
            if self.params['ascii_h'] != ideal_h:
                self.params['ascii_h'] = ideal_h
                # Отправим сигнал в ControlPanel для синхронизации слайдера
                if hasattr(self, '_notify_height_change'):
                    self._notify_height_change(ideal_h)

        if changed:
            self.update_metrics()
        if redraw_needed:
            self.update()

    def set_notify_height_callback(self, callback):
        self._notify_height_change = callback

    def set_notify_width_callback(self, callback):
        self._notify_width_change = callback

    def update_metrics(self):
        font = QtGui.QFont("Courier New", self.params['font_size'])
        fm = QtGui.QFontMetrics(font)
        self.char_w = fm.horizontalAdvance("W") or 8
        # Для точности: учитываем реальное соотношение W/H символа
        # В большинстве систем: char_w ≈ 8, line_h ≈ 14 → ratio ≈ 0.57
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

    def _render_to_painter(self, painter, scale=1.0):
        if self.ascii_symbols is None:
            return
        font = QtGui.QFont("Courier New", int(self.params['font_size'] * scale))
        painter.setFont(font)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, False)
        H, W = self.ascii_symbols.shape
        char_w = self.char_w * scale
        line_h = self.line_h * scale
        font_size_scaled = self.params['font_size'] * scale
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
                    x * char_w,
                    y * line_h + font_size_scaled,
                    ch
                )

    def _save_pdf_fpdf(self, full_path):
        if FPDF is None:
            raise RuntimeError("fpdf2 not available")
        try:
            pdf = FPDF(unit="mm", format="A4")
            pdf.add_page()
            # Точная настройка под Courier New: 2.1 мм на символ по X, 3.5 мм по Y
            mm_per_char_x = 2.1
            mm_per_char_y = 3.5
            content_w = self.params['ascii_w'] * mm_per_char_x
            content_h = self.params['ascii_h'] * mm_per_char_y
            x0 = (210 - content_w) / 2
            y0 = (297 - content_h) / 2
            pdf.set_font("Courier", size=self.params['font_size'] * 0.8)
            bg = (255, 255, 255) if self.params['invert'] else (0, 0, 0)
            pdf.set_fill_color(*bg)
            pdf.rect(0, 0, 210, 297, "F")
            H, W = self.ascii_symbols.shape
            for y in range(H):
                for x in range(W):
                    ch = self.ascii_symbols[y, x]
                    if not ch.strip():
                        continue
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
                    pdf.set_text_color(r, g, b)
                    pdf.text(x0 + x * mm_per_char_x, y0 + y * mm_per_char_y + 3, ch)
            # ✅ Прямая запись — в Pydroid 3 работает в ~/ и Download/
            pdf.output(full_path)
            return True
        except Exception as e:
            print("FPDF save error:", e)
            traceback.print_exc()
            return False

    def save_frame(self, fmt="png", quality=95, scale=2):
        if self.ascii_symbols is None:
            return False, ""
        timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
        filename = f"ascii_{timestamp}.{fmt}"
        full_path = os.path.join(SAVE_DIR, filename)
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
        except Exception as e:
            print("Mkdir error:", e)
            return False, full_path
        try:
            if fmt == "pdf":
                success = self._save_pdf_fpdf(full_path)
                return success, full_path
            elif fmt in ("png", "jpg"):
                w_px = int(self.params['ascii_w'] * self.char_w * scale)
                h_px = int(self.params['ascii_h'] * self.line_h * scale)
                img = QtGui.QImage(w_px, h_px, QtGui.QImage.Format_RGB888)
                bg = QtCore.Qt.black if not self.params['invert'] else QtCore.Qt.white
                img.fill(bg)
                painter = QtGui.QPainter(img)
                painter.scale(scale, scale)
                self._render_to_painter(painter, scale=1.0)
                painter.end()
                if fmt == "png":
                    success = img.save(full_path, "PNG")
                else:
                    success = img.save(full_path, "JPG", quality=quality)
                return bool(success), full_path
            else:
                return False, full_path
        except Exception as e:
            print("Save error:", e)
            traceback.print_exc()
            return False, full_path

    def save_current_frame_txt(self):
        if self.ascii_symbols is None:
            return False, ""
        timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
        filename = f"ascii_{timestamp}.txt"
        full_path = os.path.join(SAVE_DIR, filename)
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
        except Exception as e:
            print("Mkdir error:", e)
            return False, full_path
        lines = ["".join(row) for row in self.ascii_symbols]
        text = "\n".join(lines)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True, full_path
        except Exception as e:
            print("TXT save error:", e)
            return False, full_path

    def get_text_ascii(self):
        if self.ascii_symbols is None:
            return ""
        return "\n".join("".join(row) for row in self.ascii_symbols)

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)

# ───────────────────────────────────────────────────────────────

class SaveDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💾 Save As")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        fmt_layout = QtWidgets.QHBoxLayout()
        fmt_layout.addWidget(QtWidgets.QLabel("Format:"))
        self.radio_png = QtWidgets.QRadioButton("PNG (lossless)")
        self.radio_jpg = QtWidgets.QRadioButton("JPEG (95% quality)")
        self.radio_pdf = QtWidgets.QRadioButton("PDF (A4, vector)")
        self.radio_png.setChecked(True)
        fmt_layout.addWidget(self.radio_png)
        fmt_layout.addWidget(self.radio_jpg)
        fmt_layout.addWidget(self.radio_pdf)
        layout.addLayout(fmt_layout)

        scale_layout = QtWidgets.QHBoxLayout()
        scale_layout.addWidget(QtWidgets.QLabel("HD Scale:"))
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scale_slider.setRange(1, 4)
        self.scale_slider.setValue(2)
        self.scale_label = QtWidgets.QLabel("2×")
        self.scale_slider.valueChanged.connect(lambda v: self.scale_label.setText(f"{v}×"))
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_label)
        layout.addLayout(scale_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.ok_btn = QtWidgets.QPushButton("✅ Save")
        self.cancel_btn = QtWidgets.QPushButton("❌ Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_settings(self):
        if self.radio_png.isChecked():
            fmt = "png"
        elif self.radio_jpg.isChecked():
            fmt = "jpg"
        else:
            fmt = "pdf"
        return {'format': fmt, 'scale': self.scale_slider.value()}

# ───────────────────────────────────────────────────────────────

class ControlPanel(QtWidgets.QWidget):
    params_changed = QtCore.Signal(int, int, float, int, bool, bool, bool, str, bool)
    save_image = QtCore.Signal()
    save_txt = QtCore.Signal()
    copy_text = QtCore.Signal()
    fullscreen_requested = QtCore.Signal()
    theme_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._block_signals = False
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.width_slider = self._make_slider("Width", 20, 120, DEFAULTS['width'], "chars")
        self.height_slider = self._make_slider("Height", 10, 70, DEFAULTS['height'], "chars")

        # 🔑 Новая кнопка: Lock Aspect Ratio
        self.aspect_lock_cb = QtWidgets.QCheckBox("🔒 Lock H = W × 0.55")
        self.aspect_lock_cb.setChecked(DEFAULTS['lock_aspect'])
        self.aspect_lock_cb.stateChanged.connect(self._on_aspect_lock_changed)

        self.contrast_slider = self._make_slider("Contrast", 0.5, 3.0, DEFAULTS['contrast'], "", factor=100)
        self.font_slider = self._make_slider("Font size", 6, 20, DEFAULTS['font_size'], "pt")

        char_layout = QtWidgets.QHBoxLayout()
        char_label = QtWidgets.QLabel("Char set:")
        char_layout.addWidget(char_label)
        self.char_combo = QtWidgets.QComboBox()
        self.char_combo.addItems(list(CHAR_SETS.keys()))
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
        self.save_img_btn = QtWidgets.QPushButton("💾 Save Image...")
        self.save_txt_btn = QtWidgets.QPushButton("📄 Save TXT")
        self.copy_btn = QtWidgets.QPushButton("📋 Copy text")
        self.fullscreen_btn = QtWidgets.QPushButton("⛶ Fullscreen")
        self.theme_btn = QtWidgets.QPushButton("🌓")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.setToolTip("Theme: Auto → Dark → Light")

        btn_layout.addWidget(self.save_img_btn)
        btn_layout.addWidget(self.save_txt_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.fullscreen_btn)
        btn_layout.addWidget(self.theme_btn)

        layout.addLayout(self.width_slider['layout'])
        layout.addLayout(self.height_slider['layout'])
        layout.addWidget(self.aspect_lock_cb)  # ← добавлена кнопка
        layout.addLayout(self.contrast_slider['layout'])
        layout.addLayout(self.font_slider['layout'])
        layout.addLayout(char_layout)
        layout.addLayout(toggle_layout)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.width_slider['slider'].valueChanged.connect(self._on_width_changed)
        self.height_slider['slider'].valueChanged.connect(self._on_height_changed)
        self.contrast_slider['slider'].valueChanged.connect(self._emit_params)
        self.font_slider['slider'].valueChanged.connect(self._emit_params)
        self.char_combo.currentTextChanged.connect(self._emit_params)
        self.color_cb.stateChanged.connect(self._emit_params)
        self.invert_cb.stateChanged.connect(self._emit_params)
        self.auto_contrast_cb.stateChanged.connect(self._emit_params)

        self.save_img_btn.clicked.connect(self.save_image)
        self.save_txt_btn.clicked.connect(self.save_txt)
        self.copy_btn.clicked.connect(self.copy_text)
        self.fullscreen_btn.clicked.connect(self.fullscreen_requested)
        self.theme_btn.clicked.connect(self.theme_requested)

    def _make_slider(self, name, min_v, max_v, default, suffix="", factor=1):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(int(min_v * factor))
        slider.setMaximum(int(max_v * factor))
        slider.setValue(int(default * factor))
        slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        label_name = QtWidgets.QLabel(name + ":")
        label_val = QtWidgets.QLabel(f"{default}{suffix}")
        slider.valueChanged.connect(lambda v: label_val.setText(f"{v/factor:.1f}{suffix}"))
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label_name)
        layout.addWidget(slider)
        layout.addWidget(label_val)
        return {'slider': slider, 'label': label_val, 'layout': layout, 'factor': factor}

    def _on_width_changed(self, value):
        if self._block_signals:
            return
        w = value
        if self.aspect_lock_cb.isChecked():
            self._block_signals = True
            h = max(10, min(70, int(w * 0.55)))
            self.height_slider['slider'].setValue(h)
            self._block_signals = False
        self._emit_params()

    def _on_height_changed(self, value):
        if self._block_signals:
            return
        h = value
        if self.aspect_lock_cb.isChecked():
            self._block_signals = True
            w = max(20, min(120, int(h / 0.55)))
            self.width_slider['slider'].setValue(w)
            self._block_signals = False
        self._emit_params()

    def _on_aspect_lock_changed(self, state):
        self._emit_params()

    def _emit_params(self):
        w = self.width_slider['slider'].value()
        h = self.height_slider['slider'].value()
        contrast = self.contrast_slider['slider'].value() / 100.0
        font = self.font_slider['slider'].value()
        use_color = self.color_cb.isChecked()
        invert = self.invert_cb.isChecked()
        auto_contrast = self.auto_contrast_cb.isChecked()
        char_set = self.char_combo.currentText()
        lock_aspect = self.aspect_lock_cb.isChecked()
        self.params_changed.emit(w, h, contrast, font, use_color, invert, auto_contrast, char_set, lock_aspect)

    def update_theme_button(self, mode):
        theme_manager = ThemeManager()
        self.theme_btn.setText(theme_manager.get_icon_for_mode(mode))

    def sync_width(self, w):
        if not self._block_signals:
            self._block_signals = True
            self.width_slider['slider'].setValue(w)
            self._block_signals = False

    def sync_height(self, h):
        if not self._block_signals:
            self._block_signals = True
            self.height_slider['slider'].setValue(h)
            self._block_signals = False

# ───────────────────────────────────────────────────────────────

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_current_theme()
        self.setWindowTitle("📺 ASCII Camera Pro")
        self.resize(800, 600)

        self.camera_widget = ASCIICameraWidget()
        self.control_panel = ControlPanel()
        self.control_panel.update_theme_button(self.theme_manager._current_mode)

        # Подключаем синхронизацию высоты ↔ ширины
        self.camera_widget.set_notify_height_callback(self.control_panel.sync_height)
        self.camera_widget.set_notify_width_callback(self.control_panel.sync_width)

        self.status_label = QtWidgets.QLabel("FPS: 0.0 | ASCII: ?×? | Mode: —")
        self.statusBar().addWidget(self.status_label)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.camera_widget)
        splitter.addWidget(self.control_panel)
        splitter.setSizes([700, 220])
        layout.addWidget(splitter)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.control_panel.params_changed.connect(self.on_params_changed, type=QtCore.Qt.DirectConnection)
        self.control_panel.save_image.connect(self.save_image_dialog)
        self.control_panel.save_txt.connect(self.save_txt)
        self.control_panel.copy_text.connect(self.copy_text)
        self.control_panel.fullscreen_requested.connect(self.toggle_fullscreen)
        self.control_panel.theme_requested.connect(self.cycle_theme)
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

        self.status_timer = QtCore.QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(500)

        self.orientation_timer = QtCore.QTimer()
        self.orientation_timer.timeout.connect(self.check_orientation)
        self.orientation_timer.start(2000)

        self.shortcut_fullscreen = QtGui.QShortcut(QtGui.QKeySequence("F11"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        self.shortcut_save_img = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.shortcut_save_img.activated.connect(self.save_image_dialog)
        self.shortcut_theme = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), self)
        self.shortcut_theme.activated.connect(self.cycle_theme)

    def on_theme_changed(self, mode):
        self.control_panel.update_theme_button(mode)

    def cycle_theme(self):
        self.theme_manager.cycle_mode()

    def on_params_changed(self, w, h, contrast, font_size, use_color, invert, auto_contrast, char_set_name, lock_aspect):
        self.camera_widget.update_params(
            ascii_w=w, ascii_h=h, contrast=contrast, font_size=font_size,
            use_color=use_color, invert=invert, auto_contrast=auto_contrast,
            char_set_name=char_set_name, lock_aspect=lock_aspect
        )

    def check_orientation(self):
        screen = self.screen()
        geo = screen.geometry()
        w, h = geo.width(), geo.height()
        is_landscape = w > h
        # 🔑 Используем корректное соотношение 1.0 / 0.55 ≈ 1.82
        target_ratio = 1.82 if is_landscape else 1.0
        new_h = min(45, max(20, self.camera_widget.params['ascii_h']))
        new_w = int(new_h * target_ratio)
        new_w = max(20, min(120, new_w))
        if abs(new_w - self.camera_widget.params['ascii_w']) > 3 or abs(new_h - self.camera_widget.params['ascii_h']) > 2:
            self.camera_widget.update_params(ascii_w=new_w, ascii_h=new_h)
            self.control_panel.sync_width(new_w)
            self.control_panel.sync_height(new_h)

    def update_status(self):
        mode = self.camera_widget.params['char_set_name']
        w = self.camera_widget.params['ascii_w']
        h = self.camera_widget.params['ascii_h']
        lock = "🔒" if self.camera_widget.params['lock_aspect'] else "🔓"
        self.status_label.setText(f"FPS: {self.camera_widget.fps:.1f} | ASCII: {w}×{h} {lock} | Mode: {mode}")

    def save_image_dialog(self):
        dialog = SaveDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            settings = dialog.get_settings()
            if settings['format'] == 'pdf' and FPDF is None:
                QtWidgets.QMessageBox.critical(
                    self, "❌ fpdf2 missing",
                    "Install fpdf2:\nSettings → Pip → Search 'fpdf2' → Install"
                )
                return
            success, path = self.camera_widget.save_frame(
                fmt=settings['format'],
                scale=settings['scale']
            )
            self._show_save_result(success, settings['format'].upper(), path)

    def save_txt(self):
        success, path = self.camera_widget.save_current_frame_txt()
        self._show_save_result(success, "TXT", path)

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
            msg = f"Saved to:\n{path}"
            if sys.platform == "linux" and "ANDROID_ROOT" in os.environ:
                msg += "\n\nOpen in Pydroid: Files → Home → ASCII_Camera"
            QtWidgets.QMessageBox.information(self, f"✅ {fmt} Saved", msg)
        else:
            QtWidgets.QMessageBox.critical(
                self, f"❌ {fmt} Error",
                f"Failed to save {fmt} file.\nPath tried:\n{path}\n\nCheck permissions or try another location."
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

# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    font = QtGui.QFont()
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
