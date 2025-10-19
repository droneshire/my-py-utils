import enum

from ryutils.alerts.discord import DiscordAlerter
from ryutils.alerts.mock import MockAlerter
from ryutils.alerts.slack import SlackAlerter


class AlertType(enum.Enum):
    SLACK = SlackAlerter
    DISCORD = DiscordAlerter
    MOCK = MockAlerter

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name
