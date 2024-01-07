import datetime
import os
import typing as T
import unittest

import dotenv
from util.twilio_util import TwilioUtil

from . import log


class TwilioUtilStub(TwilioUtil):
    def __init__(self):
        super().__init__("", "", "", verbose=True, time_between_sms=0)
        self.num_sent = 0
        self.send_to = ""
        self.content = ""
        self.now: datetime.datetime = datetime.datetime(2021, 1, 1, 12 + 8, 0, 0)

    def send_sms_if_in_window(
        self,
        to_number: str,
        content: str,
        now: datetime.datetime = datetime.datetime.utcnow(),
    ) -> None:
        super().send_sms_if_in_window(to_number, content, self.now)

    def send_sms(self, to_number: str, content: str) -> None:
        log.print_normal(f"Sending SMS to {to_number} with content:\n{content}")
        self.num_sent += 1
        self.send_to = to_number
        self.content = content
        return

    def reset(self) -> None:
        self.num_sent = 0
        self.send_to = ""
        self.content = ""
        return


class TwilioTest(unittest.TestCase):
    twilio_stub: TwilioUtilStub = None
    test_dir: str = os.path.join(os.path.dirname(__file__), "test_data")
    test_client_name = "test"
    test_num = "+1234567890"

    def setUp(self) -> None:
        self.twilio_stub = TwilioUtilStub()

        dotenv.load_dotenv(".env")

    def tearDown(self) -> None:
        dotenv.load_dotenv(".env")

        self.twilio_stub = None


if __name__ == "__main__":
    unittest.main()
