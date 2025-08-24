"""
Alert module for Discord
"""

import asyncio

from discord_webhook import DiscordEmbed, DiscordWebhook

from ryutils.alerts.alerter import Alerter


class DiscordAlerter(Alerter):
    TYPE = "Discord"

    def __init__(self, webhook_url: str, title: str) -> None:
        super().__init__(webhook_url)
        self.title = title
        self.webhook = DiscordWebhook(url=webhook_url)

    def send_alert(self, message: str) -> None:
        """
        Sends an alert message to Discord.

        Args:
            message (str): The message to be sent.

        Raises:
            Exception: If the alert fails to be sent to Discord.
        """
        embed = DiscordEmbed(title=self.title, description=message)
        self.webhook.add_embed(embed)
        response = self.webhook.execute(remove_embeds=True)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to send alert to Discord: {response.text}")

    async def send_alert_async(self, message: str) -> None:
        """
        Sends an alert message to Discord.

        Args:
            message (str): The message to be sent.

        Raises:
            Exception: If the alert fails to be sent to Discord.
        """
        embed = DiscordEmbed(title=self.title, description=message)
        self.webhook.add_embed(embed)
        response = await asyncio.to_thread(self.webhook.execute, remove_embeds=True)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to send alert to Discord: {response.text}")
