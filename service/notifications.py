import logging
import os

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


load_dotenv()


class NotificationsService:
    """Service class for handling notifications."""

    def __init__(self):
        self.mail_api_key = os.getenv("MAIL_API_KEY")
        self.mail_domain = os.getenv("MAIL_DOMAIN")

        self.sender_name = "Flashcards App"
        self.sender_email = f"no-reply@{self.mail_domain}"

    def _send_email(self, to_email: str, subject: str, text: str):
        """Send an email using the Mailgun API."""

        try:
            response = requests.post(
                url=f"https://api.mailgun.net/v3/{self.mail_domain}/messages",
                auth=("api", self.mail_api_key),
                data={
                    "from": f"{self.sender_name} <{self.sender_email}>",
                    "to": f"<{to_email}>",
                    "subject": subject,
                    "text": text,
                }
            )
            response.raise_for_status()
            logger.info("Email sent.")
        except requests.RequestException as e:
            logger.error(f"Failed to send login code: {e}")
            raise

    def send_verification_code(self, email: str, code: str):
        """Send a verification code to the specified email address."""

        subject = "Your Verification Code"
        text = f"Your verification code is: {code}."

        self._send_email(to_email=email, subject=subject, text=text)

    def health_check(self):
        """Check the health of the notifications service."""

        try:
            response = requests.get(
                url=f"https://api.mailgun.net/v3/domains/{self.mail_domain}",
                auth=("api", self.mail_api_key),
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Notifications service health check failed: {e}")
            return False
