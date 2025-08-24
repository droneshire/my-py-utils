"""
Alert module for Slack
"""

import asyncio

from slack_sdk.webhook import WebhookClient

from ryutils.alerts.alerter import Alerter


class SlackAlerter(Alerter):
    TYPE = "Slack"
    BASE_URL = "https://hooks.slack.com/services/"

    def __init__(self, webhook_url: str) -> None:
        alert_id = self._get_id(webhook_url)
        super().__init__(alert_id)
        self.webhook = WebhookClient(webhook_url)

    def _get_id(self, webhook_url: str) -> str:
        try:
            return webhook_url.split(self.BASE_URL)[1]
        except IndexError:
            return webhook_url

    def send_alert(self, message: str) -> None:
        """
        Sends an alert message to Slack.

        Args:
            message (str): The message to be sent.

        Raises:
            Exception: If the alert fails to be sent to Slack.
        """
        self._send_alert(message)

    async def send_alert_async(self, message: str) -> None:
        """
        Sends an alert message to Slack asynchronously using the Slack SDK and aiohttp.

        Args:
            message (str): The message to be sent.

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
