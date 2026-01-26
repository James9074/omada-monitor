#!/usr/bin/env python3

import sys
import os
import json
import re
import random
import collections
import base64

# Check for demo mode early (before conditional imports)
DEMO_MODE = '--demo' in sys.argv or os.environ.get('OMADA_DEMO') == '1'

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                           QLabel, QStatusBar, QHeaderView, QDialog, QLineEdit,
                           QFormLayout, QMessageBox, QCheckBox, QFrame, QGraphicsOpacityEffect,
                           QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation, QEasingCurve, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon

# Only import Omada and cryptography when not in demo mode
if not DEMO_MODE:
    from omada import Omada
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
else:
    # Dummy placeholders for demo mode
    Omada = None
    Fernet = None


class MockOmada:
    """Mock Omada controller for demo/testing purposes"""

    MOCK_CLIENTS = [
        {'name': 'iPhone 14 Pro', 'ip': '192.168.1.101', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Living Room AP', 'activity': 2500000,
         'trafficDown': 15000000000, 'trafficUp': 3200000000, 'uptime': 345600},
        {'name': 'MacBook Pro', 'ip': '192.168.1.102', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Office AP', 'activity': 8500000,
         'trafficDown': 125000000000, 'trafficUp': 28000000000, 'uptime': 604800},
        {'name': 'iPad Air', 'ip': '192.168.1.103', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Living Room AP', 'activity': 1200000,
         'trafficDown': 8500000000, 'trafficUp': 950000000, 'uptime': 172800},
        {'name': 'Samsung Smart TV', 'ip': '192.168.1.150', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Living Room AP', 'activity': 25000000,
         'trafficDown': 450000000000, 'trafficUp': 2500000000, 'uptime': 1209600},
        {'name': 'PlayStation 5', 'ip': '192.168.1.151', 'active': True, 'connectDevType': 'switch',
         'networkName': 'Gaming VLAN', 'switchName': 'Main Switch', 'port': 3, 'activity': 15000000,
         'trafficDown': 850000000000, 'trafficUp': 125000000000, 'uptime': 86400},
        {'name': 'Work Laptop', 'ip': '192.168.1.104', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Office AP', 'activity': 5500000,
         'trafficDown': 95000000000, 'trafficUp': 18000000000, 'uptime': 432000},
        {'name': 'Smart Thermostat', 'ip': '192.168.1.200', 'active': True, 'connectDevType': 'ap',
         'ssid': 'IoT_Network', 'apName': 'Basement AP', 'activity': 15000,
         'trafficDown': 125000000, 'trafficUp': 85000000, 'uptime': 2592000},
        {'name': 'Ring Doorbell', 'ip': '192.168.1.201', 'active': True, 'connectDevType': 'ap',
         'ssid': 'IoT_Network', 'apName': 'Living Room AP', 'activity': 850000,
         'trafficDown': 28000000000, 'trafficUp': 15000000000, 'uptime': 2592000},
        {'name': 'Philips Hue Bridge', 'ip': '192.168.1.202', 'active': True, 'connectDevType': 'switch',
         'networkName': 'IoT VLAN', 'switchName': 'Main Switch', 'port': 8, 'activity': 5000,
         'trafficDown': 50000000, 'trafficUp': 25000000, 'uptime': 5184000},
        {'name': 'Guest iPhone', 'ip': '192.168.2.50', 'active': True, 'connectDevType': 'ap',
         'ssid': 'GuestNetwork', 'apName': 'Living Room AP', 'activity': 3500000,
         'trafficDown': 2500000000, 'trafficUp': 450000000, 'uptime': 7200},
        {'name': 'Sonos Speaker', 'ip': '192.168.1.160', 'active': True, 'connectDevType': 'ap',
         'ssid': 'HomeNetwork', 'apName': 'Living Room AP', 'activity': 2000000,
         'trafficDown': 85000000000, 'trafficUp': 1500000000, 'uptime': 1814400},
        {'name': 'NAS Server', 'ip': '192.168.1.10', 'active': True, 'connectDevType': 'switch',
         'networkName': 'Server VLAN', 'switchName': 'Main Switch', 'port': 1, 'activity': 45000000,
         'trafficDown': 2500000000000, 'trafficUp': 1800000000000, 'uptime': 7776000},
    ]

    def __init__(self, baseurl=None, site=None, verify=False):
        self.baseurl = baseurl or "https://demo.omada.local"
        self.site = site or "Demo Site"

    def login(self, username=None, password=None):
        pass  # Always succeeds in demo mode

    def logout(self):
        pass

    def getSiteClients(self):
        """Return mock clients with slightly randomized activity"""
        clients = []
        for client in self.MOCK_CLIENTS:
            c = client.copy()
            # Add some variance to activity
            c['activity'] = int(c['activity'] * random.uniform(0.7, 1.3))
            clients.append(c)
        return clients


# Modern Dark Theme Stylesheet
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    background-color: #1a1a2e;
    color: #eaeaea;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    color: #eaeaea;
    padding: 2px;
}

QLabel#statusLabel {
    font-size: 14px;
    font-weight: 500;
    padding: 8px 12px;
    border-radius: 6px;
    background-color: #16213e;
}

QLabel#statusLabel[status="connected"] {
    color: #4ade80;
    border-left: 3px solid #4ade80;
}

QLabel#statusLabel[status="disconnected"] {
    color: #f87171;
    border-left: 3px solid #f87171;
}

QLabel#statusLabel[status="loading"] {
    color: #60a5fa;
    border-left: 3px solid #60a5fa;
}

QLabel#emptyStateLabel {
    font-size: 16px;
    color: #6b7280;
    padding: 40px;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: 600;
    color: #ffffff;
}

QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #374151;
    color: #6b7280;
}

QPushButton#secondaryButton {
    background-color: #374151;
    color: #e5e7eb;
}

QPushButton#secondaryButton:hover {
    background-color: #4b5563;
}

QPushButton#refreshButton {
    background-color: #10b981;
}

QPushButton#refreshButton:hover {
    background-color: #059669;
}

QPushButton#refreshButton:disabled {
    background-color: #374151;
}

QLineEdit {
    background-color: #16213e;
    border: 2px solid #374151;
    border-radius: 6px;
    padding: 8px 12px;
    color: #eaeaea;
    selection-background-color: #3b82f6;
}

QLineEdit:focus {
    border-color: #3b82f6;
}

QLineEdit:disabled {
    background-color: #1f2937;
    color: #6b7280;
}

QLineEdit[valid="false"] {
    border-color: #ef4444;
}

QLineEdit[valid="true"] {
    border-color: #10b981;
}

QCheckBox {
    spacing: 8px;
    color: #e5e7eb;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #374151;
    background-color: #16213e;
}

QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1e2a47;
    border: 1px solid #374151;
    border-radius: 8px;
    gridline-color: #374151;
    selection-background-color: #3b82f6;
    selection-color: white;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #2d3748;
}

QTableWidget::item:selected {
    background-color: #3b82f6;
}

QTableWidget::item:hover {
    background-color: #2d3a5c;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 8px;
    border: none;
    border-bottom: 2px solid #374151;
}

QHeaderView::section:hover {
    background-color: #1e293b;
    color: #e2e8f0;
}

QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #374151;
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4b5563;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1a1a2e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #374151;
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4b5563;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QStatusBar {
    background-color: #0f172a;
    color: #94a3b8;
    border-top: 1px solid #374151;
    padding: 4px 8px;
}

QDialog {
    background-color: #1a1a2e;
}

QMessageBox {
    background-color: #1a1a2e;
}

QMessageBox QLabel {
    color: #eaeaea;
}

QFrame#separator {
    background-color: #374151;
    max-height: 1px;
}

QFrame#card {
    background-color: #16213e;
    border-radius: 8px;
    border: 1px solid #374151;
}

/* Search box specific styling */
QLineEdit#searchBox {
    background-color: #16213e;
    border: 2px solid #374151;
    border-radius: 20px;
    padding: 8px 16px 8px 36px;
    min-width: 250px;
}

QLineEdit#searchBox:focus {
    border-color: #3b82f6;
}
"""


class CredentialManager:
    def __init__(self):
        # Skip initialization in demo mode
        if DEMO_MODE:
            self.fernet = None
            return

        self.config_dir = os.path.expanduser('~/.omada-monitor')
        self.config_file = os.path.join(self.config_dir, 'credentials.enc')
        self.key_file = os.path.join(self.config_dir, 'key')

        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)

        if not os.path.exists(self.key_file):
            self._generate_key()
        else:
            with open(self.key_file, 'rb') as f:
                self.key = f.read()

        self.fernet = Fernet(self.key)

    def _generate_key(self):
        self.key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(self.key)
        os.chmod(self.key_file, 0o600)

    def save_credentials(self, username, password, baseurl, site, verify):
        if DEMO_MODE:
            return  # Don't save in demo mode

        data = {
            'username': username,
            'password': password,
            'baseurl': baseurl,
            'site': site,
            'verify': verify
        }
        encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
        with open(self.config_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(self.config_file, 0o600)

    def load_credentials(self):
        if DEMO_MODE:
            return None, None, None, None, False

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'rb') as f:
                    encrypted_data = f.read()
                data = json.loads(self.fernet.decrypt(encrypted_data))
                return (
                    data.get('username'),
                    data.get('password'),
                    data.get('baseurl'),
                    data.get('site'),
                    data.get('verify', False)
                )
        except Exception as e:
            print(f"Error loading credentials: {e}")
        return None, None, None, None, False


class DataRefreshWorker(QThread):
    """Worker thread for refreshing data without blocking UI"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, omada):
        super().__init__()
        self.omada = omada

    def run(self):
        try:
            clients = list(self.omada.getSiteClients())
            self.finished.emit(clients)
        except Exception as e:
            self.error.emit(str(e))


class SortableIPItem(QTableWidgetItem):
    def __init__(self, display_text, ip_addr):
        super().__init__(display_text)
        self.ip_addr = ip_addr
        self.sort_key = self._ip_to_int(ip_addr)

    def _ip_to_int(self, ip):
        try:
            if ip in ('--', '', None):
                return (-1, -1, -1, -1)
            octets = ip.split('.')
            if len(octets) != 4:
                return (-1, -1, -1, -1)
            return tuple(int(octet) for octet in octets)
        except (ValueError, AttributeError):
            return (-1, -1, -1, -1)

    def __lt__(self, other):
        if hasattr(other, 'sort_key'):
            return self.sort_key < other.sort_key
        return super().__lt__(other)


class SortableTableItem(QTableWidgetItem):
    def __init__(self, display_text, sort_key):
        super().__init__(display_text)
        self.sort_key = sort_key

    def __lt__(self, other):
        try:
            return self.sort_key < other.sort_key
        except (TypeError, AttributeError):
            return super().__lt__(other)


class ValidationError:
    """Container for validation error information"""
    def __init__(self, field, message):
        self.field = field
        self.message = message


class LoginDialog(QDialog):
    def __init__(self, parent=None, saved_username="", saved_password="",
                 saved_baseurl="", saved_site="", saved_verify=False):
        super().__init__(parent)
        self.setWindowTitle("Omada Controller Login")
        self.setMinimumWidth(450)
        self.setModal(True)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title_label = QLabel("Connect to Omada Controller")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle = QLabel("Enter your controller credentials to continue")
        subtitle.setStyleSheet("color: #6b7280; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(8)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Create widgets with validation
        self.baseurl = QLineEdit(saved_baseurl or "")
        self.baseurl.setPlaceholderText("https://omada.example.com:8043")
        self.baseurl.textChanged.connect(self._validate_url)

        self.username = QLineEdit(saved_username or "")
        self.username.setPlaceholderText("admin")
        self.username.textChanged.connect(self._validate_username)

        self.password = QLineEdit(saved_password or "")
        self.password.setPlaceholderText("••••••••")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.textChanged.connect(self._validate_password)

        self.site = QLineEdit(saved_site or "Default")
        self.site.setPlaceholderText("Default")
        self.site.textChanged.connect(self._validate_site)

        self.verify = QCheckBox("Verify SSL Certificate")
        self.verify.setChecked(saved_verify)

        # Error labels
        self.url_error = QLabel()
        self.url_error.setStyleSheet("color: #ef4444; font-size: 11px; padding-left: 2px;")
        self.url_error.hide()

        self.username_error = QLabel()
        self.username_error.setStyleSheet("color: #ef4444; font-size: 11px; padding-left: 2px;")
        self.username_error.hide()

        self.password_error = QLabel()
        self.password_error.setStyleSheet("color: #ef4444; font-size: 11px; padding-left: 2px;")
        self.password_error.hide()

        self.site_error = QLabel()
        self.site_error.setStyleSheet("color: #ef4444; font-size: 11px; padding-left: 2px;")
        self.site_error.hide()

        # Add to form
        form_layout.addRow("Base URL:", self.baseurl)
        form_layout.addRow("", self.url_error)
        form_layout.addRow("Username:", self.username)
        form_layout.addRow("", self.username_error)
        form_layout.addRow("Password:", self.password)
        form_layout.addRow("", self.password_error)
        form_layout.addRow("Site:", self.site)
        form_layout.addRow("", self.site_error)
        form_layout.addRow("", self.verify)

        main_layout.addLayout(form_layout)

        main_layout.addSpacing(8)

        # General error label
        self.general_error = QLabel()
        self.general_error.setStyleSheet("""
            color: #fca5a5;
            background-color: rgba(239, 68, 68, 0.1);
            border: 1px solid #ef4444;
            border-radius: 6px;
            padding: 10px;
            font-size: 12px;
        """)
        self.general_error.setWordWrap(True)
        self.general_error.hide()
        main_layout.addWidget(self.general_error)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)

        self.login_button = QPushButton("Connect")
        self.login_button.clicked.connect(self._attempt_login)
        self.login_button.setDefault(True)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.login_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.credential_manager = CredentialManager()
        self.omada = None
        self._login_successful = False

    def _validate_url(self):
        url = self.baseurl.text().strip()
        if not url:
            self._show_field_error(self.baseurl, self.url_error, "URL is required")
            return False

        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            self._show_field_error(self.baseurl, self.url_error, "Enter a valid URL (e.g., https://omada.example.com:8043)")
            return False

        self._clear_field_error(self.baseurl, self.url_error)
        return True

    def _validate_username(self):
        username = self.username.text().strip()
        if not username:
            self._show_field_error(self.username, self.username_error, "Username is required")
            return False
        if len(username) < 2:
            self._show_field_error(self.username, self.username_error, "Username must be at least 2 characters")
            return False

        self._clear_field_error(self.username, self.username_error)
        return True

    def _validate_password(self):
        password = self.password.text()
        if not password:
            self._show_field_error(self.password, self.password_error, "Password is required")
            return False

        self._clear_field_error(self.password, self.password_error)
        return True

    def _validate_site(self):
        site = self.site.text().strip()
        if not site:
            self._show_field_error(self.site, self.site_error, "Site name is required")
            return False

        self._clear_field_error(self.site, self.site_error)
        return True

    def _show_field_error(self, field, error_label, message):
        field.setProperty("valid", "false")
        field.style().unpolish(field)
        field.style().polish(field)
        error_label.setText(message)
        error_label.show()

    def _clear_field_error(self, field, error_label):
        field.setProperty("valid", "true")
        field.style().unpolish(field)
        field.style().polish(field)
        error_label.hide()

    def _validate_all(self):
        """Validate all fields and return True if all pass"""
        valid = True
        valid = self._validate_url() and valid
        valid = self._validate_username() and valid
        valid = self._validate_password() and valid
        valid = self._validate_site() and valid
        return valid

    def _attempt_login(self):
        """Attempt to login with current credentials"""
        self.general_error.hide()

        if not self._validate_all():
            return

        # Disable form during login
        self._set_form_enabled(False)
        self.login_button.setText("Connecting...")

        # Process events to show the disabled state
        QApplication.processEvents()

        try:
            self.omada = Omada(
                baseurl=self.baseurl.text().strip(),
                site=self.site.text().strip(),
                verify=self.verify.isChecked()
            )
            self.omada.login(
                username=self.username.text().strip(),
                password=self.password.text()
            )

            # Save credentials only after successful login
            self.credential_manager.save_credentials(
                self.username.text().strip(),
                self.password.text(),
                self.baseurl.text().strip(),
                self.site.text().strip(),
                self.verify.isChecked()
            )

            self._login_successful = True
            self.accept()

        except Exception as e:
            error_msg = str(e)

            # Provide more specific error messages
            if "Connection refused" in error_msg or "Failed to establish" in error_msg:
                error_msg = "Could not connect to the controller. Please check the URL and ensure the controller is running."
            elif "401" in error_msg or "authentication" in error_msg.lower() or "password" in error_msg.lower():
                error_msg = "Invalid username or password. Please check your credentials."
            elif "SSL" in error_msg or "certificate" in error_msg.lower():
                error_msg = "SSL certificate verification failed. Try unchecking 'Verify SSL Certificate' for self-signed certificates."
            elif "timeout" in error_msg.lower():
                error_msg = "Connection timed out. The controller may be unreachable."
            elif "privilege" in error_msg.lower() or "site" in error_msg.lower():
                error_msg = f"Access denied to site '{self.site.text()}'. Please check the site name."

            self.general_error.setText(f"Connection failed: {error_msg}")
            self.general_error.show()

        finally:
            self._set_form_enabled(True)
            self.login_button.setText("Connect")

    def _set_form_enabled(self, enabled):
        self.baseurl.setEnabled(enabled)
        self.username.setEnabled(enabled)
        self.password.setEnabled(enabled)
        self.site.setEnabled(enabled)
        self.verify.setEnabled(enabled)
        self.login_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled)

    def get_omada(self):
        """Return the authenticated Omada instance"""
        return self.omada

    def was_successful(self):
        return self._login_successful


class OmadaClientMonitor(QMainWindow):
    FIELDDEF = collections.OrderedDict([
        ('name',        ('NAME',         20)),
        ('ip',          ('IP ADDRESS',   14)),
        ('active',      ('STATUS',       10)),
        ('networkName', ('SSID/NETWORK', 14)),
        ('port',        ('AP/PORT',      14)),
        ('activity',    ('ACTIVITY',     10)),
        ('trafficDown', ('DOWNLOAD',     10)),
        ('trafficUp',   ('UPLOAD',       10)),
        ('uptime',      ('UPTIME',       14)),
    ])

    def __init__(self, demo_mode=False):
        super().__init__()
        self.demo_mode = demo_mode
        title = "Omada Client Monitor"
        if demo_mode:
            title += " (Demo Mode)"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1300, 700)
        self.setMinimumWidth(900)
        self.setMinimumHeight(500)

        self.credential_manager = CredentialManager()
        self.omada = None
        self.refresh_worker = None
        self._all_clients = []  # Store all clients for filtering
        self._current_filter = ""

        # Attempt login (skip for demo mode)
        if not self._perform_login():
            sys.exit(1)

        self.setup_ui()

    def _perform_login(self):
        """Perform login with iterative retry instead of recursion"""
        # Use mock data in demo mode
        if self.demo_mode:
            self.omada = MockOmada()
            return True

        # First try auto-login
        if self._try_auto_login():
            return True

        # Show login dialog in a loop until success or cancel
        while True:
            saved_username, saved_password, saved_baseurl, saved_site, saved_verify = \
                self.credential_manager.load_credentials()

            dialog = LoginDialog(
                self, saved_username or "", saved_password or "",
                saved_baseurl or "", saved_site or "", saved_verify
            )

            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.was_successful():
                self.omada = dialog.get_omada()
                return True
            elif dialog.exec() != QDialog.DialogCode.Accepted:
                # User cancelled
                return False

    def _try_auto_login(self):
        """Attempt to login with saved credentials"""
        saved_username, saved_password, saved_baseurl, saved_site, saved_verify = \
            self.credential_manager.load_credentials()

        if all([saved_username, saved_password, saved_baseurl, saved_site is not None]):
            try:
                self.omada = Omada(
                    baseurl=saved_baseurl,
                    site=saved_site,
                    verify=saved_verify
                )
                self.omada.login(username=saved_username, password=saved_password)
                return True
            except Exception as e:
                print(f"Auto-login failed: {e}")
        return False

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header section
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Title and status
        title_status_layout = QVBoxLayout()
        title_status_layout.setSpacing(4)

        title_label = QLabel("Client Monitor")
        title_label.setObjectName("titleLabel")
        title_status_layout.addWidget(title_label)

        status_text = "Demo Mode - Sample Data" if self.demo_mode else "Connected to Omada Controller"
        self.status_label = QLabel(status_text)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("status", "connected")
        title_status_layout.addWidget(self.status_label)

        header_layout.addLayout(title_status_layout)
        header_layout.addStretch()

        # Search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search clients...")
        self.search_box.textChanged.connect(self._filter_clients)
        self.search_box.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_box)
        header_layout.addLayout(search_layout)

        header_layout.addSpacing(8)

        # Buttons
        self.login_button = QPushButton("Settings")
        self.login_button.setObjectName("secondaryButton")
        self.login_button.clicked.connect(self._show_login)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.clicked.connect(self.refresh_data)

        header_layout.addWidget(self.login_button)
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        # Stacked widget for table and empty state
        self.stack = QStackedWidget()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.FIELDDEF))
        self.table.setHorizontalHeaderLabels([field[0] for field in self.FIELDDEF.values()])

        header = self.table.horizontalHeader()
        total_width = sum(width for _, (_, width) in self.FIELDDEF.items())

        for col, (field, (_, width)) in enumerate(self.FIELDDEF.items()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            header.resizeSection(col, int(width * 100 / total_width))

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.stack.addWidget(self.table)

        # Empty state
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_label = QLabel("No clients connected")
        self.empty_label.setObjectName("emptyStateLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_subtitle = QLabel("Clients will appear here when they connect to your network")
        empty_subtitle.setStyleSheet("color: #4b5563; font-size: 13px;")
        empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addWidget(self.empty_label)
        empty_layout.addWidget(empty_subtitle)
        self.stack.addWidget(empty_widget)

        # Loading state
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_label = QLabel("Loading clients...")
        self.loading_label.setObjectName("emptyStateLabel")
        self.loading_label.setStyleSheet("color: #60a5fa; font-size: 16px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        self.stack.addWidget(loading_widget)

        layout.addWidget(self.stack)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Client count label in status bar
        self.client_count_label = QLabel()
        self.statusBar.addPermanentWidget(self.client_count_label)

        # Auto-refresh timer (every 30 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)

        # Initial data load
        self.refresh_data()

    def _show_login(self):
        """Show login dialog for settings changes"""
        saved_username, saved_password, saved_baseurl, saved_site, saved_verify = \
            self.credential_manager.load_credentials()

        dialog = LoginDialog(
            self, saved_username or "", saved_password or "",
            saved_baseurl or "", saved_site or "", saved_verify
        )

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.was_successful():
            self.omada = dialog.get_omada()
            self._update_status("connected", "Connected to Omada Controller")
            self.refresh_data()

    def _update_status(self, status, message):
        """Update the status label with proper styling"""
        self.status_label.setText(message)
        self.status_label.setProperty("status", status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _filter_clients(self, text):
        """Filter the table based on search text"""
        self._current_filter = text.lower()
        self._display_clients(self._all_clients)

    def _display_clients(self, clients):
        """Display clients in the table with optional filtering"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        # Filter clients if search text is present
        filtered_clients = clients
        if self._current_filter:
            filtered_clients = [
                c for c in clients
                if self._current_filter in c.get('name', '').lower()
                or self._current_filter in c.get('ip', '').lower()
                or self._current_filter in c.get('ssid', '').lower()
                or self._current_filter in c.get('networkName', '').lower()
                or self._current_filter in c.get('apName', '').lower()
            ]

        if not filtered_clients:
            if self._current_filter:
                self.empty_label.setText(f"No clients matching '{self._current_filter}'")
            else:
                self.empty_label.setText("No clients connected")
            self.stack.setCurrentIndex(1)  # Show empty state
            self.client_count_label.setText("")
            return

        self.stack.setCurrentIndex(0)  # Show table
        self.table.setRowCount(len(filtered_clients))

        for row, client in enumerate(filtered_clients):
            formatted_client = self.format_client_data(client)

            for col, (field, _) in enumerate(self.FIELDDEF.items()):
                item = self.create_table_item(field, formatted_client[field], client)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                # Color code the status
                if field == 'active':
                    if formatted_client[field] == 'CONNECTED':
                        item.setForeground(QColor('#4ade80'))
                    else:
                        item.setForeground(QColor('#6b7280'))

                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

        # Update client count
        total = len(clients)
        shown = len(filtered_clients)
        if self._current_filter:
            self.client_count_label.setText(f"Showing {shown} of {total} clients")
        else:
            self.client_count_label.setText(f"{total} client{'s' if total != 1 else ''} connected")

    def format_client_data(self, client):
        formatted = {}
        formatted['name'] = client.get('name', '--')
        formatted['ip'] = client.get('ip', '--')
        formatted['active'] = self.format_status(client.get('active', False))

        if client.get('connectDevType') == 'ap':
            formatted['networkName'] = client.get('ssid', '--')
        else:
            formatted['networkName'] = client.get('networkName', '--')

        formatted['port'] = self.format_port(client)
        formatted['activity'] = self.format_size(client.get('activity', 0), 'B/s')
        formatted['trafficDown'] = self.format_size(client.get('trafficDown', 0), 'B')
        formatted['trafficUp'] = self.format_size(client.get('trafficUp', 0), 'B')
        formatted['uptime'] = self.format_time(client.get('uptime', 0))

        return formatted

    @staticmethod
    def format_status(active):
        return 'CONNECTED' if active else '--'

    @staticmethod
    def format_port(client):
        if client.get('connectDevType') == 'ap':
            return client.get('apName', '--')
        elif 'switchName' in client and 'port' in client:
            return f"{client['switchName']} Port {client['port']}"
        return '--'

    @staticmethod
    def format_size(size, suffix='B'):
        try:
            size = float(size)
            for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
                if abs(size) < 1000.0:
                    return f'{size:.1f} {unit}{suffix}'
                size /= 1000.0
            return f'{size:.1f} Y{suffix}'
        except (TypeError, ValueError):
            return '--'

    @staticmethod
    def format_time(seconds):
        try:
            seconds = int(seconds)
            if seconds <= 0:
                return '--'
            d = seconds // (3600 * 24)
            h = seconds // 3600 % 24
            m = seconds % 3600 // 60
            s = seconds % 3600 % 60
            if d > 0: return f'{d}d {h}:{m:02d}:{s:02d}'
            if h > 0: return f'{h}:{m:02d}:{s:02d}'
            if m > 0: return f'{m:02d}:{s:02d}'
            if s > 0: return f'{s:02d}'
            return '--'
        except (TypeError, ValueError):
            return '--'

    def create_table_item(self, field, value, client):
        if field == 'ip':
            return SortableIPItem(str(value), str(value))
        elif field == 'uptime':
            seconds = client.get('uptime', 0)
            return SortableTableItem(self.format_time(seconds), seconds)
        elif field in ('trafficDown', 'trafficUp', 'activity'):
            bytes_value = client.get(field, 0)
            return SortableTableItem(
                self.format_size(bytes_value, 'B/s' if field == 'activity' else 'B'),
                bytes_value
            )
        else:
            return QTableWidgetItem(str(value))

    def refresh_data(self):
        """Refresh data using a worker thread"""
        if self.refresh_worker and self.refresh_worker.isRunning():
            return  # Already refreshing

        # Update UI to show loading state
        self._update_status("loading", "Refreshing...")
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")
        self.stack.setCurrentIndex(2)  # Show loading state

        # Create and start worker
        self.refresh_worker = DataRefreshWorker(self.omada)
        self.refresh_worker.finished.connect(self._on_refresh_complete)
        self.refresh_worker.error.connect(self._on_refresh_error)
        self.refresh_worker.start()

    def _on_refresh_complete(self, clients):
        """Handle successful data refresh"""
        self._all_clients = clients
        self._display_clients(clients)

        status_text = "Demo Mode - Sample Data" if self.demo_mode else "Connected to Omada Controller"
        self._update_status("connected", status_text)
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")
        self.statusBar.showMessage(f"Last updated: {QDateTime.currentDateTime().toString('hh:mm:ss AP')}")

    def _on_refresh_error(self, error_msg):
        """Handle refresh error"""
        self._update_status("disconnected", "Connection error")
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")

        # Show more specific error messages
        if "Connection refused" in error_msg:
            display_msg = "Cannot reach controller - connection refused"
        elif "timeout" in error_msg.lower():
            display_msg = "Connection timed out"
        elif "logged in" in error_msg.lower():
            display_msg = "Session expired - please reconnect"
        else:
            display_msg = f"Error: {error_msg}"

        self.statusBar.showMessage(display_msg)

        # Show empty state with error
        self.empty_label.setText("Unable to load clients")
        self.stack.setCurrentIndex(1)

    def closeEvent(self, event):
        self.timer.stop()
        if self.refresh_worker:
            self.refresh_worker.quit()
            self.refresh_worker.wait()
        if self.omada:
            try:
                self.omada.logout()
            except Exception:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_STYLESHEET)

    window = OmadaClientMonitor(demo_mode=DEMO_MODE)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
