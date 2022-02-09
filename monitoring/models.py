import logging
import datetime
from typing import List, Tuple, Union
from sqlalchemy import Column, ForeignKey, Integer, DateTime, Date, String
from sqlalchemy.orm import relationship
from .db import Session, Base, engine

logger = logging.getLogger(__name__)


def remove_all_old():
    """
    Remove all old database entries which are no longer relevant
    """
    with Session.begin() as session:
        today = datetime.date.today()+ datetime.timedelta(days=1)
        session.query(Schedule).filter(Schedule.date<today).delete()
        today_earliest = datetime.datetime.combine(today, datetime.datetime.min.time())
        session.query(Reservation).filter(Reservation.start<today_earliest).delete()

class Reservation(Base):
    __tablename__ = 'reservation'

    id = Column(Integer, primary_key=True)
    tail_code = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    schedule_id = Column(Integer, ForeignKey('schedule.id'))

    def __eq__(self, other):
        if self.tail_code == other.tail_code and self.start == other.start and self.end == other.end:
            return True
        return False

    def to_dict(self):
        return {"tail_code": self.tail_code, "start": self.start, "end": self.end}


class Schedule(Base):
    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    reservations = relationship("Reservation", cascade="all, delete-orphan")

Base.metadata.create_all(engine)