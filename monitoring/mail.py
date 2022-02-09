import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_email(cancellations, recipients, contact, host, port, login, password):
    # check for missing information
    failed = False
    if not login:
        logging.error("No login found for email client")
        failed = True
    if not password:
        logging.error("No password found for email client")
        failed = True
    if not recipients:
        logging.error("No recipients found for email")
        failed = True
    if not contact:
        logging.error("No sender (contact) found for email")
        failed = True
    if not cancellations:
        logging.info("No cancellations found")
        failed = True
    
    if failed:
        return
    
    # Craft email message
    msg = EmailMessage()
    message = "The following cancellations have occured:\n"
    max_tail_code = len(max(cancellations, key=lambda x: len(x['tail_code']))['tail_code'])+4
    for c in cancellations:
        message += f"{c['tail_code'].ljust(max_tail_code)}{c['start'].strftime('%a %b %d    %I:%M %p')} - {c['end'].strftime('%I:%M %p')}\n"
    message += f"\n\n\nIf you want to be removed from this service please contact {contact}"
    msg.set_content(message)

    # add required fields
    msg['Subject'] = 'Purdue Airport Reservation Tracker - Cancellations'
    msg['From'] = contact
    msg['To'] = ', '.join(recipients)

    # Send the message via configured SMTP server
    server = smtplib.SMTP_SSL(host, port)
    server.login(login, password)
    server.send_message(msg)
    server.quit()