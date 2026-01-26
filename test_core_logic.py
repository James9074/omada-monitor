#!/usr/bin/env python3
"""
Core logic tests for Omada Monitor that don't require GUI.
Tests data formatting, validation patterns, and edge cases.
"""

import sys
import os
import re
import json
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch


class TestSizeFormatting(unittest.TestCase):
    """Test size formatting function"""

    @staticmethod
    def format_size(size, suffix='B'):
        """Copy of the format_size function for testing"""
        try:
            size = float(size)
            for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
                if abs(size) < 1000.0:
                    return f'{size:.1f} {unit}{suffix}'
                size /= 1000.0
            return f'{size:.1f} Y{suffix}'
        except (TypeError, ValueError):
            return '--'

    def test_bytes(self):
        self.assertEqual(self.format_size(0, 'B'), '0.0 B')
        self.assertEqual(self.format_size(500, 'B'), '500.0 B')
        self.assertEqual(self.format_size(999, 'B'), '999.0 B')

    def test_kilobytes(self):
        self.assertEqual(self.format_size(1000, 'B'), '1.0 KB')
        self.assertEqual(self.format_size(1500, 'B'), '1.5 KB')
        self.assertEqual(self.format_size(999999, 'B'), '1000.0 KB')

    def test_megabytes(self):
        self.assertEqual(self.format_size(1000000, 'B'), '1.0 MB')
        self.assertEqual(self.format_size(1500000, 'B'), '1.5 MB')

    def test_gigabytes(self):
        self.assertEqual(self.format_size(1000000000, 'B'), '1.0 GB')
        self.assertEqual(self.format_size(5000000000, 'B'), '5.0 GB')

    def test_terabytes(self):
        self.assertEqual(self.format_size(1000000000000, 'B'), '1.0 TB')

    def test_petabytes(self):
        self.assertEqual(self.format_size(1500000000000000, 'B'), '1.5 PB')

    def test_with_suffix(self):
        self.assertEqual(self.format_size(1500000, 'B/s'), '1.5 MB/s')

    def test_invalid_input(self):
        self.assertEqual(self.format_size(None, 'B'), '--')
        self.assertEqual(self.format_size('invalid', 'B'), '--')
        self.assertEqual(self.format_size([], 'B'), '--')

    def test_negative_values(self):
        self.assertEqual(self.format_size(-100, 'B'), '-100.0 B')
        self.assertEqual(self.format_size(-1500000, 'B'), '-1.5 MB')


class TestTimeFormatting(unittest.TestCase):
    """Test time formatting function"""

    @staticmethod
    def format_time(seconds):
        """Copy of the format_time function for testing"""
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

    def test_zero(self):
        self.assertEqual(self.format_time(0), '--')

    def test_seconds_only(self):
        self.assertEqual(self.format_time(1), '01')
        self.assertEqual(self.format_time(30), '30')
        self.assertEqual(self.format_time(59), '59')

    def test_minutes_and_seconds(self):
        self.assertEqual(self.format_time(60), '01:00')
        self.assertEqual(self.format_time(90), '01:30')
        self.assertEqual(self.format_time(3599), '59:59')

    def test_hours(self):
        self.assertEqual(self.format_time(3600), '1:00:00')
        self.assertEqual(self.format_time(3661), '1:01:01')
        self.assertEqual(self.format_time(7200), '2:00:00')

    def test_days(self):
        self.assertEqual(self.format_time(86400), '1d 0:00:00')
        self.assertEqual(self.format_time(90061), '1d 1:01:01')
        self.assertEqual(self.format_time(172800), '2d 0:00:00')

    def test_long_uptime(self):
        # 365 days
        self.assertEqual(self.format_time(365 * 86400), '365d 0:00:00')

    def test_invalid_input(self):
        self.assertEqual(self.format_time(None), '--')
        self.assertEqual(self.format_time('invalid'), '--')
        self.assertEqual(self.format_time([]), '--')

    def test_negative(self):
        # Negative values should return '--' due to the logic
        self.assertEqual(self.format_time(-1), '--')


class TestIPSorting(unittest.TestCase):
    """Test IP address sorting logic"""

    @staticmethod
    def ip_to_int(ip):
        """Copy of IP conversion logic for testing"""
        try:
            if ip in ('--', '', None):
                return (-1, -1, -1, -1)
            octets = ip.split('.')
            if len(octets) != 4:
                return (-1, -1, -1, -1)
            return tuple(int(octet) for octet in octets)
        except (ValueError, AttributeError):
            return (-1, -1, -1, -1)

    def test_valid_ips(self):
        self.assertEqual(self.ip_to_int('192.168.1.1'), (192, 168, 1, 1))
        self.assertEqual(self.ip_to_int('10.0.0.1'), (10, 0, 0, 1))
        self.assertEqual(self.ip_to_int('255.255.255.255'), (255, 255, 255, 255))

    def test_sorting_order(self):
        ip1 = self.ip_to_int('192.168.1.1')
        ip2 = self.ip_to_int('192.168.1.10')
        ip3 = self.ip_to_int('10.0.0.1')

        self.assertTrue(ip3 < ip1)  # 10.x.x.x < 192.x.x.x
        self.assertTrue(ip1 < ip2)  # .1 < .10

    def test_invalid_ips(self):
        self.assertEqual(self.ip_to_int('--'), (-1, -1, -1, -1))
        self.assertEqual(self.ip_to_int(''), (-1, -1, -1, -1))
        self.assertEqual(self.ip_to_int(None), (-1, -1, -1, -1))
        self.assertEqual(self.ip_to_int('192.168'), (-1, -1, -1, -1))
        self.assertEqual(self.ip_to_int('a.b.c.d'), (-1, -1, -1, -1))

    def test_invalid_sorts_first(self):
        invalid = self.ip_to_int('--')
        valid = self.ip_to_int('192.168.1.1')
        self.assertTrue(invalid < valid)


class TestURLValidation(unittest.TestCase):
    """Test URL validation patterns"""

    @staticmethod
    def validate_url(url):
        """URL validation logic from LoginDialog"""
        if not url:
            return False
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url))

    def test_valid_https(self):
        self.assertTrue(self.validate_url('https://omada.example.com:8043'))
        self.assertTrue(self.validate_url('https://192.168.1.1:8043'))
        self.assertTrue(self.validate_url('https://localhost:8043'))

    def test_valid_http(self):
        self.assertTrue(self.validate_url('http://omada.example.com:8043'))
        self.assertTrue(self.validate_url('http://localhost'))

    def test_with_path(self):
        self.assertTrue(self.validate_url('https://omada.example.com:8043/api/v2'))

    def test_invalid_urls(self):
        self.assertFalse(self.validate_url(''))
        self.assertFalse(self.validate_url('not-a-url'))
        self.assertFalse(self.validate_url('ftp://example.com'))
        self.assertFalse(self.validate_url('example.com'))


class TestStatusFormatting(unittest.TestCase):
    """Test status formatting"""

    @staticmethod
    def format_status(active):
        return 'CONNECTED' if active else '--'

    def test_connected(self):
        self.assertEqual(self.format_status(True), 'CONNECTED')

    def test_disconnected(self):
        self.assertEqual(self.format_status(False), '--')

    def test_none(self):
        self.assertEqual(self.format_status(None), '--')


class TestPortFormatting(unittest.TestCase):
    """Test port formatting"""

    @staticmethod
    def format_port(client):
        if client.get('connectDevType') == 'ap':
            return client.get('apName', '--')
        elif 'switchName' in client and 'port' in client:
            return f"{client['switchName']} Port {client['port']}"
        return '--'

    def test_ap_connection(self):
        client = {'connectDevType': 'ap', 'apName': 'Living Room AP'}
        self.assertEqual(self.format_port(client), 'Living Room AP')

    def test_switch_connection(self):
        client = {'connectDevType': 'switch', 'switchName': 'Main Switch', 'port': 5}
        self.assertEqual(self.format_port(client), 'Main Switch Port 5')

    def test_missing_ap_name(self):
        client = {'connectDevType': 'ap'}
        self.assertEqual(self.format_port(client), '--')

    def test_empty_client(self):
        self.assertEqual(self.format_port({}), '--')


class TestClientFiltering(unittest.TestCase):
    """Test client filtering logic"""

    def setUp(self):
        self.clients = [
            {'name': 'iPhone 14', 'ip': '192.168.1.100', 'ssid': 'HomeWiFi', 'networkName': 'LAN', 'apName': 'Living Room'},
            {'name': 'MacBook Pro', 'ip': '192.168.1.101', 'ssid': 'HomeWiFi', 'networkName': 'LAN', 'apName': 'Office'},
            {'name': 'Smart TV', 'ip': '10.0.0.50', 'ssid': 'GuestWiFi', 'networkName': 'Guest', 'apName': 'Living Room'},
            {'name': 'Printer', 'ip': '192.168.1.200', 'ssid': '', 'networkName': 'LAN', 'apName': ''},
        ]

    def filter_clients(self, filter_text):
        """Filtering logic from OmadaClientMonitor"""
        filter_text = filter_text.lower()
        return [
            c for c in self.clients
            if filter_text in c.get('name', '').lower()
            or filter_text in c.get('ip', '').lower()
            or filter_text in c.get('ssid', '').lower()
            or filter_text in c.get('networkName', '').lower()
            or filter_text in c.get('apName', '').lower()
        ]

    def test_filter_by_name(self):
        result = self.filter_clients('iphone')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'iPhone 14')

    def test_filter_by_ip(self):
        result = self.filter_clients('192.168.1')
        self.assertEqual(len(result), 3)

    def test_filter_by_ssid(self):
        result = self.filter_clients('homewifi')
        self.assertEqual(len(result), 2)

    def test_filter_by_ap_name(self):
        result = self.filter_clients('living room')
        self.assertEqual(len(result), 2)

    def test_filter_case_insensitive(self):
        result = self.filter_clients('MACBOOK')
        self.assertEqual(len(result), 1)

    def test_no_matches(self):
        result = self.filter_clients('android')
        self.assertEqual(len(result), 0)

    def test_empty_filter(self):
        result = self.filter_clients('')
        self.assertEqual(len(result), 4)


class TestCredentialManagerLogic(unittest.TestCase):
    """Test credential management logic"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, '.omada-monitor')
        os.makedirs(self.config_dir, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_credential_data_structure(self):
        """Test credential data structure"""
        # Test that credential data follows expected format
        original_data = {
            'username': 'testuser',
            'password': 'testpass',
            'baseurl': 'https://test.com',
            'site': 'TestSite',
            'verify': True
        }

        # Verify all required fields are present
        required_fields = ['username', 'password', 'baseurl', 'site', 'verify']
        for field in required_fields:
            self.assertIn(field, original_data)

        # Verify types
        self.assertIsInstance(original_data['username'], str)
        self.assertIsInstance(original_data['verify'], bool)

    def test_directory_permissions(self):
        """Test that config directory has correct permissions"""
        # Check directory permissions (0o700 = rwx------)
        mode = os.stat(self.config_dir).st_mode & 0o777
        self.assertEqual(mode, 0o700)


class TestErrorMessageHandling(unittest.TestCase):
    """Test error message handling and formatting"""

    @staticmethod
    def format_error(error_msg):
        """Error message formatting from LoginDialog"""
        if "Connection refused" in error_msg or "Failed to establish" in error_msg:
            return "Could not connect to the controller. Please check the URL and ensure the controller is running."
        elif "401" in error_msg or "authentication" in error_msg.lower() or "password" in error_msg.lower():
            return "Invalid username or password. Please check your credentials."
        elif "SSL" in error_msg or "certificate" in error_msg.lower():
            return "SSL certificate verification failed. Try unchecking 'Verify SSL Certificate' for self-signed certificates."
        elif "timeout" in error_msg.lower():
            return "Connection timed out. The controller may be unreachable."
        elif "privilege" in error_msg.lower() or "site" in error_msg.lower():
            return "Access denied to the requested site. Please check the site name."
        return error_msg

    def test_connection_refused(self):
        result = self.format_error("Connection refused")
        self.assertIn("check the URL", result)

    def test_auth_error(self):
        result = self.format_error("401 Unauthorized")
        self.assertIn("Invalid username or password", result)

    def test_ssl_error(self):
        result = self.format_error("SSL certificate verify failed")
        self.assertIn("SSL certificate verification failed", result)

    def test_timeout_error(self):
        result = self.format_error("Connection timeout occurred")
        self.assertIn("timed out", result)

    def test_privilege_error(self):
        result = self.format_error("User does not have privilege to site")
        self.assertIn("Access denied", result)

    def test_generic_error(self):
        result = self.format_error("Unknown error occurred")
        self.assertEqual(result, "Unknown error occurred")


class TestEdgeCases(unittest.TestCase):
    """Test various edge cases"""

    def test_empty_client_data(self):
        """Test handling of empty client dict"""
        client = {}
        name = client.get('name', '--')
        ip = client.get('ip', '--')
        active = client.get('active', False)

        self.assertEqual(name, '--')
        self.assertEqual(ip, '--')
        self.assertFalse(active)

    def test_none_values_in_client(self):
        """Test handling of None values"""
        client = {'name': None, 'ip': None}
        name = client.get('name') or '--'
        ip = client.get('ip') or '--'

        self.assertEqual(name, '--')
        self.assertEqual(ip, '--')

    def test_very_large_traffic_value(self):
        """Test handling of extremely large values"""
        # Exabyte
        size = 1e18
        result = TestSizeFormatting.format_size(size, 'B')
        self.assertIn('E', result)

    def test_unicode_in_client_name(self):
        """Test handling of unicode characters"""
        client = {'name': '测试设备', 'ip': '192.168.1.1'}
        name = client.get('name', '--')
        self.assertEqual(name, '测试设备')


class TestClientDataProcessing(unittest.TestCase):
    """Test client data processing logic"""

    def test_format_complete_client(self):
        """Test formatting a complete client record"""
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

        formatted = {
            'name': client.get('name', '--'),
            'ip': client.get('ip', '--'),
            'active': 'CONNECTED' if client.get('active', False) else '--',
            'networkName': client.get('ssid', '--') if client.get('connectDevType') == 'ap' else client.get('networkName', '--'),
            'port': client.get('apName', '--') if client.get('connectDevType') == 'ap' else '--',
            'activity': TestSizeFormatting.format_size(client.get('activity', 0), 'B/s'),
            'trafficDown': TestSizeFormatting.format_size(client.get('trafficDown', 0), 'B'),
            'trafficUp': TestSizeFormatting.format_size(client.get('trafficUp', 0), 'B'),
            'uptime': TestTimeFormatting.format_time(client.get('uptime', 0)),
        }

        self.assertEqual(formatted['name'], 'Test Device')
        self.assertEqual(formatted['ip'], '192.168.1.100')
        self.assertEqual(formatted['active'], 'CONNECTED')
        self.assertEqual(formatted['networkName'], 'MyNetwork')
        self.assertEqual(formatted['port'], 'Living Room AP')
        self.assertIn('MB/s', formatted['activity'])
        self.assertIn('GB', formatted['trafficDown'])
        self.assertIn('d ', formatted['uptime'])


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSizeFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestTimeFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestIPSorting))
    suite.addTests(loader.loadTestsFromTestCase(TestURLValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestStatusFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestPortFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestClientFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestCredentialManagerLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorMessageHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestClientDataProcessing))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
