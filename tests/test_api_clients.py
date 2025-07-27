#!/usr/bin/env python3
"""
Comprehensive API unit tests for Glucose-GPT
Tests all API client functionality with proper mocking
"""

import unittest
from unittest import mock
import pytest
import json
import requests
from typing import Dict, Any

# Import the API clients
from glucosegpt.clients.libre_view import LibreCGMClient, ApiConfig
from glucosegpt.clients.libre_linkup import LibreLinkUpClient, LibreLinkUpConfig
from glucosegpt.utils.data_masking import DefaultDataMasker
from glucosegpt.utils.logger import setup_logger

class TestApiConfig(unittest.TestCase):
    """Test ApiConfig functionality"""
    
    def test_api_config_creation(self):
        """Test API configuration creation with defaults"""
        config = ApiConfig()
        self.assertEqual(config.version, "4.7")
        self.assertEqual(config.product, "llu.ios")  # Corrected expected value
        self.assertEqual(config.region, "us")
        self.assertIsNotNone(config.base_url)
    
    def test_api_config_custom_values(self):
        """Test API configuration with custom values"""
        config = ApiConfig(
            version="4.8",
            product="android",
            region="eu",
            base_url="https://custom.example.com"
        )
        self.assertEqual(config.version, "4.8")
        self.assertEqual(config.product, "android")
        self.assertEqual(config.region, "eu")
        self.assertEqual(config.base_url, "https://custom.example.com")


class TestLibreCGMClient(unittest.TestCase):
    """Test LibreCGM Client API functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.email = "test@example.com"
        self.password = "testpassword"
        self.config = ApiConfig()
        self.client = LibreCGMClient(
            email=self.email,
            password=self.password,
            config=self.config
        )
    
    def test_client_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.email, self.email)
        self.assertEqual(self.client.password, self.password)
        self.assertEqual(self.client.config, self.config)
        self.assertIsInstance(self.client.data_masker, DefaultDataMasker)
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_authentication_success(self, mock_make_request):
        """Test successful authentication"""
        # Mock successful response from _make_request
        mock_make_request.return_value = {
            "status": 0,
            "data": {
                "user": {
                    "id": "test_user_id",
                    "email": "test@example.com"
                },
                "authTicket": {
                    "token": "test_token",
                    "expires": 3600,
                    "duration": 3600
                }
            }
        }
        
        result = self.client.authenticate()
        
        # Verify the method was called correctly
        mock_make_request.assert_called_once_with('POST', '/llu/auth/login', data={
            "email": self.email,
            "password": self.password
        })
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], 0)
        self.assertIn("data", result)
        # Verify that auth_ticket was set
        self.assertIsNotNone(self.client.auth_ticket)
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_authentication_failure(self, mock_make_request):
        """Test authentication failure"""
        # Mock failed response that raises an exception
        mock_make_request.side_effect = Exception("Authentication failed")
        
        with self.assertRaises(Exception):
            self.client.authenticate()
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_get_current_user(self, mock_make_request):
        """Test getting current user profile"""
        # Set up authenticated client
        self.client.auth_ticket = {"token": "test_token"}
        self.client.token = "test_token"
        
        # Mock successful response
        mock_make_request.return_value = {
            "status": 0,
            "data": {
                "user": {
                    "id": "user123",
                    "email": "test@example.com",
                    "firstName": "Test",
                    "lastName": "User"
                }
            }
        }
        
        result = self.client.get_current_user()
        
        # Verify the call
        mock_make_request.assert_called_once_with('GET', '/user', headers=mock.ANY)
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_list_connections(self, mock_make_request):
        """Test listing patient connections"""
        # Set up authenticated client
        self.client.auth_ticket = {"token": "test_token"}
        self.client.token = "test_token"
        
        # Mock successful response
        mock_make_request.return_value = {
            "status": 0,
            "data": [
                {
                    "patientId": "patient123",
                    "firstName": "John",
                    "lastName": "Doe",
                    "targetLow": 70,
                    "targetHigh": 180
                }
            ]
        }
        
        result = self.client.list_connections()
        
        # Verify the call
        mock_make_request.assert_called_once_with('GET', '/llu/connections', headers=mock.ANY)
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_get_patient_graph(self, mock_make_request):
        """Test getting patient glucose graph data"""
        # Set up authenticated client
        self.client.auth_ticket = {"token": "test_token"}
        self.client.token = "test_token"
        patient_id = "patient123"
        
        # Mock successful response
        mock_make_request.return_value = {
            "status": 0,
            "data": {
                "graphData": [
                    {
                        "FactoryTimestamp": "2025-01-01T10:00:00",
                        "Timestamp": "2025-01-01T10:00:00",
                        "type": 1,
                        "ValueInMgPerDl": 120,
                        "TrendArrow": 4
                    }
                ]
            }
        }
        
        result = self.client.get_patient_graph(patient_id)
        
        # Verify the call
        mock_make_request.assert_called_once_with('GET', f'/llu/connections/{patient_id}/graph', headers=mock.ANY)


class TestLibreLinkUpClient(unittest.TestCase):
    """Test LibreLinkUp Client API functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.username = "test@example.com"
        self.password = "testpassword"
        self.config = LibreLinkUpConfig()
        self.client = LibreLinkUpClient(
            username=self.username,
            password=self.password,
            config=self.config
        )
    
    def test_client_initialization(self):
        """Test LibreLinkUp client initialization"""
        self.assertEqual(self.client.username, self.username)
        self.assertEqual(self.client.password, self.password)
        self.assertEqual(self.client.config, self.config)
    
    @mock.patch('glucosegpt.clients.libre_linkup.LibreLinkUpClient._make_request')
    def test_linkup_authentication(self, mock_make_request):
        """Test LibreLinkUp authentication"""
        # Mock successful response
        mock_make_request.return_value = {
            "status": 0,
            "data": {
                "user": {
                    "id": "linkup_user_id",
                    "email": "test@example.com"
                },
                "authTicket": {
                    "token": "linkup_token",
                    "expires": 3600
                }
            }
        }
        
        result = self.client.authenticate()
        
        # Verify the call was made correctly
        mock_make_request.assert_called_once()
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], 0)


class TestDataMasking(unittest.TestCase):
    """Test data masking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.masker = DefaultDataMasker()
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking"""
        test_data = {
            "email": "test@example.com",
            "password": "secretpassword123",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "normal_field": "normal_value"
        }
        masked = self.masker.mask_sensitive_data(test_data)
        
        # Check that sensitive fields are masked
        self.assertNotEqual(masked["email"], test_data["email"])
        self.assertIn("...", masked["email"])
        # The actual implementation masks longer passwords with first 3 and last 4 chars
        self.assertNotEqual(masked["password"], test_data["password"])
        self.assertTrue(masked["password"].startswith("sec"))
        self.assertTrue(masked["password"].endswith("123"))
        self.assertNotEqual(masked["token"], test_data["token"])
        
        # Check that normal fields are not masked
        self.assertEqual(masked["normal_field"], test_data["normal_field"])


class TestAPIErrorHandling(unittest.TestCase):
    """Test API error handling scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = LibreCGMClient(
            email="test@example.com",
            password="test",
            config=ApiConfig()
        )
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_network_error_handling(self, mock_make_request):
        """Test network error handling"""
        # Mock network error
        mock_make_request.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.client.authenticate()
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_timeout_error_handling(self, mock_make_request):
        """Test timeout error handling"""
        # Mock timeout error
        mock_make_request.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with self.assertRaises(requests.exceptions.Timeout):
            self.client.authenticate()
    
    @mock.patch('glucosegpt.clients.libre_view.LibreCGMClient._make_request')
    def test_invalid_json_response(self, mock_make_request):
        """Test handling of invalid JSON responses"""
        # Mock response with invalid JSON
        mock_make_request.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with self.assertRaises(json.JSONDecodeError):
            self.client.authenticate()


class TestAPIRateLimiting(unittest.TestCase):
    """Test API rate limiting scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = LibreCGMClient(
            email="test@example.com",
            password="test",
            config=ApiConfig()
        )
    
    @mock.patch('requests.post')
    def test_rate_limit_handling(self, mock_post):
        """Test rate limit error handling"""
        # Mock rate limit response
        mock_response = mock.Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": "Rate limit exceeded"
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(Exception):
            self.client.authenticate()


class TestAPIRegionalSupport(unittest.TestCase):
    """Test API regional support functionality"""
    
    def test_us_region_config(self):
        """Test US region configuration"""
        config = ApiConfig(region="us")
        self.assertEqual(config.region, "us")
        # US region should use default base URL
        self.assertIsNotNone(config.base_url)
    
    def test_eu_region_config(self):
        """Test EU region configuration"""
        config = ApiConfig(region="eu")
        self.assertEqual(config.region, "eu")
        # EU region should have appropriate base URL
        self.assertIsNotNone(config.base_url)


if __name__ == "__main__":
    print("🧪 Running Glucose-GPT API Unit Tests")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2)
