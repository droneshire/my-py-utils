"""
Dummy class for testing purposes.
"""

import typing as T
from dataclasses import dataclass, field

from ryutils.alerts.alerter import Alerter


@dataclass
class MockAlerter(Alerter):
    webhook_url: str
    _callback: T.Callable[[str], None] = field(default_factory=lambda: lambda _: None)

    def __post_init__(self) -> None:
        # Call parent constructor
        super().__init__(self.webhook_url, "Mock")

    @property
    def callback(self) -> T.Callable[[str], None]:
        return self._callback

    @callback.setter
    def callback(self, callback: T.Callable[[str], None]) -> None:
        self._callback = callback

    def send_alert(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message using the callback.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert (ignored for Mock).
        """
        self.callback(message)

    async def send_alert_async(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message using the callback.

        Args:
            message (str): The message to be sent.
            title (str | None): Optional title for the alert (ignored for Mock).
        """
        self.send_alert(message)
