"""
py2app setup script for Atlas
Creates a native macOS application bundle

Usage:
    python3 setup_app.py py2app
"""

from setuptools import setup

APP = ['atlas/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'atlas',
        'psutil',
        'speedtest',
    ],
    'includes': [
        'subprocess',
        'threading',
        'http.server',
        'socketserver',
        'json',
        'logging',
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
    ],
    'plist': {
        'CFBundleName': 'Atlas',
        'CFBundleDisplayName': 'Atlas Dashboard',
        'CFBundleIdentifier': 'com.company.atlas',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'LSMinimumSystemVersion': '10.15',
        'LSUIElement': False,  # Set to True to hide from Dock
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'CFBundleDocumentTypes': [],
        'NSHumanReadableCopyright': 'Copyright © 2025. All rights reserved.',
    },
    'iconfile': None,  # Add 'icon.icns' if you have an icon
}

setup(
    name='Atlas',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'psutil',
        'speedtest-cli',
    ],
)
