import logging
import os
from shiftbot.icloud.email_client_icloud import fetch_emails
from shiftbot.parse_pdf import handle_attachments
from shiftbot.icloud.populate_calendar_icloud import populate_calendar
from shiftbot.run_logging import RunTracker, RUN_LOGGER_NAME

def main():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    logger = logging.getLogger(RUN_LOGGER_NAME)
    logger.info("Starting DienstplanAutomation run", extra={"scanned": 0})
    with RunTracker():
        logger.info("Scanning iCloud inbox for DP emails…")
        fetch_emails()  # emits summary log with counters

        logger.info("Parsing next unvalidated PDF attachment…")
        handle_attachments()  # emits summary log with counters

        logger.info("Syncing planned events to iCloud calendar…")
        populate_calendar()  # emits summary log with counters

if __name__ == "__main__":
    main()
