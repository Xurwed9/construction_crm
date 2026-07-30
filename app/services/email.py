import logging

logger = logging.getLogger(__name__)


class EmailService:
    async def send_account_created(
        self,
        email: str,
        first_name: str,
        phone: str,
        temporary_password: str,
    ) -> None:
        subject = "Your CRM account"
        body = (
            f"Your account has been created.\n\n"
            f"Login: {phone}\n"
            f"Temporary password: {temporary_password}\n\n"
            f"Please change your password after logging in."
        )
        logger.info("Email to %s: [%s] %s", email, subject, body)


email_service = EmailService()
