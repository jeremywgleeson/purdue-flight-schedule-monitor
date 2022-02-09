FROM python:3
LABEL maintainer="jgleeson@purdue.edu"

ENV EMAIL_CONTACT=$EMAIL_CONTACT
ENV EMAIL_HOST=$EMAIL_HOST
ENV EMAIL_PORT=$EMAIL_PORT
ENV EMAIL_LOGIN=$EMAIL_LOGIN
ENV EMAIL_PASSWORD=$EMAIL_PASSWORD
ENV TARGET_EMAIL=$TARGET_EMAIL

RUN useradd -ms /bin/bash flight-monitor \
    && apt-get update \
    && apt-get install -y cron tzdata \
    && chmod u+s $(which cron)

# static time zone
ENV TZ="America/New_York"

WORKDIR /home/flight-monitor
COPY . .
RUN /usr/bin/crontab -u flight-monitor flight-monitor-crontab
RUN pip install -r requirements.txt
USER flight-monitor
CMD printenv | sed 's/^\(.*\)$/export \1/g' > .env; chmod+x .env; cron -f