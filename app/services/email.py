import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def _is_configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)

    async def _send(self, to_email: str, subject: str, body: str) -> None:
        if not self._is_configured():
            logger.info(
                "SMTP not configured. Would send email to %s: [%s] %s",
                to_email,
                subject,
                body,
            )
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        def _send_sync():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], to_email, msg.as_string())

        try:
            await asyncio.to_thread(_send_sync)
            logger.info("Email sent to %s: [%s]", to_email, subject)
        except (smtplib.SMTPException, OSError) as e:
            logger.error("Failed to send email to %s: %s", to_email, e)

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
        await self._send(email, subject, body)

    async def send_password_reset(
        self,
        email: str,
        first_name: str,
        phone: str,
        temporary_password: str,
    ) -> None:
        subject = "Your password has been reset"
        body = (
            f"Your password has been reset by an administrator.\n\n"
            f"Login: {phone}\n"
            f"New temporary password: {temporary_password}\n\n"
            f"Please change your password after logging in."
        )
        await self._send(email, subject, body)


email_service = EmailService()
