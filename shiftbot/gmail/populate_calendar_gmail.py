import os
import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from sqlalchemy import select
from dotenv import load_dotenv
from caldav import DAVClient
from icalendar import Calendar as ICalendar, Event as ICalEvent



provider = "gmail"
load_dotenv()
CALENDAR_NAME = "Work"
USERNAME = os.getenv("GMAIL_CALENDAR_USERNAME")
PASSWORD = os.getenv("GMAIL_CALENDAR_PASSWORD")
# Optional read-only ICS URL to avoid OAuth/browser entirely
ICS_URL = os.getenv("GMAIL_CALENDAR_ICS_URL")
# Google CalDAV typically lives under apidata.googleusercontent.com and requires OAuth.
# We allow overriding via env for testing against any CalDAV-compatible server.
CALDAV_URL = os.getenv(
    "GMAIL_CALDAV_URL",
    "https://apidata.googleusercontent.com/caldav/v2/",
)
try:
    assert USERNAME is not None
    assert PASSWORD is not None
except AssertionError:
    raise ValueError("GMAIL_CALENDAR_USERNAME and GMAIL_CALENDAR_PASSWORD must be set in environment variables.")


def populate_calendar():
    """List available calendars and select the configured one."""
    try:
        client = DAVClient(url=CALDAV_URL, username=USERNAME, password=PASSWORD)
        principal = client.principal()
        calendars = principal.calendars()
        print("Available calendars:")
        for cal in calendars:
            # cal.name is typically populated; fall back to path if missing
            name = getattr(cal, "name", None) or getattr(cal, "path", "<unknown>")
            print(f"- {name}")

        # Keep existing behavior of looking up a specific calendar by name
        calendar = principal.calendar(name=CALENDAR_NAME)
        if calendar is None:
            print(f"Calendar named '{CALENDAR_NAME}' not found.")
        else:
            print(f"Selected calendar: {getattr(calendar, 'name', CALENDAR_NAME)}")
        return {"listed": len(calendars)}
    except Exception as e:
        print(f"Failed to list calendars: {e}")
        print(
            "Note: Google Calendar CalDAV requires OAuth — username/password or app passwords do not work."
        )
        print(
            "If you need headless read-only access without a browser, set GMAIL_CALENDAR_ICS_URL to your calendar's secret ICS URL."
        )
        return {"listed": 0, "error": str(e)}


def list_from_ics():
    """Fetch and summarize a calendar from its private ICS URL (read-only)."""
    if not ICS_URL:
        print("GMAIL_CALENDAR_ICS_URL is not set; cannot use ICS fallback.")
        return {"listed": 0}
    try:
        req = Request(ICS_URL, headers={"User-Agent": "dienstplan-automation/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
        cal = ICalendar.from_ical(data)
        cal_name = cal.get("X-WR-CALNAME", "Unnamed calendar")
        print("Available calendars (ICS read-only):")
        print(f"- {cal_name}")

        # Optional: show a few upcoming events as a quick sanity check
        now = datetime.datetime.now(datetime.timezone.utc)
        upcoming = []
        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart = component.get("DTSTART")
                dtend = component.get("DTEND")
                summary = str(component.get("SUMMARY", "(no title)"))
                try:
                    # Handle both date and datetime
                    start = getattr(dtstart, "dt", None) or dtstart
                    end = getattr(dtend, "dt", None) or dtend
                    # Convert date to datetime at midnight if needed
                    if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
                        start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
                    if isinstance(end, datetime.date) and not isinstance(end, datetime.datetime):
                        end = datetime.datetime.combine(end, datetime.time.min, tzinfo=datetime.timezone.utc)
                    if start >= now:
                        upcoming.append((start, end, summary))
                except Exception:
                    continue
        upcoming.sort(key=lambda x: x[0])
        for start, end, summary in upcoming[:5]:
            print(f"  • {start.isoformat()} - {end.isoformat()}: {summary}")
        return {"listed": 1, "previewed_events": min(5, len(upcoming))}
    except (HTTPError, URLError) as e:
        print(f"Failed to fetch ICS: {e}")
        return {"listed": 0, "error": str(e)}
    except Exception as e:
        print(f"Failed to parse ICS: {e}")
        return {"listed": 0, "error": str(e)}


if __name__ == "__main__":
    if ICS_URL:
        list_from_ics()
    else:
        populate_calendar()
