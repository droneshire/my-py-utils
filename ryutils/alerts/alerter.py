"""
Interface class for alerters.

Alerters are classes that send alerts to users.
"""

import abc


class Alerter(abc.ABC):
    """
    Interface class for alerters.

    Alerters are classes that send alerts to users.
    """

    def __init__(self, alert_id: str, alerter_type: str = "Alerter") -> None:
        self.alert_id = alert_id
        self.TYPE = alerter_type

    @abc.abstractmethod
    def send_alert(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to the specified recipients.

        Args:
            message (str): The alert message to send.
            title (str | None): Optional title for the alert.

        Returns:
            None
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def send_alert_async(self, message: str, title: str | None = None) -> None:
        """
        Sends an alert message to the specified recipients.

        Args:
            message (str): The alert message to send.
            title (str | None): Optional title for the alert.

        Returns:
            None
        """
        raise NotImplementedError

    def __str__(self) -> str:
        return self.TYPE

    def __repr__(self) -> str:
        return f"{self.TYPE}({self.alert_id})"

    def __hash__(self) -> int:
        return hash((self.alert_id, self.TYPE))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Alerter):
            return False
        return self.TYPE == other.TYPE and self.alert_id == other.alert_id

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Alerter):
            return NotImplemented
        return (self.alert_id, self.TYPE) < (other.alert_id, other.TYPE)
