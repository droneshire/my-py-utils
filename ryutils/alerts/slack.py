"""
Alert module for Slack
"""

import asyncio
from dataclasses import dataclass

from slack_sdk.webhook import WebhookClient

from ryutils.alerts.alerter import Alerter


@dataclass
class SlackAlerter(Alerter):
    webhook_url: str

    def __post_init__(self) -> None:
        # Call parent constructor
        super().__init__(self.webhook_url, "Slack")
        self.webhook = WebhookClient(self.webhook_url)
        # Set alert_id from webhook_url
        self.alert_id = self._get_id(self.webhook_url)

    def _get_id(self, webhook_url: str) -> str:
        BASE_URL = "https://hooks.slack.com/services/"
        try:
            return webhook_url.split(BASE_URL)[1]
        except IndexError:
            return webhook_url

    def send_alert(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to Slack.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert (ignored for Slack).

        Raises:
            Exception: If the alert fails to be sent to Slack.
        """
        self._send_alert(message)

    async def send_alert_async(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to Slack asynchronously using the Slack SDK and aiohttp.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert (ignored for Slack).

        Raises:
            Exception: If the alert fails to be sent to Slack.
        """
        # Run the synchronous send method from the Slack SDK in a separate thread
        await asyncio.to_thread(self._send_alert, message)

    def _send_alert(self, message: str) -> None:
        """
        Synchronously sends the message using the Slack SDK.

        This method is executed in a separate thread to avoid blocking the event loop.
        """
        response = self.webhook.send(text=message)

        if response.status_code != 200 or response.body != "ok":
            error = (
                f"Failed to send alert to Slack, err: {response.status_code}"
                f" response: {response.body}"
            )
            raise ConnectionError(error)
