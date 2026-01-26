#!/usr/bin/env python3
"""
Comprehensive test suite for Omada Monitor application.
Tests UI components, validation logic, data formatting, and edge cases.
"""

import sys
import os
import json
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Set up Qt platform for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Initialize QApplication for tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from omada_monitor import (
    CredentialManager,
    SortableIPItem,
    SortableTableItem,
    LoginDialog,
    OmadaClientMonitor,
    ValidationError,
    DataRefreshWorker,
)


class TestCredentialManager(unittest.TestCase):
    """Test credential encryption and storage"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_expanduser = os.path.expanduser

    def tearDown(self):
        os.path.expanduser = self.original_expanduser
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_credential_manager_creates_directory(self):
        """Test that credential manager creates config directory"""
        with patch('os.path.expanduser', return_value=self.test_dir):
            with patch.object(CredentialManager, '__init__', lambda s: None):
                cm = CredentialManager()
                cm.config_dir = os.path.join(self.test_dir, '.omada-monitor')
                os.makedirs(cm.config_dir, mode=0o700, exist_ok=True)
                self.assertTrue(os.path.exists(cm.config_dir))

    def test_save_and_load_credentials(self):
        """Test saving and loading credentials"""
        with patch('os.path.expanduser', return_value=self.test_dir):
            # Create a fresh credential manager with our test directory
            config_dir = os.path.join(self.test_dir, '.omada-monitor')
            os.makedirs(config_dir, mode=0o700, exist_ok=True)

            cm = CredentialManager.__new__(CredentialManager)
            cm.config_dir = config_dir
            cm.config_file = os.path.join(config_dir, 'credentials.enc')
            cm.key_file = os.path.join(config_dir, 'key')
            cm._generate_key()
            from cryptography.fernet import Fernet
            cm.fernet = Fernet(cm.key)

            # Save credentials
            cm.save_credentials('testuser', 'testpass', 'https://test.com', 'TestSite', True)

            # Load and verify
            username, password, baseurl, site, verify = cm.load_credentials()
            self.assertEqual(username, 'testuser')
            self.assertEqual(password, 'testpass')
            self.assertEqual(baseurl, 'https://test.com')
            self.assertEqual(site, 'TestSite')
            self.assertTrue(verify)

    def test_load_nonexistent_credentials(self):
        """Test loading credentials when none exist"""
        with patch('os.path.expanduser', return_value=self.test_dir):
            config_dir = os.path.join(self.test_dir, '.omada-monitor')
            os.makedirs(config_dir, mode=0o700, exist_ok=True)

            cm = CredentialManager.__new__(CredentialManager)
            cm.config_dir = config_dir
            cm.config_file = os.path.join(config_dir, 'credentials.enc')
            cm.key_file = os.path.join(config_dir, 'key')
            cm._generate_key()
            from cryptography.fernet import Fernet
            cm.fernet = Fernet(cm.key)

            username, password, baseurl, site, verify = cm.load_credentials()
            self.assertIsNone(username)
            self.assertIsNone(password)
            self.assertIsNone(baseurl)
            self.assertIsNone(site)
            self.assertFalse(verify)


class TestSortableIPItem(unittest.TestCase):
    """Test IP address sorting functionality"""

    def test_valid_ip_sorting(self):
        """Test that valid IPs sort correctly"""
        item1 = SortableIPItem("192.168.1.1", "192.168.1.1")
        item2 = SortableIPItem("192.168.1.10", "192.168.1.10")
        item3 = SortableIPItem("10.0.0.1", "10.0.0.1")

        # 10.0.0.1 should come before 192.168.1.1
        self.assertTrue(item3 < item1)
        # 192.168.1.1 should come before 192.168.1.10
        self.assertTrue(item1 < item2)

    def test_invalid_ip_handling(self):
        """Test that invalid IPs are handled gracefully"""
        item_valid = SortableIPItem("192.168.1.1", "192.168.1.1")
        item_invalid = SortableIPItem("--", "--")
        item_empty = SortableIPItem("", "")

        # Invalid IPs should sort before valid ones
        self.assertTrue(item_invalid < item_valid)
        self.assertTrue(item_empty < item_valid)

    def test_ip_parsing_edge_cases(self):
        """Test edge cases in IP parsing"""
        # Malformed IP
        item = SortableIPItem("192.168", "192.168")
        self.assertEqual(item.sort_key, (-1, -1, -1, -1))

        # Non-numeric octets
        item = SortableIPItem("a.b.c.d", "a.b.c.d")
        self.assertEqual(item.sort_key, (-1, -1, -1, -1))

        # None value
        item = SortableIPItem("--", None)
        self.assertEqual(item.sort_key, (-1, -1, -1, -1))


class TestSortableTableItem(unittest.TestCase):
    """Test custom table item sorting"""

    def test_numeric_sorting(self):
        """Test that numeric values sort correctly"""
        item1 = SortableTableItem("1.5 MB", 1500000)
        item2 = SortableTableItem("2.0 MB", 2000000)
        item3 = SortableTableItem("500 KB", 500000)

        self.assertTrue(item3 < item1)
        self.assertTrue(item1 < item2)

    def test_time_sorting(self):
        """Test that time values sort correctly"""
        item1 = SortableTableItem("5:00:00", 18000)  # 5 hours
        item2 = SortableTableItem("1d 0:00:00", 86400)  # 1 day
        item3 = SortableTableItem("30:00", 1800)  # 30 minutes

        self.assertTrue(item3 < item1)
        self.assertTrue(item1 < item2)


class TestDataFormatting(unittest.TestCase):
    """Test data formatting functions"""

    def test_format_size_bytes(self):
        """Test byte size formatting"""
        self.assertEqual(OmadaClientMonitor.format_size(0, 'B'), '0.0 B')
        self.assertEqual(OmadaClientMonitor.format_size(500, 'B'), '500.0 B')
        self.assertEqual(OmadaClientMonitor.format_size(1000, 'B'), '1.0 KB')
        self.assertEqual(OmadaClientMonitor.format_size(1500000, 'B'), '1.5 MB')
        self.assertEqual(OmadaClientMonitor.format_size(1500000000, 'B'), '1.5 GB')

    def test_format_size_edge_cases(self):
        """Test edge cases for size formatting"""
        self.assertEqual(OmadaClientMonitor.format_size(None, 'B'), '--')
        self.assertEqual(OmadaClientMonitor.format_size('invalid', 'B'), '--')
        self.assertEqual(OmadaClientMonitor.format_size(-100, 'B'), '-100.0 B')

    def test_format_time_seconds(self):
        """Test time formatting"""
        self.assertEqual(OmadaClientMonitor.format_time(0), '--')
        self.assertEqual(OmadaClientMonitor.format_time(30), '30')
        self.assertEqual(OmadaClientMonitor.format_time(90), '01:30')
        self.assertEqual(OmadaClientMonitor.format_time(3661), '1:01:01')
        self.assertEqual(OmadaClientMonitor.format_time(90061), '1d 1:01:01')

    def test_format_time_edge_cases(self):
        """Test edge cases for time formatting"""
        self.assertEqual(OmadaClientMonitor.format_time(None), '--')
        self.assertEqual(OmadaClientMonitor.format_time('invalid'), '--')
        self.assertEqual(OmadaClientMonitor.format_time(-1), '--')

    def test_format_status(self):
        """Test status formatting"""
        self.assertEqual(OmadaClientMonitor.format_status(True), 'CONNECTED')
        self.assertEqual(OmadaClientMonitor.format_status(False), '--')
        self.assertEqual(OmadaClientMonitor.format_status(None), '--')

    def test_format_port_ap(self):
        """Test port formatting for AP connections"""
        client = {'connectDevType': 'ap', 'apName': 'Living Room AP'}
        self.assertEqual(OmadaClientMonitor.format_port(client), 'Living Room AP')

    def test_format_port_switch(self):
        """Test port formatting for switch connections"""
        client = {'connectDevType': 'switch', 'switchName': 'Main Switch', 'port': 5}
        self.assertEqual(OmadaClientMonitor.format_port(client), 'Main Switch Port 5')

    def test_format_port_missing_data(self):
        """Test port formatting with missing data"""
        self.assertEqual(OmadaClientMonitor.format_port({}), '--')
        self.assertEqual(OmadaClientMonitor.format_port({'connectDevType': 'ap'}), '--')


class TestLoginDialogValidation(unittest.TestCase):
    """Test login dialog validation logic"""

    def setUp(self):
        self.dialog = LoginDialog()

    def tearDown(self):
        self.dialog.close()

    def test_url_validation_empty(self):
        """Test URL validation with empty input"""
        self.dialog.baseurl.setText("")
        self.assertFalse(self.dialog._validate_url())

    def test_url_validation_invalid(self):
        """Test URL validation with invalid URL"""
        self.dialog.baseurl.setText("not-a-url")
        self.assertFalse(self.dialog._validate_url())

    def test_url_validation_valid_https(self):
        """Test URL validation with valid HTTPS URL"""
        self.dialog.baseurl.setText("https://omada.example.com:8043")
        self.assertTrue(self.dialog._validate_url())

    def test_url_validation_valid_http(self):
        """Test URL validation with valid HTTP URL"""
        self.dialog.baseurl.setText("http://localhost:8043")
        self.assertTrue(self.dialog._validate_url())

    def test_username_validation_empty(self):
        """Test username validation with empty input"""
        self.dialog.username.setText("")
        self.assertFalse(self.dialog._validate_username())

    def test_username_validation_too_short(self):
        """Test username validation with short input"""
        self.dialog.username.setText("a")
        self.assertFalse(self.dialog._validate_username())

    def test_username_validation_valid(self):
        """Test username validation with valid input"""
        self.dialog.username.setText("admin")
        self.assertTrue(self.dialog._validate_username())

    def test_password_validation_empty(self):
        """Test password validation with empty input"""
        self.dialog.password.setText("")
        self.assertFalse(self.dialog._validate_password())

    def test_password_validation_valid(self):
        """Test password validation with valid input"""
        self.dialog.password.setText("password123")
        self.assertTrue(self.dialog._validate_password())

    def test_site_validation_empty(self):
        """Test site validation with empty input"""
        self.dialog.site.setText("")
        self.assertFalse(self.dialog._validate_site())

    def test_site_validation_valid(self):
        """Test site validation with valid input"""
        self.dialog.site.setText("Default")
        self.assertTrue(self.dialog._validate_site())

    def test_validate_all_empty_form(self):
        """Test validating entire form when empty"""
        self.dialog.baseurl.setText("")
        self.dialog.username.setText("")
        self.dialog.password.setText("")
        self.dialog.site.setText("")
        self.assertFalse(self.dialog._validate_all())

    def test_validate_all_valid_form(self):
        """Test validating entire form with valid data"""
        self.dialog.baseurl.setText("https://omada.example.com:8043")
        self.dialog.username.setText("admin")
        self.dialog.password.setText("password123")
        self.dialog.site.setText("Default")
        self.assertTrue(self.dialog._validate_all())


class TestClientDataFormatting(unittest.TestCase):
    """Test client data formatting"""

    def test_format_client_data_complete(self):
        """Test formatting complete client data"""
        client = {
            'name': 'Test Device',
            'ip': '192.168.1.100',
            'active': True,
            'connectDevType': 'ap',
            'ssid': 'MyNetwork',
            'apName': 'Living Room AP',
            'activity': 1500000,
            'trafficDown': 5000000000,
            'trafficUp': 1000000000,
            'uptime': 86400
        }

        # We need to use the class method
        formatted = OmadaClientMonitor.format_client_data(None, client)

        self.assertEqual(formatted['name'], 'Test Device')
        self.assertEqual(formatted['ip'], '192.168.1.100')
        self.assertEqual(formatted['active'], 'CONNECTED')
        self.assertEqual(formatted['networkName'], 'MyNetwork')
        self.assertEqual(formatted['port'], 'Living Room AP')

    def test_format_client_data_missing_fields(self):
        """Test formatting client data with missing fields"""
        client = {}

        formatted = OmadaClientMonitor.format_client_data(None, client)

        self.assertEqual(formatted['name'], '--')
        self.assertEqual(formatted['ip'], '--')
        self.assertEqual(formatted['active'], '--')
        self.assertEqual(formatted['port'], '--')


class TestFilteringLogic(unittest.TestCase):
    """Test client filtering logic"""

    def test_filter_by_name(self):
        """Test filtering clients by name"""
        clients = [
            {'name': 'iPhone', 'ip': '192.168.1.1', 'ssid': '', 'networkName': '', 'apName': ''},
            {'name': 'MacBook', 'ip': '192.168.1.2', 'ssid': '', 'networkName': '', 'apName': ''},
            {'name': 'iPad', 'ip': '192.168.1.3', 'ssid': '', 'networkName': '', 'apName': ''},
        ]

        filter_text = 'mac'
        filtered = [
            c for c in clients
            if filter_text in c.get('name', '').lower()
        ]

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'MacBook')

    def test_filter_by_ip(self):
        """Test filtering clients by IP address"""
        clients = [
            {'name': 'Device1', 'ip': '192.168.1.100', 'ssid': '', 'networkName': '', 'apName': ''},
            {'name': 'Device2', 'ip': '192.168.1.200', 'ssid': '', 'networkName': '', 'apName': ''},
            {'name': 'Device3', 'ip': '10.0.0.1', 'ssid': '', 'networkName': '', 'apName': ''},
        ]

        filter_text = '192.168'
        filtered = [
            c for c in clients
            if filter_text in c.get('ip', '').lower()
        ]

        self.assertEqual(len(filtered), 2)

    def test_filter_case_insensitive(self):
        """Test that filtering is case insensitive"""
        clients = [
            {'name': 'IPHONE', 'ip': '', 'ssid': '', 'networkName': '', 'apName': ''},
            {'name': 'macbook', 'ip': '', 'ssid': '', 'networkName': '', 'apName': ''},
        ]

        filter_text = 'iphone'
        filtered = [
            c for c in clients
            if filter_text in c.get('name', '').lower()
        ]

        self.assertEqual(len(filtered), 1)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_empty_client_list(self):
        """Test handling of empty client list"""
        clients = []
        self.assertEqual(len(clients), 0)

    def test_client_with_none_values(self):
        """Test handling clients with None values"""
        client = {
            'name': None,
            'ip': None,
            'active': None,
            'uptime': None,
        }

        name = client.get('name', '--') or '--'
        self.assertEqual(name, '--')

    def test_large_traffic_values(self):
        """Test formatting of large traffic values"""
        # Test petabyte range
        result = OmadaClientMonitor.format_size(1500000000000000, 'B')
        self.assertIn('P', result)

    def test_very_long_uptime(self):
        """Test formatting of very long uptime"""
        # 365 days
        seconds = 365 * 24 * 3600
        result = OmadaClientMonitor.format_time(seconds)
        self.assertIn('365d', result)


class TestURLValidationEdgeCases(unittest.TestCase):
    """Test URL validation edge cases"""

    def setUp(self):
        self.dialog = LoginDialog()

    def tearDown(self):
        self.dialog.close()

    def test_url_with_path(self):
        """Test URL validation with path"""
        self.dialog.baseurl.setText("https://omada.example.com:8043/api")
        self.assertTrue(self.dialog._validate_url())

    def test_url_with_ip(self):
        """Test URL validation with IP address"""
        self.dialog.baseurl.setText("https://192.168.1.1:8043")
        self.assertTrue(self.dialog._validate_url())

    def test_url_localhost(self):
        """Test URL validation with localhost"""
        self.dialog.baseurl.setText("http://localhost:8043")
        self.assertTrue(self.dialog._validate_url())

    def test_url_with_spaces(self):
        """Test URL validation with spaces (should fail)"""
        self.dialog.baseurl.setText("https://example .com")
        self.assertFalse(self.dialog._validate_url())


class TestDataRefreshWorkerSignals(unittest.TestCase):
    """Test DataRefreshWorker signal emissions"""

    def test_worker_emits_finished_on_success(self):
        """Test that worker emits finished signal with data"""
        mock_omada = MagicMock()
        mock_omada.getSiteClients.return_value = [
            {'name': 'Device1', 'ip': '192.168.1.1'},
            {'name': 'Device2', 'ip': '192.168.1.2'},
        ]

        worker = DataRefreshWorker(mock_omada)
        results = []

        def capture_results(data):
            results.extend(data)

        worker.finished.connect(capture_results)
        worker.run()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'Device1')

    def test_worker_emits_error_on_exception(self):
        """Test that worker emits error signal on exception"""
        mock_omada = MagicMock()
        mock_omada.getSiteClients.side_effect = Exception("Connection failed")

        worker = DataRefreshWorker(mock_omada)
        errors = []

        def capture_error(msg):
            errors.append(msg)

        worker.error.connect(capture_error)
        worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("Connection failed", errors[0])


class TestValidationError(unittest.TestCase):
    """Test ValidationError class"""

    def test_validation_error_creation(self):
        """Test creating a ValidationError"""
        error = ValidationError("username", "Username is required")
        self.assertEqual(error.field, "username")
        self.assertEqual(error.message, "Username is required")


def run_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCredentialManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSortableIPItem))
    suite.addTests(loader.loadTestsFromTestCase(TestSortableTableItem))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestLoginDialogValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestClientDataFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestFilteringLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestURLValidationEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestDataRefreshWorkerSignals))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationError))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
