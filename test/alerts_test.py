"""
Unit tests for the alerts module.
"""

import argparse
import unittest
from unittest.mock import Mock, patch, MagicMock
import typing as T

from ryutils.alerts.alerter import Alerter
from ryutils.alerts.discord import DiscordAlerter
from ryutils.alerts.slack import SlackAlerter
from ryutils.alerts.mock import MockAlerter
from ryutils.alerts.factory import AlertFactory
from ryutils.alerts.alert_types import AlertType


class TestAlerter(unittest.TestCase):
    """Test the base Alerter class."""

    def test_alerter_initialization(self) -> None:
        """Test Alerter initialization through concrete implementation."""
        # Use MockAlerter to test base class functionality
        alerter = MockAlerter(webhook_url="test_id")
        self.assertEqual(alerter.alert_id, "test_id")
        self.assertEqual(alerter.TYPE, "Mock")

    def test_alerter_string_representation(self) -> None:
        """Test Alerter string representation."""
        alerter = MockAlerter(webhook_url="test_id")
        self.assertEqual(str(alerter), "Mock")
        self.assertEqual(repr(alerter), "Mock(test_id)")

    def test_alerter_equality(self) -> None:
        """Test Alerter equality comparison."""
        alerter1 = MockAlerter(webhook_url="test_id")
        alerter2 = MockAlerter(webhook_url="test_id")
        alerter3 = MockAlerter(webhook_url="different_id")
        
        # Set same callback for equality test
        def dummy_callback(msg: str) -> None:
            pass
        alerter1.callback = dummy_callback
        alerter2.callback = dummy_callback
        alerter3.callback = dummy_callback

        self.assertEqual(alerter1, alerter2)
        self.assertNotEqual(alerter1, alerter3)

    def test_alerter_hash(self) -> None:
        """Test Alerter hash function."""
        alerter1 = MockAlerter(webhook_url="test_id")
        alerter2 = MockAlerter(webhook_url="test_id")
        alerter3 = MockAlerter(webhook_url="different_id")
        
        # Set same callback for hash test
        def dummy_callback(msg: str) -> None:
            pass
        alerter1.callback = dummy_callback
        alerter2.callback = dummy_callback
        alerter3.callback = dummy_callback

        self.assertEqual(hash(alerter1), hash(alerter2))
        self.assertNotEqual(hash(alerter1), hash(alerter3))

    def test_alerter_ordering(self) -> None:
        """Test Alerter ordering."""
        alerter1 = MockAlerter(webhook_url="a")
        alerter2 = MockAlerter(webhook_url="b")
        
        # Set same callback for ordering test
        def dummy_callback(msg: str) -> None:
            pass
        alerter1.callback = dummy_callback
        alerter2.callback = dummy_callback

        self.assertLess(alerter1, alerter2)


class TestMockAlerter(unittest.TestCase):
    """Test MockAlerter functionality."""

    def test_mock_alerter_initialization(self) -> None:
        """Test MockAlerter initialization."""
        mock_alerter = MockAlerter(webhook_url="http://test.com")
        self.assertEqual(mock_alerter.webhook_url, "http://test.com")
        self.assertEqual(mock_alerter.TYPE, "Mock")
        self.assertEqual(mock_alerter.alert_id, "http://test.com")

    def test_mock_alerter_callback_property(self) -> None:
        """Test MockAlerter callback property."""
        mock_alerter = MockAlerter(webhook_url="http://test.com")

        # Test default callback
        self.assertIsNotNone(mock_alerter.callback)

        # Test setting callback
        received_messages = []
        def test_callback(message: str) -> None:
            received_messages.append(message)

        mock_alerter.callback = test_callback
        mock_alerter.send_alert("Test message")

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0], "Test message")

    def test_mock_alerter_send_alert(self) -> None:
        """Test MockAlerter send_alert method."""
        mock_alerter = MockAlerter(webhook_url="http://test.com")
        received_messages = []

        def test_callback(message: str) -> None:
            received_messages.append(message)

        mock_alerter.callback = test_callback
        mock_alerter.send_alert("Test message")

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0], "Test message")

    def test_mock_alerter_send_alert_async(self) -> None:
        """Test MockAlerter send_alert_async method."""
        mock_alerter = MockAlerter(webhook_url="http://test.com")
        received_messages = []

        def test_callback(message: str) -> None:
            received_messages.append(message)

        mock_alerter.callback = test_callback

        import asyncio
        asyncio.run(mock_alerter.send_alert_async("Test async message"))

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0], "Test async message")

    def test_mock_alerter_equality(self) -> None:
        """Test MockAlerter equality with same callback."""
        mock1 = MockAlerter(webhook_url="http://test.com")
        mock2 = MockAlerter(webhook_url="http://test.com")

        # Set same callback for both
        def dummy_callback(msg: str) -> None:
            pass
        mock1.callback = dummy_callback
        mock2.callback = dummy_callback

        self.assertEqual(mock1, mock2)


class TestSlackAlerter(unittest.TestCase):
    """Test SlackAlerter functionality."""

    def test_slack_alerter_initialization(self) -> None:
        """Test SlackAlerter initialization."""
        slack_alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/test/webhook")
        self.assertEqual(slack_alerter.webhook_url, "https://hooks.slack.com/services/test/webhook")
        self.assertEqual(slack_alerter.TYPE, "Slack")
        self.assertEqual(slack_alerter.alert_id, "test/webhook")

    def test_slack_alerter_get_id_extraction(self) -> None:
        """Test SlackAlerter ID extraction from webhook URL."""
        slack_alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/test/webhook")
        self.assertEqual(slack_alerter.alert_id, "test/webhook")

    def test_slack_alerter_get_id_fallback(self) -> None:
        """Test SlackAlerter ID fallback for non-standard URLs."""
        slack_alerter = SlackAlerter(webhook_url="https://custom.slack.com/webhook")
        self.assertEqual(slack_alerter.alert_id, "https://custom.slack.com/webhook")

    @patch('ryutils.alerts.slack.WebhookClient')
    def test_slack_alerter_send_alert_success(self, mock_webhook_client: Mock) -> None:
        """Test SlackAlerter send_alert success case."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.body = "ok"
        mock_webhook_client.return_value.send.return_value = mock_response

        slack_alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/test/webhook")
        slack_alerter.send_alert("Test message")

        mock_webhook_client.return_value.send.assert_called_once_with(text="Test message")

    @patch('ryutils.alerts.slack.WebhookClient')
    def test_slack_alerter_send_alert_failure(self, mock_webhook_client: Mock) -> None:
        """Test SlackAlerter send_alert failure case."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.body = "error"
        mock_webhook_client.return_value.send.return_value = mock_response

        slack_alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/test/webhook")

        with self.assertRaises(ConnectionError):
            slack_alerter.send_alert("Test message")

    @patch('ryutils.alerts.slack.WebhookClient')
    @patch('asyncio.to_thread')
    def test_slack_alerter_send_alert_async(self, mock_to_thread: Mock, mock_webhook_client: Mock) -> None:
        """Test SlackAlerter send_alert_async method."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.body = "ok"
        mock_webhook_client.return_value.send.return_value = mock_response

        slack_alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/test/webhook")

        import asyncio
        asyncio.run(slack_alerter.send_alert_async("Test async message"))

        mock_to_thread.assert_called_once()


class TestDiscordAlerter(unittest.TestCase):
    """Test DiscordAlerter functionality."""

    def test_discord_alerter_initialization(self) -> None:
        """Test DiscordAlerter initialization."""
        discord_alerter = DiscordAlerter(
            webhook_url="https://discord.com/api/webhooks/test",
            title="Test Alert"
        )
        self.assertEqual(discord_alerter.webhook_url, "https://discord.com/api/webhooks/test")
        self.assertEqual(discord_alerter.title, "Test Alert")
        self.assertEqual(discord_alerter.TYPE, "Discord")
        self.assertEqual(discord_alerter.alert_id, "https://discord.com/api/webhooks/test")

    def test_discord_alerter_add_title(self) -> None:
        """Test DiscordAlerter add_title method."""
        discord_alerter = DiscordAlerter(
            webhook_url="https://discord.com/api/webhooks/test",
            title="Original Title"
        )
        self.assertEqual(discord_alerter.title, "Original Title")

        discord_alerter.add_title("New Title")
        self.assertEqual(discord_alerter.title, "New Title")

    @patch('ryutils.alerts.discord.DiscordWebhook')
    @patch('ryutils.alerts.discord.DiscordEmbed')
    def test_discord_alerter_send_alert_success(self, mock_embed: Mock, mock_webhook: Mock) -> None:
        """Test DiscordAlerter send_alert success case."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_webhook.return_value.execute.return_value = mock_response

        discord_alerter = DiscordAlerter(
            webhook_url="https://discord.com/api/webhooks/test",
            title="Test Alert"
        )
        discord_alerter.send_alert("Test message")

        mock_embed.assert_called_once_with(title="Test Alert", description="Test message")
        mock_webhook.return_value.add_embed.assert_called_once()
        mock_webhook.return_value.execute.assert_called_once_with(remove_embeds=True)

    @patch('ryutils.alerts.discord.DiscordWebhook')
    @patch('ryutils.alerts.discord.DiscordEmbed')
    def test_discord_alerter_send_alert_failure(self, mock_embed: Mock, mock_webhook: Mock) -> None:
        """Test DiscordAlerter send_alert failure case."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "error"
        mock_webhook.return_value.execute.return_value = mock_response

        discord_alerter = DiscordAlerter(
            webhook_url="https://discord.com/api/webhooks/test",
            title="Test Alert"
        )

        with self.assertRaises(ConnectionError):
            discord_alerter.send_alert("Test message")

    @patch('ryutils.alerts.discord.DiscordWebhook')
    @patch('ryutils.alerts.discord.DiscordEmbed')
    @patch('asyncio.to_thread')
    def test_discord_alerter_send_alert_async(self, mock_to_thread: Mock, mock_embed: Mock, mock_webhook: Mock) -> None:
        """Test DiscordAlerter send_alert_async method."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_webhook.return_value.execute.return_value = mock_response

        discord_alerter = DiscordAlerter(
            webhook_url="https://discord.com/api/webhooks/test",
            title="Test Alert"
        )

        import asyncio
        asyncio.run(discord_alerter.send_alert_async("Test async message"))

        mock_to_thread.assert_called_once()


class TestAlertFactory(unittest.TestCase):
    """Test AlertFactory functionality."""

    def test_create_mock_alert(self) -> None:
        """Test creating MockAlerter via factory."""
        args = argparse.Namespace()
        args.webhook_url = "https://test.com/webhook"

        alert = AlertFactory.create_alert(AlertType.MOCK, args)

        self.assertIsInstance(alert, MockAlerter)
        self.assertEqual(alert.webhook_url, "https://test.com/webhook")

    def test_create_slack_alert(self) -> None:
        """Test creating SlackAlerter via factory."""
        args = argparse.Namespace()
        args.webhook_url = "https://hooks.slack.com/services/test/webhook"

        alert = AlertFactory.create_alert(AlertType.SLACK, args)

        self.assertIsInstance(alert, SlackAlerter)
        self.assertEqual(alert.webhook_url, "https://hooks.slack.com/services/test/webhook")

    def test_create_discord_alert_with_title(self) -> None:
        """Test creating DiscordAlerter via factory with title."""
        args = argparse.Namespace()
        args.webhook_url = "https://discord.com/api/webhooks/test"
        args.title = "Custom Title"

        alert = AlertFactory.create_alert(AlertType.DISCORD, args)

        self.assertIsInstance(alert, DiscordAlerter)
        self.assertEqual(alert.webhook_url, "https://discord.com/api/webhooks/test")
        self.assertEqual(alert.title, "Custom Title")

    def test_create_discord_alert_without_title(self) -> None:
        """Test creating DiscordAlerter via factory without title."""
        args = argparse.Namespace()
        args.webhook_url = "https://discord.com/api/webhooks/test"
        # No title attribute

        alert = AlertFactory.create_alert(AlertType.DISCORD, args)

        self.assertIsInstance(alert, DiscordAlerter)
        self.assertEqual(alert.webhook_url, "https://discord.com/api/webhooks/test")
        self.assertEqual(alert.title, "Alert")  # Default title

    @patch('ryutils.log.print_normal')
    def test_create_alert_verbose(self, mock_print: Mock) -> None:
        """Test creating alert with verbose logging."""
        args = argparse.Namespace()
        args.webhook_url = "https://test.com/webhook"

        AlertFactory.create_alert(AlertType.MOCK, args, verbose=True)

        mock_print.assert_called_once_with("Attempting to create AlertType.MOCK alerter")


class TestAlertType(unittest.TestCase):
    """Test AlertType enum functionality."""

    def test_alert_type_values(self) -> None:
        """Test AlertType enum values."""
        self.assertEqual(AlertType.SLACK.value, SlackAlerter)
        self.assertEqual(AlertType.DISCORD.value, DiscordAlerter)
        self.assertEqual(AlertType.MOCK.value, MockAlerter)

    def test_alert_type_string_representation(self) -> None:
        """Test AlertType string representation."""
        self.assertEqual(str(AlertType.SLACK), "SLACK")
        self.assertEqual(str(AlertType.DISCORD), "DISCORD")
        self.assertEqual(str(AlertType.MOCK), "MOCK")

    def test_alert_type_repr(self) -> None:
        """Test AlertType repr."""
        self.assertEqual(repr(AlertType.SLACK), "SLACK")
        self.assertEqual(repr(AlertType.DISCORD), "DISCORD")
        self.assertEqual(repr(AlertType.MOCK), "MOCK")


if __name__ == '__main__':
    unittest.main()
