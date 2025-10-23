import logging
from datetime import datetime
from pathlib import Path
from typing import Union
from dotenv import load_dotenv
import os
from imap_tools import MailBox, MailMessage, MailAttachment
from email.utils import parseaddr

from ..util import create_sha256_hash
from ..db.db import get_session
from ..db.models.attachment import Attachment
from ..db.models.message import Message

provider = "icloud"
load_dotenv()
ALLOWED_SENDERS = {"leonbeitz@hotmail.de", "d.back@c68ad.de"}
STORAGE_DIR = Path(os.getenv("ATTACHMENT_DIR", "attachments"))
USERNAME = os.getenv("ICLOUD_USERNAME")
PASSWORD = os.getenv("ICLOUD_PASSWORD")
IMAP_SERVER = os.getenv("ICLOUD_IMAP_SERVER", "imap.mail.me.com")
try:
    assert USERNAME is not None
    assert PASSWORD is not None
except AssertionError:
    raise ValueError("ICLOUD_USERNAME and ICLOUD_PASSWORD must be set in environment variables.")


def fetch_emails():
    """Fetch emails from iCloud and process relevant attachments.

    Returns a stats dict: scanned, matched, skipped, failures.
    """
    stats = {"scanned": 0, "matched": 0, "skipped": 0, "failures": 0}
    mailbox = MailBox(IMAP_SERVER).login(USERNAME, PASSWORD)
    with mailbox:
        for mail in mailbox.fetch(reverse=True, limit=20):
            stats["scanned"] += 1
            logger = logging.getLogger("shiftbot")
            try:
                subject = mail.subject
                sender = parseaddr(mail.from_ or "")[1].lower()
                allowed = sender in ALLOWED_SENDERS
                has_attachments = len(mail.attachments) > 1
                if not (allowed and has_attachments):
                    stats["skipped"] += 1
                    continue
                processed = handle_mail(mail)
                if processed:
                    stats["matched"] += 1
                    logger.info("Processed email from %s: %s", sender, subject)
                else:
                    stats["skipped"] += 1
                    logger.info("Email already processed, skipping from %s: %s", sender, subject)
            except Exception:
                stats["failures"] += 1
                logger.exception(
                    "Error processing email (sender=%s, subject=%s, uid=%s)",
                    sender,
                    subject,
                    getattr(mail, "uid", None),
                )
    # Emit a single summary log for the RunDBHandler to pick up counters
    logging.getLogger("shiftbot").info(
        "Email scan complete (scanned=%s, matched=%s, skipped=%s, failures=%s)",
        stats["scanned"], stats["matched"], stats["skipped"], stats["failures"],
        extra=stats,
    )
    return stats

def handle_mail(mail: MailMessage) -> bool:
    """Process a single email message. Returns True if processed."""
    session = get_session()
    with session as db:
        existing_msg = db.get(Message, mail.uid)
        if existing_msg:
            return False  # Skip already processed messages
        for att in mail.attachments:
            if "DP_" in att.filename and att.filename.endswith(".pdf"):
                path = save_attachment(att.payload, att.filename)
                db_insert(mail, att, path)
        return True

def db_insert(mail: MailMessage, att: MailAttachment, path: str):
    """ Insert email and attachment metadata into the database. """
    session = get_session()
    with session as db:
        msg = db.get(Message, mail.uid)
        if not msg:
            msg = Message(
                            msg_id=mail.uid,
                            from_addr=mail.from_,
                            subject=mail.subject,
                            provider=provider,
                            received_at_utc=mail.date,
                            processed_at_utc=datetime.now().astimezone(),
                            status="processed",
                            notes=None,
                        )
            attachment = Attachment(
                            filename=att.filename,
                            mime_type=att.content_type,
                            size_bytes=att.size,
                            sha256=create_sha256_hash(att.payload),  
                            validated=False,
                            stored_path=path,
                            message=msg
                        )
            msg.attachments.append(attachment)
            db.add(msg)
            db.add(attachment)
            db.commit()


def _sanitize_filename(name: str) -> str:
    # Drop any path components, keep only the final name
    return Path(name).name

def save_attachment(payload: Union[bytes, memoryview], filename: str) -> str:
    """
    Save payload to STORAGE_DIR/filename and return absolute path.
    Ensures STORAGE_DIR exists and filename is sanitized.
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(filename)
    target = STORAGE_DIR / safe_name
    # write bytes
    with open(target, "wb") as f:
        f.write(payload)
    return str(target.resolve())
