import sched
import requests
import datetime
import logging
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict

from sqlalchemy import delete
from .models import Schedule, Reservation
from .db import Session

logger = logging.getLogger(__name__)

PAGE = "https://lai.kal-soft.com/Schedule.asp?location=1"


def clean_text(txt: str) -> str:
    """
    clean text scraped by replacing invisible characters
    """
    return txt.replace("&nbsp;", "").strip()


def gen_url(target_date: datetime.date) -> str:
    """
    generate url for target date
    """
    return f"{PAGE}&date={target_date.strftime('%m/%d/%Y')}"


def get_page_content(target_date: datetime.date) -> str:
    """
    get page content for target date using request
    """
    logger.info(f"Retreiving page content for {target_date.ctime()}")
    r = requests.get(gen_url(target_date))
    return r.text


def parse_page(
    page_content: str, target_date: datetime.date, include: List[str] = None, exclude: List[str] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    parse page, extracting and updating reservations for given dates

    if include is specified, only include tail codes in this list
    if exclude is specified include all tail codes not in this list
    if neither include nor exclude is specified include all tail codes

    :param page_content: html page content
    :param target_date: date page content was scraped from
    :param include: list of tail codes to track, defaults to None
    :param exclude: list of tail codes to NOT track, defaults to None
    :return: lists of deleted, created reservations in dictionary format
    """
    logger.info(f"Parsing schedule for {target_date.ctime()}")

    # parse content
    soup = BeautifulSoup(page_content, "html.parser")
    new_schedule = soup.find("table", {"id": "schedule"})
    if not new_schedule:
        logging.error(
            "Unable to find 'schedule' table in response from web server"
        )
        return None, None
    
    # get iterable rows of table
    rows = new_schedule.findChildren("tr", recursive=False)

    # parse times array to determine starting and stopping times
    times = []
    times_row = rows[0]
    thirty_min_delta = datetime.timedelta(minutes=30)
    for col in times_row.findChildren("td", recusive=False):
        txt = clean_text(col.getText())
        if txt == "Tail Number":
            continue
        else:
            try:
                # process string to get hours as number
                hour = int(txt.split(":")[0].strip())
                if "PM" in txt and hour != 12:
                    hour += 12
            except Exception as e:
                logging.error(e)
                return None, None
            
            # add on the hour time and +30 min
            base = datetime.datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=hour,
            )
            extra_half = base + thirty_min_delta
            times.append(base)
            times.append(extra_half)

    # add additional 30 min increment to allow end time
    if times:
        times.append(times[-1] + thirty_min_delta)
    else:
        logging.error("No time array exists, unable to continue parsing")
        return None, None
    
    parsed_reservations = []
    # skip first row as we already parsed it for timings
    # skip last row because it contains timings again
    for row in rows[1:-1]:
        # get columns
        tds = row.findChildren("td", recusive=False)

        # extract tail code from row
        tail_code = clean_text(tds[0].getText())

        # skip rest of row if we shouldn't check it
        if exclude and tail_code in exclude:
            continue
        elif include and tail_code not in include:
            continue

        # parse existing reservations from rest of row
        time_ind = 0
        for col in tds[1:]:
            txt = clean_text(col.getText())
            if txt == "Reserved":
                # get number of time increments reservation spans
                res_length = int(col["colspan"].strip())
                start = times[time_ind]
                end = times[time_ind + res_length]
                
                # generate reservation out of session
                new_res = Reservation(tail_code=tail_code, start=start, end=end)
                parsed_reservations.append(new_res)

                time_ind += res_length
            else:
                time_ind += 1

    # find differences between parsed schedule and last saved schedule for target date
    deleted_reservations = []
    created_reservations = []
    with Session.begin() as session:
        schedule = session.query(Schedule).filter_by(date=target_date).first()
        if not schedule:
            # create schedule and add reservations
            new_schedule = Schedule(date=target_date)
            session.add(new_schedule)
            for reservation in parsed_reservations:
                session.add(reservation)
                new_schedule.reservations.append(reservation)
        else:
            # find reservations deleted since last parse
            for reservation in schedule.reservations:
                if reservation not in parsed_reservations:
                    deleted_reservations.append(reservation.to_dict())
                    schedule.reservations.remove(reservation)
                    session.delete(reservation)

            # find reservations created since last parse
            for reservation in parsed_reservations:
                if reservation not in schedule.reservations:
                    created_reservations.append(reservation.to_dict())
                    schedule.reservations.append(reservation)
                    session.add(reservation)

    if deleted_reservations:
        logger.info(f"Created: {deleted_reservations}")
    if created_reservations:
        logger.info(f"Deleted: {created_reservations}")

    logger.info(f"Completed parsing schedule for {target_date.ctime()}")
    return deleted_reservations, created_reservations


def get_changes(target_date: datetime.date, include: List[str] = None, exclude: List[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    fetch content, parse, and extract changes since last run for specified target date

    :param target_date: date to check for changes on
    :param include: list of tail codes to track, defaults to None
    :param exclude: list of tail codes to NOT track, defaults to None
    :return: lists of deleted, created reservations in dictionary format
    """
    content = get_page_content(target_date)
    deleted_reservations, created_reservations = parse_page(content, target_date, include, exclude)
    return deleted_reservations, created_reservations

def get_changes_days(target_dates: List[datetime.date], include: List[str] = None, exclude: List[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    fetch content, parse, and extract changes since last run for all specified target dates

    :param target_dates: list of dates to check for changes on
    :param include: list of tail codes to track, defaults to None
    :param exclude: list of tail codes to NOT track, defaults to None
    :return: lists of deleted, created reservations in dictionary format (combined from all dates)
    """
    deleted_reservations = []
    created_reservations = []
    for date in target_dates:
        curr_del, curr_cre = get_changes(date, include, exclude)
        deleted_reservations.extend(curr_del)
        created_reservations.extend(curr_cre)
    return deleted_reservations, created_reservations
