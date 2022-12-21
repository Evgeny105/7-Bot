from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from config import PG_URL

Base = declarative_base()
engine = create_async_engine(
    PG_URL,
    echo=True,
)


class Users(Base):
    __tablename__ = "users"

    user_id = Column(Integer, unique=True, primary_key=True, index=True)
    user_login = Column(String)
    user_name = Column(String)
    user_tz = Column(String)


class Reminders(Base):
    __tablename__ = "reminders"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.user_id"))
    type_of_reminder = Column(String)
    reminder = Column(String)
    reminder_time = Column(DateTime)
