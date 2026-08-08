import logging

logger = logging.getLogger(__name__)


class NotificationsService:
    """Service class for handling notifications."""

    @staticmethod
    def _send_code_via_email(email: str, code: str):
        # Placeholder for sending the code via email
        logger.info(f"Sending code to email {email}")
        # In a real implementation, integrate with an email service provider here.
