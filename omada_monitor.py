#!/usr/bin/env python3

import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, 
                           QLabel, QStatusBar, QHeaderView, QDialog, QLineEdit,
                           QFormLayout, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from omada import Omada
import collections
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class CredentialManager:
    def __init__(self):
        self.config_dir = os.path.expanduser('~/.omada-monitor')
        self.config_file = os.path.join(self.config_dir, 'credentials.enc')
        self.key_file = os.path.join(self.config_dir, 'key')
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
        
        # Initialize or load encryption key
        if not os.path.exists(self.key_file):
            self._generate_key()
        else:
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        
        self.fernet = Fernet(self.key)

    def _generate_key(self):
        """Generate and save a new encryption key"""
        self.key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(self.key)
        os.chmod(self.key_file, 0o600)    
    def save_credentials(self, username, password, baseurl, site, verify):
        """Encrypt and save credentials and config"""
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
        """Load and decrypt credentials"""
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
                    data.get('verify', False)  # Default to False for backward compatibility
                )
        except Exception as e:
            print(f"Error loading credentials: {e}")
        return None, None, None, None, False
    
class SortableIPItem(QTableWidgetItem):
    def __init__(self, display_text, ip_addr):
        super().__init__(display_text)
        self.ip_addr = ip_addr
        self.sort_key = self._ip_to_int(ip_addr)

    def _ip_to_int(self, ip):
        """Convert an IP address to a tuple of integers for proper sorting"""
        try:
            # Handle empty or invalid IPs
            if ip in ('--', '', None):
                return (-1, -1, -1, -1)  # Will sort before valid IPs
            
            # Split IP into octets and convert to integers
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
    
class LoginDialog(QDialog):
    def __init__(self, parent=None, saved_username="", saved_password="", 
                 saved_baseurl="", saved_site="", saved_verify=False):
        super().__init__(parent)
        self.setWindowTitle("Omada Controller Login")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QFormLayout()
        
        # Create widgets
        self.username = QLineEdit(saved_username)
        self.password = QLineEdit(saved_password)
        self.baseurl = QLineEdit(saved_baseurl or "")
        self.site = QLineEdit(saved_site or "Default")
        self.verify = QCheckBox("Verify Certificate")
        self.verify.setChecked(saved_verify)
        
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_button = QPushButton("Save and Login")
        
        # Add widgets to layout
        layout.addRow("Username:", self.username)
        layout.addRow("Password:", self.password)
        layout.addRow("Base URL:", self.baseurl)        
        layout.addRow("Site:", self.site)
        layout.addRow("", self.verify)
        
        button_layout = QHBoxLayout()        
        button_layout.addWidget(self.login_button)
        layout.addRow("", button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.login_button.clicked.connect(self.accept)        
        
        self.credential_manager = CredentialManager()

    def accept(self):
        self.save()
        super().accept()

    def save(self):
        """Save credentials and config securely"""
        self.credential_manager.save_credentials(
            self.username.text(),
            self.password.text(),
            self.baseurl.text(),
            self.site.text(),
            self.verify.isChecked()
        )

    def get_credentials(self):
        return (
            self.username.text(),
            self.password.text(),
            self.baseurl.text(),
            self.site.text(),
            self.verify.isChecked()
        )
      
class SortableTableItem(QTableWidgetItem):
    def __init__(self, display_text, sort_key):
        super().__init__(display_text)
        self.sort_key = sort_key

    def __lt__(self, other):
        try:
            return self.sort_key < other.sort_key
        except (TypeError, AttributeError):
            return super().__lt__(other)       

class OmadaClientMonitor(QMainWindow):
    FIELDDEF = collections.OrderedDict([
        ('name',        ('USERNAME',     20)),
        ('ip',          ('IP ADDRESS',   16)),
        ('active',      ('STATUS',       12)),
        ('networkName', ('SSID/NETWORK', 16)),
        ('port',        ('AP/PORT',      16)),
        ('activity',    ('ACTIVITY',     12)),
        ('trafficDown', ('DOWNLOAD',     10)),
        ('trafficUp',   ('UPLOAD',       10)),
        ('uptime',      ('UPTIME',       16)),
    ])

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omada Client Monitor")
        self.setGeometry(100, 100, 1200, 600)
        self.setMinimumWidth(800)
        
        # Initialize credential manager
        self.credential_manager = CredentialManager()
        
        # Attempt auto-login with saved credentials
        if not self.try_auto_login():
            # Show login dialog if auto-login fails or no saved credentials
            if not self.show_login():
                sys.exit(1)
            
        self.setup_ui()

    def try_auto_login(self):
        """Attempt to login with saved credentials"""
        saved_username, saved_password, saved_baseurl, saved_site, saved_verify = self.credential_manager.load_credentials()
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

    def show_login(self):
        # Load saved credentials
        saved_username, saved_password, saved_baseurl, saved_site, saved_verify = self.credential_manager.load_credentials()
        
        dialog = LoginDialog(
            self, saved_username, saved_password,
            saved_baseurl, saved_site, saved_verify
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username, password, baseurl, site, verify = dialog.get_credentials()
            try:
                self.omada = Omada(
                    baseurl=baseurl,
                    site=site,
                    verify=verify
                )
                self.omada.login(username=username, password=password)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Login Error", f"Failed to connect: {str(e)}")
                return self.show_login()  # Recursively show login dialog until successful
        return False

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        # Reduce layout margins to maximize space
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Create header section
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Connected to Omada Controller")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        login_button = QPushButton("Edit Login Config")
        login_button.clicked.connect(self.show_login)
        
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(login_button)
        header_layout.addWidget(refresh_button)
        layout.addLayout(header_layout)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.FIELDDEF))
        self.table.setHorizontalHeaderLabels([field[0] for field in self.FIELDDEF.values()])
        
        # Set table properties
        header = self.table.horizontalHeader()
        
        # Calculate total relative width
        total_width = sum(width for _, (_, width) in self.FIELDDEF.items())
        
        # Set proportional column widths
        for col, (field, (_, width)) in enumerate(self.FIELDDEF.items()):
            # Use Stretch mode for all columns
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            # Set relative width based on FIELDDEF proportions
            header.resizeSection(col, int(width * 100 / total_width))
            
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.table)

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Set up auto-refresh timer (every 30 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)

        # Initial data load and sort
        self.refresh_data()
        
        # Set default sort to uptime column (ascending)
        uptime_column = list(self.FIELDDEF.keys()).index('uptime')
        self.table.sortItems(uptime_column, Qt.SortOrder.AscendingOrder)

    def format_client_data(self, client):
        formatted = {}
        
        # Handle basic fields
        formatted['name'] = client.get('name', '--')
        formatted['ip'] = client.get('ip', '--')
        formatted['active'] = self.format_status(client.get('active', False))
        
        # Handle network name based on device type
        if client.get('connectDevType') == 'ap':
            formatted['networkName'] = client.get('ssid', '--')
        else:
            formatted['networkName'] = client.get('networkName', '--')
        
        # Handle port/AP field
        formatted['port'] = self.format_port(client)
        
        # Handle traffic fields
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
            # Special handling for IP addresses
            return SortableIPItem(str(value), str(value))
        elif field == 'uptime':
            # Store raw seconds for sorting, but display formatted time
            seconds = client.get('uptime', 0)
            return SortableTableItem(self.format_time(seconds), seconds)
        elif field in ('trafficDown', 'trafficUp', 'activity'):
            # Store raw bytes for sorting, but display formatted size
            bytes_value = client.get(field, 0)
            return SortableTableItem(self.format_size(bytes_value, 'B/s' if field == 'activity' else 'B'), bytes_value)
        else:
            # Regular string item
            return QTableWidgetItem(str(value))

    def refresh_data(self):
        try:
            # Temporarily disable sorting to prevent issues while updating
            self.table.setSortingEnabled(False)
            
            # Clear existing rows
            self.table.setRowCount(0)
            
            # Get and add new data
            clients = list(self.omada.getSiteClients())
            self.table.setRowCount(len(clients))
            
            for row, client in enumerate(clients):
                formatted_client = self.format_client_data(client)
                
                for col, (field, _) in enumerate(self.FIELDDEF.items()):
                    item = self.create_table_item(field, formatted_client[field], client)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row, col, item)
            
            # Re-enable sorting and restore default sort
            self.table.setSortingEnabled(True)
            uptime_column = list(self.FIELDDEF.keys()).index('uptime')
            self.table.sortItems(uptime_column, Qt.SortOrder.AscendingOrder)

            self.statusBar.showMessage(f"Last updated: {QDateTime.currentDateTime().toString()}")
            
        except Exception as e:
            self.statusBar.showMessage(f"Error refreshing data: {str(e)}")
    
    def closeEvent(self, event):
        self.timer.stop()
        self.omada.logout()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    window = OmadaClientMonitor()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()