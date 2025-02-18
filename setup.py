# setup.py
from setuptools import setup
import os
import shutil

# Clean function
def clean_builds():
    dirs_to_clean = ['build', 'dist']
    files_to_clean = [f for f in os.listdir('.') if f.endswith('.pyc') or f.endswith('.pyo') or f.endswith('.egg-info')]
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
    
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)

# Clean previous builds
clean_builds()

APP = ['omada_monitor.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,  # Disable argv emulation
    'packages': [
        'PyQt6',
        'cryptography',
        'omada',
    ],
    'includes': [
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
    ],
    'excludes': [
        'tkinter',
        'Carbon',
        'pytest',
        '_pytest',
    ],
    'iconfile': 'app_icon.icns',
    'plist': {
        'CFBundleName': "Omada Monitor",
        'CFBundleDisplayName': "Omada Monitor",
        'CFBundleGetInfoString': "Monitor Omada network clients",
        'CFBundleIdentifier': "com.wlan1.omadamonitor",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.15',
        'NSHumanReadableCopyright': "Copyright © 2025, wlan1, All Rights Reserved"
    }
}

setup(
    name="Omada Monitor",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app>=0.28.0'],
)