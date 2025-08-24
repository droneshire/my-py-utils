"""
Twilio alerting plugin
"""

import asyncio
import typing as T

from ryutils.alerts.alerter import Alerter
from ryutils.sms import twilio_util


class TwilioAlerter(Alerter):
    """Send SMS alerts using Twilio."""

    TYPE = "Twilio"

    def __init__(
        self,
        my_number: str,
        auth_token: str,
        sid: str,
        to_number: str,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        super().__init__(f"{my_number}:{to_number}")
        self.client: twilio_util.TwilioUtil = twilio_util.TwilioUtil(
            my_number=my_number,
            auth_token=auth_token,
            sid=sid,
            dry_run=dry_run,
            verbose=verbose,
        )
        self._to_number = to_number

    @property
    def to_number(self) -> T.Optional[str]:
        return self._to_number

    @to_number.setter
    def to_number(self, value: str) -> None:
        self._to_number = value

    def send_alert(self, message: str) -> None:
        """Send an alert."""
        if self.client is None:
            raise ValueError("Twilio client is not set up")

        if self.to_number is None:
            raise ValueError("To number is not set")

        self.client.send_sms(to_number=self.to_number, content=message)

    async def send_alert_async(self, message: str) -> None:
        """Send an alert asynchronously."""
        await asyncio.to_thread(self.send_alert, message)
