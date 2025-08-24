"""
Dummy class for testing purposes.
"""

import typing as T

from ryutils.alerts.alerter import Alerter


class MockAlerter(Alerter):
    TYPE = "Mock"

    def __init__(self, webhook_url: str) -> None:
        super().__init__(webhook_url)
        self.webhook_url = webhook_url
        self._callback: T.Callable[[str], None] = lambda _: None

    @property
    def callback(self) -> T.Callable[[str], None]:
        return self._callback

    @callback.setter
    def callback(self, callback: T.Callable[[str], None]) -> None:
        self._callback = callback

    def send_alert(self, message: str) -> None:
        self.callback(message)

    async def send_alert_async(self, message: str) -> None:
        self.send_alert(message)
