"""
Factory for creating alerts and the associated CLI arguments.
"""

import argparse
import typing as T

from ryutils import log
from ryutils.alerts.alert_types import AlertType
from ryutils.alerts.alerter import Alerter


class AlertFactory:
    @staticmethod
    def create_alert(
        alert_type: AlertType, args: argparse.Namespace, verbose: bool = False
    ) -> Alerter:
        alert_class_type = alert_type.value

        if verbose:
            log.print_normal(f"Attempting to create {alert_type} alerter")

        return T.cast(Alerter, alert_class_type(args.webhook_url))
