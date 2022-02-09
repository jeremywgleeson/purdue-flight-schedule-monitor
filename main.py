import datetime
import logging
import yaml
import os
from monitoring.scrape import get_changes_days
from monitoring.db import Session
from monitoring.models import Reservation, remove_all_old
from monitoring.mail import send_email

CONFIG_KEYS = ['TIME_MIN', 'TIME_MAX', 'TARGET_EMAIL', 'TARGET_EMAILS', 'PLANE_INCLUDE', 'PLANE_EXCLUDE']
SECRET_KEYS = ['EMAIL_CONTACT', 'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_LOGIN', 'EMAIL_PASSWORD']
DEFAULT_CONFIG_PATH = "./config.yaml"

def load_email_secrets():
    logging.info("Loading environmental secrets")
    config = {}
    for key in SECRET_KEYS:
        val = os.environ.get(key)
        if not val:
            logging.critical(f"No {key} supplied! This should be added as an environmental variable")
            raise Exception(key)
        config[key] = val

    return config

def load_yaml_config():
    logging.info("Loading yaml for config")
    config_path = os.environ.get("CONFIG_FILE")
    if not config_path:
        logging.info(f"No config file path supplied. Using default ({DEFAULT_CONFIG_PATH})")
        config_path = DEFAULT_CONFIG_PATH

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    stripped_config = {k:v for k,v in config.items() if k in (CONFIG_KEYS+SECRET_KEYS)}
    if 'TARGET_EMAIL' in stripped_config and 'TARGET_EMAILS' not in stripped_config:
        stripped_config['TARGET_EMAILS'] = [stripped_config['TARGET_EMAIL']]
        del stripped_config['TARGET_EMAIL']

    return stripped_config

def load_env_config():
    logging.info("Loading environmental variables for config")
    config = load_email_secrets()
    for key in CONFIG_KEYS:
        val = os.environ.get(key)
        if val:
            config[key] = val
    return config

def load_config():
    config = load_yaml_config()
    config.update(load_env_config())
    if 'TARGET_EMAIL' in config:
        if 'TARGET_EMAILS' not in config:
            config['TARGET_EMAILS'] = []
        config['TARGET_EMAILS'].append(config['TARGET_EMAIL'])
        del config['TARGET_EMAIL']
    
    if 'PLANE_INCLUDE' in config and config['PLANE_INCLUDE']:
        if 'PLANE_EXCLUDE' in config: del config['PLANE_EXCLUDE']
    elif 'PLANE_EXCLUDE' in config and config['PLANE_EXCLUDE']:
        if 'PLANE_INCLUDE' in config: del config['PLANE_INCLUDE']
    else:
        config['PLANE_INCLUDE'] = None
        config['PLANE_EXCLUDE'] = None

    return config

def test_addition():
    with Session.begin() as session:
        session.query(Reservation).filter_by(tail_code="N560PU").delete()

def test_deletion(hours_away):
    with Session.begin() as session:
        new_res = Reservation(tail_code="N560PU", start=datetime.datetime.now()+datetime.timedelta(hours=hours_away), end=datetime.datetime.now()+datetime.timedelta(hours=hours_away+1), schedule_id=3)
        session.add(new_res)


def main():
    # configure logger
    logging.basicConfig(
        filename="schedule_monitor.log",
        encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=logging.INFO,
    )
    logging.info("Starting...")

    # load config from config file and environment
    config = load_config()

    # determine how many days to scan based on TIME_MAX
    first_date = datetime.date.today()
    now = datetime.datetime.now()
    last_date = (now + datetime.timedelta(hours=float(config["TIME_MAX"]))).date()
    target_datetimes = [first_date + datetime.timedelta(days=i) for i in range((last_date-first_date).days + 1)]
    
    # determine which planes to scan for
    include = config['PLANE_INCLUDE'] if 'PLANE_INCLUDE' in config else None
    exclude = config['PLANE_EXCLUDE'] if 'PLANE_EXCLUDE' in config else None
    
    # get schedule changes
    deleted, _ = get_changes_days(target_datetimes, include=include, exclude=exclude)

    # filter deleted for only changes in target time frame
    del_filtered = []
    earliest = now + datetime.timedelta(hours=float(config["TIME_MIN"]))
    latest = now + datetime.timedelta(hours=float(config["TIME_MAX"]))
    for el in deleted:
        if el['start'] > earliest and el['start'] < latest:
            del_filtered.append(el)

    # send email containing relevant deleted reservations
    send_email(del_filtered, config['TARGET_EMAILS'], config['EMAIL_CONTACT'], config['EMAIL_HOST'], config['EMAIL_PORT'], config['EMAIL_LOGIN'], config['EMAIL_PASSWORD'])
    
    # remove past database entries
    remove_all_old()


if __name__ == "__main__":
    main()