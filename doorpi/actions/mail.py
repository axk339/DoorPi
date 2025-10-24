"""Actions related to emails: mailto"""

import email.message
import logging
import smtplib
from typing import Any, Mapping, Optional

import doorpi
from doorpi import metadata
from doorpi.actions import snapshot

from . import Action

LOGGER = logging.getLogger(__name__)


class MailAction(Action):
    """Send an email"""

    def __init__(
        self,
        to: str,
        subject: str = "Doorbell",
        text: str = "Someone rang the door!",
        attach_snapshot: str = "false",
    ) -> None:
        super().__init__()
        self.__subject = subject
        self.__snap = attach_snapshot.lower().strip() in {
            "true",
            "yes",
            "on",
            "1",
        }

        cfg = doorpi.INSTANCE.config.view(("mail", to))

        self.__host = cfg["server"]
        self.__port = cfg["port"]
        __email = cfg["email"]

        need_login = cfg["need_login"]
        if need_login:
            self.__user = cfg["username"]
            self.__pass = cfg["password"]
        else:
            self.__user = self.__pass = None

        self.__to = cfg["receiver"]
        self.__from = __email
        if not self.__to:
            self.__to = (self.__from,)
        self.__ssl = cfg["ssl"]
        self.__starttls = cfg["tls"]
        self.__signature = cfg["signature"]

        if text.startswith("/"):
            # Read actual text from file
            self.__textfile: Optional[str] = text
            with open(text, "rt") as textfile:
                self.__text = textfile.read()
        else:
            self.__textfile = None
            self.__text = text

        if not __email:
            raise ValueError("Email has to be defined")
        if not self.__host:
            raise ValueError("No SMTP host set")
        if self.__port < 0 or self.__port > 65535:
            raise ValueError("Invalid SMTP port")
        if need_login and not self.__user:
            raise ValueError("need_login = True, but no SMTP user specified")
        if self.__ssl and self.__starttls:
            raise ValueError("Cannot combine SSL and STARTTLS")

        # Test the SMTP connection by greeting the server and logging in
        with smtplib.SMTP_SSL(
            self.__host, self.__port
        ) if self.__ssl else smtplib.SMTP(self.__host, self.__port) as smtp:
            self._start_session(smtp)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        msg = email.message.EmailMessage()
        msg["To"] = ", ".join(self.__to)
        msg["From"] = self.__from or '"{}" <{}@{}>'.format(
            metadata.distribution.metadata["Name"], self.__user, self.__host
        )
        msg["Subject"] = doorpi.INSTANCE.parse_string(self.__subject)

        text = self.__text
        if self.__signature:
            text += f"\n\n{self.__signature}"
        msg.set_content(doorpi.INSTANCE.parse_string(text))

        if self.__snap:
            try:
                snapfile = snapshot.SnapshotAction.list_all()[-1]
                snap_data = snapfile.read_bytes()
                msg.add_attachment(
                    snap_data,
                    "application",
                    "octet-stream",
                    cte="base64",
                    disposition="attachment",
                    filename=snapfile.name,
                )
            except IndexError:
                LOGGER.error("No snapshots to attach to email")
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception(
                    "[%s] Cannot attach snapshot to email", event_id
                )

        session: smtplib.SMTP
        if self.__ssl:
            session = smtplib.SMTP_SSL(self.__host, self.__port)
        else:
            session = smtplib.SMTP(self.__host, self.__port)
        try:
            with session as smtp:
                self._start_session(smtp)
                smtp.send_message(msg)

        except smtplib.SMTPException as err:
            LOGGER.error(
                "Failed sending email to %s: %s: %s",
                self.__to,
                type(err).__name__,
                err,
            )
        else:
            LOGGER.info("Sent email to %s", ', '.join(self.__to))

    def _start_session(self, smtp: smtplib.SMTP) -> None:
        if self.__starttls:
            smtp.starttls()
        if self.__user:
            smtp.login(self.__user, self.__pass)

    def __str__(self) -> str:
        return f"Send a mail to {', '.join(self.__to)}"

    def __repr__(self) -> str:
        return (
            f"mailto:{self.__to},{self.__subject},"
            f"{self.__textfile or self.__text},{self.__snap}"
        )
