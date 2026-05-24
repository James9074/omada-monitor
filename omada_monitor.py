#!/usr/bin/env python3

import sys
import os
import json
import ipaddress
import collections
from functools import partial

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                           QLabel, QStatusBar, QHeaderView, QDialog, QLineEdit,
                           QFormLayout, QMessageBox, QCheckBox, QComboBox, QMenu,
                           QDialogButtonBox, QStackedWidget, QAbstractItemView)
from PyQt6.QtCore import (Qt, QTimer, QDateTime, QThread, QObject, pyqtSignal,
                          QSettings)
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from omada import Omada
from cryptography.fernet import Fernet


def apply_session_timeout(omada, timeout=10):
    """Ensure every request the Omada session makes has a network timeout.

    omada.py never passes ``timeout=`` to requests, so a controller that is
    reachable but unresponsive would otherwise hang the call (and, before the
    worker thread, the whole UI) until the OS-level TCP timeout.
    """
    omada.session.request = partial(omada.session.request, timeout=timeout)


class CredentialManager:
    def __init__(self):
        self.config_dir = os.path.expanduser('~/.omada-monitor')
        self.config_file = os.path.join(self.config_dir, 'credentials.enc')
        self.key_file = os.path.join(self.config_dir, 'key')

        # Ensure config directory exists and is private even if it predates us.
        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.config_dir, 0o700)
        except OSError:
            pass

        # Initialize or load encryption key
        if not os.path.exists(self.key_file):
            self._generate_key()
        else:
            with open(self.key_file, 'rb') as f:
                self.key = f.read()

        self.fernet = Fernet(self.key)

    @staticmethod
    def _write_secure(path, data):
        """Atomically create/overwrite ``path`` with 0600 permissions.

        Opening with the mode set up front avoids the brief window where the
        secret would be world-readable between ``open`` and a later ``chmod``.
        """
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)

    def _generate_key(self):
        """Generate and save a new encryption key"""
        self.key = Fernet.generate_key()
        self._write_secure(self.key_file, self.key)

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
        self._write_secure(self.config_file, encrypted_data)

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
        except Exception:
            # Avoid leaking request/credential details to the system log.
            print("Could not load saved credentials.")
        return None, None, None, None, False


class SortableIPItem(QTableWidgetItem):
    def __init__(self, display_text, ip_addr):
        super().__init__(display_text)
        self.ip_addr = ip_addr
        self.sort_key = self._ip_sort_key(ip_addr)

    @staticmethod
    def _ip_sort_key(ip):
        """Build a sort key that orders IPv4/IPv6 correctly.

        Returns ``(version, integer_value)`` so addresses sort numerically and
        IPv4 sorts before IPv6. Missing/invalid addresses sort first.
        """
        try:
            if ip in ('--', '', None):
                return (-1, -1)
            addr = ipaddress.ip_address(ip.strip())
            return (addr.version, int(addr))
        except (ValueError, AttributeError):
            return (-1, -1)

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


class LoginDialog(QDialog):
    def __init__(self, parent=None, saved_username="", saved_password="",
                 saved_baseurl="", saved_site="", saved_verify=False):
        super().__init__(parent)
        self.setWindowTitle("Omada Controller Login")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QFormLayout()

        # Create widgets
        self.username = QLineEdit(saved_username or "")
        self.password = QLineEdit(saved_password or "")
        self.baseurl = QLineEdit(saved_baseurl or "")
        self.baseurl.setPlaceholderText("http://192.168.0.1 or https://controller.example.com")
        self.site = QLineEdit(saved_site or "Default")
        self.verify = QCheckBox("Verify TLS certificate")
        self.verify.setChecked(saved_verify)

        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        # Add widgets to layout
        layout.addRow("Username:", self.username)
        layout.addRow("Password:", self.password)
        layout.addRow("Base URL:", self.baseurl)
        layout.addRow("Site:", self.site)
        layout.addRow("", self.verify)

        # Standard Save / Cancel buttons give native ordering, Esc to cancel,
        # and Return to accept.
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save and Login")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        self.setLayout(layout)

        self.credential_manager = CredentialManager()

    def accept(self):
        if not self.baseurl.text().strip():
            QMessageBox.warning(self, "Missing Base URL",
                                "Please enter the controller Base URL "
                                "(e.g. http://192.168.0.1).")
            return
        self.save()
        super().accept()

    def save(self):
        """Save credentials and config securely"""
        self.credential_manager.save_credentials(
            self.username.text(),
            self.password.text(),
            self.baseurl.text().strip(),
            self.site.text().strip() or "Default",
            self.verify.isChecked()
        )

    def get_credentials(self):
        return (
            self.username.text(),
            self.password.text(),
            self.baseurl.text().strip(),
            self.site.text().strip() or "Default",
            self.verify.isChecked()
        )


class ClientFetchWorker(QObject):
    """Fetches the client list off the GUI thread.

    On failure it makes a single re-login attempt (handles controller session
    tokens expiring during long runtimes) before reporting the error.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, omada, credential_manager):
        super().__init__()
        self.omada = omada
        self.credential_manager = credential_manager

    def run(self):
        try:
            self.finished.emit(list(self.omada.getSiteClients()))
            return
        except Exception as first_error:
            # The session token may have expired -- try one silent re-login.
            try:
                username, password, _, _, _ = self.credential_manager.load_credentials()
                if username and password:
                    self.omada.loginResult = None
                    self.omada.login(username=username, password=password)
                    self.finished.emit(list(self.omada.getSiteClients()))
                    return
            except Exception:
                pass
            self.error.emit(str(first_error))


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

    # Columns whose values are numeric and read better right-aligned.
    NUMERIC_FIELDS = {'activity', 'trafficDown', 'trafficUp', 'uptime'}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omada Client Monitor")
        self.setGeometry(100, 100, 1200, 600)
        self.setMinimumWidth(800)

        self.settings = QSettings()
        self._refresh_seconds = self._read_refresh_seconds()
        self._initial_sort = self._read_saved_sort()
        self._connected_color = QColor(46, 160, 67)  # legible green on light/dark

        # Refresh-thread state.
        self._thread = None
        self._worker = None
        self._refreshing = False
        self._first_load = True

        # Initialize credential manager
        self.credential_manager = CredentialManager()

        # Attempt auto-login with saved credentials
        if not self.try_auto_login():
            # Show login dialog if auto-login fails or no saved credentials
            if not self.show_login():
                sys.exit(1)

        self.setup_ui()

        # Restore the previous window size/position if we have one.
        geometry = self.settings.value('geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _read_refresh_seconds(self):
        try:
            secs = int(self.settings.value('refreshSeconds', 30))
        except (TypeError, ValueError):
            secs = 30
        return secs if secs in (10, 30, 60, 300) else 30

    def _read_saved_sort(self):
        col = self.settings.value('sortColumn')
        order = self.settings.value('sortOrder')
        if col is None or order is None:
            return None
        try:
            return (int(col), Qt.SortOrder(int(order)))
        except (TypeError, ValueError):
            return None

    def try_auto_login(self):
        """Attempt to login with saved credentials"""
        saved_username, saved_password, saved_baseurl, saved_site, saved_verify = \
            self.credential_manager.load_credentials()
        if all(x not in (None, '') for x in
               (saved_username, saved_password, saved_baseurl, saved_site)):
            try:
                self.omada = Omada(
                    baseurl=saved_baseurl,
                    site=saved_site,
                    verify=saved_verify
                )
                apply_session_timeout(self.omada)
                self.omada.login(username=saved_username, password=saved_password)
                return True
            except Exception:
                print("Auto-login failed; prompting for credentials.")
        return False

    def show_login(self):
        """Prompt for credentials, retrying until the user logs in or cancels.

        Returns True if a connection was established, False if cancelled.
        """
        while True:
            saved = self.credential_manager.load_credentials()
            dialog = LoginDialog(self, *saved)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

            username, password, baseurl, site, verify = dialog.get_credentials()
            try:
                new_omada = Omada(baseurl=baseurl, site=site, verify=verify)
                apply_session_timeout(new_omada)
                new_omada.login(username=username, password=password)
            except Exception as e:
                QMessageBox.critical(self, "Login Error", f"Failed to connect: {str(e)}")
                continue

            # Tear down any previous session before swapping it out.
            old_omada = getattr(self, 'omada', None)
            if old_omada is not None:
                try:
                    old_omada.logout()
                except Exception:
                    pass
            self.omada = new_omada
            return True

    def on_edit_login(self):
        if self.show_login():
            self.refresh_data()

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        # Reduce layout margins to maximize space
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Create header section
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Connecting to Omada Controller…")
        self.status_label.setStyleSheet("font-weight: 600;")

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter clients…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setMaximumWidth(220)
        self.filter_edit.textChanged.connect(self.apply_filter)

        interval_label = QLabel("Refresh:")
        self.interval_combo = QComboBox()
        for label, secs in [("10s", 10), ("30s", 30), ("60s", 60), ("5m", 300)]:
            self.interval_combo.addItem(label, secs)
        idx = self.interval_combo.findData(self._refresh_seconds)
        if idx >= 0:
            self.interval_combo.setCurrentIndex(idx)
        self.interval_combo.currentIndexChanged.connect(self.on_interval_changed)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        login_button = QPushButton("Edit Login Config")
        login_button.clicked.connect(self.on_edit_login)

        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.filter_edit)
        header_layout.addWidget(interval_label)
        header_layout.addWidget(self.interval_combo)
        header_layout.addWidget(login_button)
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.FIELDDEF))
        self.table.setHorizontalHeaderLabels([field[0] for field in self.FIELDDEF.values()])

        # Set table properties
        header = self.table.horizontalHeader()

        # Set proportional column widths based on FIELDDEF weights. Interactive
        # mode (with a stretching last column) honors these proportions while
        # still letting the user resize -- Stretch mode would ignore them.
        total_width = sum(width for _, (_, width) in self.FIELDDEF.items())
        base_width = 1180
        for col, (field, (_, width)) in enumerate(self.FIELDDEF.items()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, int(width * base_width / total_width))
        header.setStretchLastSection(True)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Right-click to copy, plus Cmd/Ctrl+C on the selection.
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.table)
        copy_shortcut.activated.connect(self.copy_selection)

        # Swap the table out for a placeholder when there are no clients.
        self.stack = QStackedWidget()
        self.empty_label = QLabel("No active clients connected")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-size: 15px;")
        self.stack.addWidget(self.table)        # index 0
        self.stack.addWidget(self.empty_label)  # index 1
        layout.addWidget(self.stack)

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Set up auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(self._refresh_seconds * 1000)

        # Initial data load (runs asynchronously).
        self.refresh_data()

    def on_interval_changed(self):
        secs = self.interval_combo.currentData()
        if secs:
            self._refresh_seconds = secs
            self.timer.setInterval(secs * 1000)

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
        # Wired client on a switch: show the port even if the switch name is
        # missing or reported under a different key by the controller.
        if client.get('port') is not None:
            switch = client.get('switchName') or client.get('switchMac') or 'Switch'
            return f"{switch} Port {client['port']}"
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
            if s > 0: return f'{s}s'
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
            return SortableTableItem(
                self.format_size(bytes_value, 'B/s' if field == 'activity' else 'B'),
                bytes_value)
        else:
            # Regular string item
            return QTableWidgetItem(str(value))

    def refresh_data(self):
        """Kick off an asynchronous fetch of the client list."""
        if self._refreshing or getattr(self, 'omada', None) is None:
            return

        self._refreshing = True
        self.refresh_button.setEnabled(False)
        self.statusBar.showMessage("Refreshing…")

        self._thread = QThread()
        self._worker = ClientFetchWorker(self.omada, self.credential_manager)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self.on_clients_loaded)
        self._worker.error.connect(self.on_fetch_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _cleanup_thread(self):
        self._refreshing = False
        self.refresh_button.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def _name_column(self):
        return list(self.FIELDDEF.keys()).index('name')

    def _ip_column(self):
        return list(self.FIELDDEF.keys()).index('ip')

    def _selected_mac(self):
        items = self.table.selectedItems()
        if not items:
            return None
        name_item = self.table.item(items[0].row(), self._name_column())
        return name_item.data(Qt.ItemDataRole.UserRole) if name_item else None

    def _select_by_mac(self, mac):
        name_col = self._name_column()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, name_col)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == mac:
                self.table.selectRow(row)
                return

    def on_clients_loaded(self, clients):
        table = self.table
        header = table.horizontalHeader()

        # Preserve the user's sort, selection, and scroll position across the
        # rebuild so a live refresh doesn't yank the view out from under them.
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        selected_mac = self._selected_mac()
        scroll_value = table.verticalScrollBar().value()

        table.setSortingEnabled(False)
        table.setRowCount(0)
        table.setRowCount(len(clients))

        name_col = self._name_column()
        for row, client in enumerate(clients):
            formatted_client = self.format_client_data(client)

            for col, (field, _) in enumerate(self.FIELDDEF.items()):
                item = self.create_table_item(field, formatted_client[field], client)
                if field in self.NUMERIC_FIELDS:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setToolTip(item.text())
                if field == 'active' and client.get('active'):
                    item.setForeground(self._connected_color)
                table.setItem(row, col, item)

            # Stash the MAC on the row so we can re-select / copy it later.
            name_item = table.item(row, name_col)
            if name_item is not None:
                name_item.setData(Qt.ItemDataRole.UserRole, client.get('mac', ''))

        table.setSortingEnabled(True)
        if self._first_load:
            col, order = self._initial_sort or (
                list(self.FIELDDEF.keys()).index('uptime'), Qt.SortOrder.AscendingOrder)
            table.sortItems(col, order)
            self._first_load = False
        else:
            table.sortItems(sort_col, sort_order)

        if selected_mac:
            self._select_by_mac(selected_mac)
        table.verticalScrollBar().setValue(scroll_value)

        self.apply_filter()

        count = len(clients)
        self.status_label.setText(f"{count} client{'' if count == 1 else 's'} connected")
        self.status_label.setStyleSheet("font-weight: 600;")
        self.stack.setCurrentIndex(0 if count else 1)
        self.statusBar.showMessage(
            f"Last updated: {QDateTime.currentDateTime().toString('h:mm:ss AP')}")

    def on_fetch_error(self, message):
        # Keep the last-known data on screen; just flag that it's stale.
        self.statusBar.showMessage(f"Error refreshing data: {message}")
        self.status_label.setText("Connection problem — showing last known data")
        self.status_label.setStyleSheet("color: #c0392b; font-weight: 600;")

    def apply_filter(self):
        text = self.filter_edit.text().strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False)
                continue
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        ip_item = self.table.item(row, self._ip_column())
        name_item = self.table.item(row, self._name_column())
        ip = ip_item.text() if ip_item else ''
        mac = name_item.data(Qt.ItemDataRole.UserRole) if name_item else ''

        menu = QMenu(self)
        copy_ip = menu.addAction(f"Copy IP ({ip})" if ip and ip != '--' else "Copy IP")
        copy_mac = menu.addAction(f"Copy MAC ({mac})" if mac else "Copy MAC")
        copy_mac.setEnabled(bool(mac))
        copy_row = menu.addAction("Copy Row")

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        clipboard = QApplication.clipboard()
        if chosen == copy_ip:
            clipboard.setText(ip)
        elif chosen == copy_mac:
            clipboard.setText(mac)
        elif chosen == copy_row:
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                cells.append(item.text() if item else '')
            clipboard.setText('\t'.join(cells))

    def copy_selection(self):
        ranges = self.table.selectedRanges()
        if not ranges:
            return
        lines = []
        for rng in ranges:
            for r in range(rng.topRow(), rng.bottomRow() + 1):
                if self.table.isRowHidden(r):
                    continue
                cells = []
                for c in range(rng.leftColumn(), rng.rightColumn() + 1):
                    item = self.table.item(r, c)
                    cells.append(item.text() if item else '')
                lines.append('\t'.join(cells))
        QApplication.clipboard().setText('\n'.join(lines))

    def _save_settings(self):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('refreshSeconds', self._refresh_seconds)
        header = self.table.horizontalHeader()
        self.settings.setValue('sortColumn', header.sortIndicatorSection())
        self.settings.setValue('sortOrder', int(header.sortIndicatorOrder().value))

    def closeEvent(self, event):
        self._save_settings()

        timer = getattr(self, 'timer', None)
        if timer is not None:
            timer.stop()

        thread = getattr(self, '_thread', None)
        if thread is not None:
            thread.quit()
            thread.wait(2000)

        omada = getattr(self, 'omada', None)
        if omada is not None:
            try:
                omada.logout()
            except Exception as e:
                print(f"Logout failed: {e}")

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    app.setOrganizationName('wlan1')
    app.setApplicationName('OmadaMonitor')
    window = OmadaClientMonitor()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
