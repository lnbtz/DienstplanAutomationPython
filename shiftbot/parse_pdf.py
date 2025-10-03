import logging
import datetime
import pymupdf
from enum import Enum

from sqlalchemy import select

from shiftbot.db.models.attachment import Attachment
from shiftbot.db.models.message import Message
from shiftbot.db.db import get_session
from shiftbot.db.models.event import Event
from zoneinfo import ZoneInfo
from shiftbot.util import create_sha256_hash

LOCAL_TZ = "Europe/Berlin"
USERNAME = "Beitz"

class ShiftType(Enum):
  DAYSHIFT = 4
  NIGHTSHIFT = 7
  DAYSHIFT_BACKUP = 8
  NIGHTSHIFT_BACKUP = 9
  
  @staticmethod
  def get_shift_type(index: int) -> "ShiftType":
    # raises ValueError if index not valid
    return ShiftType(index)
    
_SHIFT_SCHEDULE = {
  ShiftType.DAYSHIFT: ("09:00", "12"),
  ShiftType.NIGHTSHIFT: ("21:00", "12"),
  ShiftType.DAYSHIFT_BACKUP: ("09:00", "1"),
  ShiftType.NIGHTSHIFT_BACKUP: ("21:00", "1"),
}

_SHIFT_NAMES = {
  ShiftType.DAYSHIFT: ("Dienst Tag"),
  ShiftType.NIGHTSHIFT: ("Dienst Nacht"),
  ShiftType.DAYSHIFT_BACKUP: ("Rufbereitschaft Tag"),
  ShiftType.NIGHTSHIFT_BACKUP: ("Rufbereitschaft Nacht"),
}

def get_shift_start_time_and_duration(shift_type: ShiftType):
  try:
    return _SHIFT_SCHEDULE[shift_type]
  except KeyError:
    raise ValueError(f"Unknown shift type: {shift_type!r}")

def get_shift_name(shift_type):
  try:
    return _SHIFT_NAMES[shift_type]
  except KeyError:
    raise ValueError(f"Unknown shift type: {shift_type!r}")

def handle_attachments():
  """Parse the next unvalidated attachment (if any) and persist events.

  Returns a stats dict: parsed, skipped, failures.
  """
  stats = {"parsed": 0, "skipped": 0, "failures": 0}
  session = get_session()
  with session as db:
    stmt = select(Attachment).where(Attachment.validated.is_(False))
    result = db.execute(stmt)
    attachment: Attachment | None = result.scalars().first()
    if not attachment:
      stats["skipped"] += 1
      logging.getLogger("shiftbot").info(
        "No unvalidated attachments found", extra={"skipped": 1}
      )
      return stats
    message: Message = attachment.message
    path = attachment.stored_path
  text = get_text_from_pdf(path)
  events = parse_shifts(text, attachment, message)
  with session as db:
    for event in events:  
      db.add(event)
    attachment.validated = True
    db.add(attachment)
    db.commit()
  stats["parsed"] += len(events)
  logging.getLogger("shiftbot").info(
    "Parsed events from PDF (parsed=%s)", stats["parsed"], extra=stats
  )
  


def parse_shifts(text: str, attachment: Attachment, message: Message):
  events = []
  lines = text.split("\n")
  date_index = 1
  shift_type_upper_index = ShiftType.NIGHTSHIFT_BACKUP.value
  for i in range(len(lines)):
    line = lines[i]
    if line.startswith(" "):
      date = lines[i + date_index]
      for j in range(shift_type_upper_index + 1):
        line = lines[i + j]
        if USERNAME in line:
          # build shift data
          shift_type = ShiftType.get_shift_type(j)
          (start, duration) = get_shift_start_time_and_duration(shift_type)
          # parse date and start (expects date like "YYYY-MM-DD" and start like "HH:MM")
          local_zone = ZoneInfo(LOCAL_TZ)
          local_dt = datetime.datetime.strptime(f"{date} {start}", "%d.%m.%y %H:%M")
          local_dt = local_dt.replace(tzinfo=local_zone)

          # start and end as UTC datetimes
          start_utc = local_dt.astimezone(datetime.timezone.utc)
          with open(attachment.stored_path, "rb") as f:
            attachment_hash = create_sha256_hash(f.read())
          event_uid = attachment_hash + start_utc.strftime('%Y%m%dT%H%MZ')
          end_utc = (local_dt + datetime.timedelta(hours=int(duration))).astimezone(datetime.timezone.utc)
          location = "Buchenring 63, 22359 Hamburg"
          status = "planned"
          event = Event(
            event_uid=event_uid,
            start_utc=start_utc,
            end_utc=end_utc,
            local_tz=LOCAL_TZ,
            shift_type=get_shift_name(shift_type),
            location=location,
            notes=None,
            checksum=None,
            provider=None,
            provider_event_id=None,
            first_synced_at_utc=None,
            last_synced_at_utc=None,
            status=status,
            last_error=None,
            replaces_event_uid=None,
            attachment=attachment,
            message=message
          )
          events.append(event)
  return events


def get_text_from_pdf(path: str):
    doc = pymupdf.open(path)
    text = ""
    for page in doc:
      text += page.get_text()
      print(text)
      break  # only first page
    doc.close()
    return text

