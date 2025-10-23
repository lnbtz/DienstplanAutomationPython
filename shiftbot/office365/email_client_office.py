import logging
from datetime import datetime
from pathlib import Path
from typing import Union
from dotenv import load_dotenv
import os
from imap_tools import MailBox, MailMessage, MailAttachment
from email.utils import parseaddr


load_dotenv()
ALLOWED_SENDERS = {"leonbeitz@hotmail.de", "d.back@c68ad.de"}
STORAGE_DIR = Path(os.getenv("ATTACHMENT_DIR", "attachments"))
USERNAME = os.getenv("OFFICE365_USERNAME")
PASSWORD = os.getenv("OFFICE365_PASSWORD")
IMAP_SERVER = os.getenv("OFFICE365_IMAP_SERVER", "outlook.office365.com")
try:
    assert USERNAME is not None
    assert PASSWORD is not None
except AssertionError:
    raise ValueError("OFFICE365_USERNAME and OFFICE365_PASSWORD must be set in environment variables.")


def fetch_emails():
    """Fetch emails from Office365 and process relevant attachments.

    Returns a stats dict: scanned, matched, skipped, failures.
    """

    mailbox = MailBox(IMAP_SERVER).login(USERNAME, PASSWORD)
    with mailbox:
        for mail in mailbox.fetch(reverse=True, limit=20):
            print(mail.subject)
            print(mail.from_)
            print(mail.attachments)
            break

if __name__ == "__main__":
    fetch_emails()