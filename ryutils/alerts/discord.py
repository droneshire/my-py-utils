"""
Alert module for Discord
"""

import asyncio
from dataclasses import dataclass

from discord_webhook import DiscordEmbed, DiscordWebhook

from ryutils.alerts.alerter import Alerter


@dataclass
class DiscordAlerter(Alerter):
    webhook_url: str

    def __post_init__(self) -> None:
        # Call parent constructor
        super().__init__(self.webhook_url, "Discord")
        self.webhook = DiscordWebhook(url=self.webhook_url)

    def send_alert(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to Discord.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert.

        Raises:
            Exception: If the alert fails to be sent to Discord.
        """
        alert_title = title or "Alert"
        embed = DiscordEmbed(title=alert_title, description=message)
        self.webhook.add_embed(embed)
        response = self.webhook.execute(remove_embeds=True)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to send alert to Discord: {response.text}")

    async def send_alert_async(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to Discord.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert.

        Raises:
            Exception: If the alert fails to be sent to Discord.
        """
        alert_title = title or "Alert"
        embed = DiscordEmbed(title=alert_title, description=message)
        self.webhook.add_embed(embed)
        response = await asyncio.to_thread(self.webhook.execute, remove_embeds=True)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to send alert to Discord: {response.text}")
