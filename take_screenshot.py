#!/usr/bin/env python3
"""Script to launch the app in demo mode and capture a screenshot."""

import sys
import os

# Force demo mode and use offscreen platform
os.environ['OMADA_DEMO'] = '1'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QScreen

# Import after setting demo mode env var
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omada_monitor import OmadaClientMonitor, DARK_STYLESHEET


def capture_screenshot():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_STYLESHEET)

    window = OmadaClientMonitor(demo_mode=True)
    window.show()

    def take_screenshot():
        # Wait for data to load and render
        screen = window.grab()
        screen.save('screenshot.png', 'PNG')
        print(f"Screenshot saved to screenshot.png")
        app.quit()

    # Take screenshot after 2 seconds (give time for data to load)
    QTimer.singleShot(2000, take_screenshot)

    sys.exit(app.exec())


if __name__ == '__main__':
    capture_screenshot()
