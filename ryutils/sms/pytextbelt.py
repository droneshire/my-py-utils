from typing import Any, Dict, Optional

import requests


class Textbelt:

    # API URL
    API_URL: str = "http://textbelt.com/"

    # The Recipient Class
    class Recipient:

        # Available Regions
        REGIONS: Dict[str, str] = {"us": "text", "ca": "canada", "intl": "intl"}

        def __init__(
            self, phone: str, key: str, region: str = "us", tag: Optional[str] = None
        ) -> None:
            self.region = region
            self.phone = phone
            self.tag = tag  # type: ignore
            self.key = key

        @property
        def phone(self) -> str:
            return self._phone

        @phone.setter
        def phone(self, phone: str) -> None:
            self._phone = str(phone)

        @property
        def region(self) -> str:
            return self._region

        @region.setter
        def region(self, region: str) -> None:
            assert region in Textbelt.Recipient.REGIONS, "Bad Region Code"
            self._region = Textbelt.Recipient.REGIONS[region]

        @property
        def tag(self) -> str:
            return self._tag

        @tag.setter
        def tag(self, tag: str) -> None:
            self._tag = tag

        # Send The Message
        def send(self, message: str) -> Dict[str, Any]:
            message = str(message)
            assert len(message) > 1, "Message Too Short"

            # API URL
            url = Textbelt.API_URL + self.region

            response = requests.post(
                url,
                {
                    "number": self.phone,
                    "message": message,
                    "key": self.key,
                },
                timeout=10,
            )

            if response.status_code != 200:
                raise ValueError("Bad Response")

            return dict(response.json())
