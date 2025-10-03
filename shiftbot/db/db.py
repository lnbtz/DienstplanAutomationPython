
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from shiftbot.config import get_url

DATABASE_URL = get_url()
# Engine = the DB connection *factory*
engine = create_engine(DATABASE_URL, future=True, echo=False)
# session = factory for Session objects (unit of work / conversation)
session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_session() -> Session:
    """
    Dependency-style helper: open a session, yield it, and ensure close.
    Use like:
        with get_session() as session:
            result = session.query(...)
    """
    return session()
