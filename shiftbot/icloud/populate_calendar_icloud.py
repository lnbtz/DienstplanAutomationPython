import logging
import datetime
import os
from pathlib import Path
from sqlalchemy import select
from dotenv import load_dotenv
from caldav import DAVClient
from icalendar import Calendar as ICalendar, Event as ICalEvent

from shiftbot.db.db import get_session
from shiftbot.db.models.event import Event
from shiftbot.util import create_sha256_hash

provider = "icloud"
load_dotenv()
CALENDAR_NAME = "Work"
USERNAME = os.getenv("ICLOUD_USERNAME")
PASSWORD = os.getenv("ICLOUD_PASSWORD")
try:
    assert USERNAME is not None
    assert PASSWORD is not None
except AssertionError:
    raise ValueError("ICLOUD_USERNAME and ICLOUD_PASSWORD must be set in environment variables.")


def populate_calendar():
    """Push planned events to iCloud calendar. Returns stats dict."""
    stats = {"upserted": 0, "skipped": 0, "failures": 0}
    client = DAVClient(url="https://caldav.icloud.com/", username=USERNAME, password=PASSWORD)
    principal = client.principal()
    calendar = principal.calendar(name=CALENDAR_NAME)
    if not calendar:
        logging.getLogger("shiftbot").warning("Calendar '%s' not found", CALENDAR_NAME)
        logging.getLogger("shiftbot").info("No events to sync to calendar", extra={"skipped": 1})
        return stats

    with get_session() as db:
        stmt = select(Event).where(Event.status == "planned", Event.provider.is_(None))
        result = db.execute(stmt)
        events = result.scalars().all()
        for event in events:
            try:
                cal = ICalendar()
                cal.add('prodid', '-//dienstplan-automation//EN')
                cal.add('version', '2.0')
                ical_event = ICalEvent()
                ical_event.add('uid', event.event_uid)
                ical_event.add('dtstamp', datetime.datetime.now(datetime.timezone.utc))
                ical_event.add('dtstart', event.start_utc)
                ical_event.add('dtend', event.end_utc)
                ical_event.add('summary', event.shift_type)
                ical_event.add('description', f"Shift imported from PDF (file: {event.attachment.filename})")
                ical_event.add('location', event.location)
                cal.add_component(ical_event)
                ical_bytes = cal.to_ical()
                calendar.save_event(ical_bytes)
                event.checksum = create_sha256_hash(ical_bytes)
                event.provider = provider
                event.provider_event_id = str(ical_event.uid)
                event.first_synced_at_utc = datetime.datetime.now(datetime.timezone.utc)
                event.last_synced_at_utc = datetime.datetime.now(datetime.timezone.utc)
                event.status = "synced"
                db.add(event)
                stats["upserted"] += 1
            except Exception:
                stats["failures"] += 1
                logging.getLogger("shiftbot").exception(
                    "Failed to sync event %s", event.event_uid
                )
        db.commit()
    logging.getLogger("shiftbot").info(
        "Calendar sync complete (upserted=%s, failures=%s)",
        stats["upserted"], stats["failures"], extra=stats
    )
    return stats