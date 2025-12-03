# 📺 ASCII Camera Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PySide6](https://img.shields.io/badge/PySide6-6.x+-orange)]()
[![Android](https://img.shields.io/badge/Android-Pydroid3-brightgreen)]()

A real-time **ASCII art camera** for Android (via Pydroid 3) and desktop. Renders live video as stylized ASCII art — with color, newspaper-style, or block-element output.


---

## ✨ Features

- 🎨 **Three ASCII styles**:
  - `Detailed`: 27-character set for smooth gradients
  - `Newspaper`: 8-character set for high-contrast print-style
  - `Block`: Unicode blocks (`█▒░ `) for bold, pixel-art look
  - `Dot`: Unicode dots (`.`) for dot look
- 📲 **Android-ready** (tested on Pydroid 3)
- 🖥️ **Desktop compatible** (Windows, Linux, macOS)
- 🎚️ Real-time controls:
  - Width / Height (ASCII resolution)
  - Contrast & Auto-contrast
  - Font size
  - Color / Monochrome / Invert
- 💾 Export:
  - `PNG` image (rendered with font)
  - `TXT` pure ASCII (for terminals, sharing, art)
  - Copy ASCII text to clipboard
- 🔄 **Auto-orientation**: adjusts ASCII grid for portrait/landscape
- 🌓 Dark theme & responsive UI

---

## 🚀 Quick Start (Pydroid 3 on Android)

1. Install **[Pydroid 3](https://play.google.com/store/apps/details?id=ru.iiec.pydroid3)**  
2. In Pydroid:  
   - `pip install opencv-python numpy Pillow PySide6-Essentials`  
   *(Note: On some devices, use `opencv-python-headless` if camera fails — but GUI won’t work)*  
3. Create `ascii_camera.py` and paste the script above  
4. Run! Grant camera permission when prompted.

> ✅ **Pro tip**: Use **landscape mode** for wider ASCII (e.g. 80×40).

---

## 🖥️ Desktop Installation

```bash
git clone https://github.com/yourname/ascii-camera-pro.git
cd ascii-camera-pro
pip install -r requirements.txt
python ascii_camera.py
```


## 🌟 Inspired by
jpventer/ascii-webcam
ThePracticalDev/ASCII-Camera

## ✨ Contribution welcome! Open an issue or PR for:

New char sets (Braille, emoji?)
Video recording
QR-code overlay
SSH terminal mode

## MIT License

Copyright (c) 2025 Vasily Popkine

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
