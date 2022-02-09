# Purdue Flight Schedule Monitor
Purdue Flight Schedule Monitor is a python monitoring script that checks the [Purdue airport flight schedule website](https://lai.kal-soft.com/) for reservation cancellations, and emails you about them.

## Usage
The script can be run by itself, or you can use the provided docker image to deploy the script as a service on your favourite cloud. (See [Deployment](#deployment))

To run independently:
1. Clone repository
2. Optionally create an environment
2. `pip install -r requirements.txt`
3. `python main.py`

Running the script to check for changes has no advantage to just checking the website yourself (unless run at regular intervals). To learn why, read [About the code](#about-the-code)

To build a custom docker image, make modifications then:  
`docker build -t flight-monitor .`

## Deployment
To deploy the docker image, use the image on your favourite cloud:  
[Image on Dockerhub]()  
This image requires secrets passed as environmental variables in order to work correctly.

If you prefer to build a custom image with secrets and config baked in, please do so.

### Environment variables
Required configs/secrets:
```
# EMAIL_CONTACT Is the service owner's email
EMAIL_CONTACT
# EMAIL_HOST Is the service sender email SMTP host (ex: smtp.gmail.com)
EMAIL_HOST
# EMAIL_HOST Is the service sender email STMP port (ex: 465)
EMAIL_PORT
# EMAIL_LOGIN Is the service sender email STMP login (ex: xxxx@gmail.com)
EMAIL_LOGIN
# EMAIL_PASSWORD Is the service sender email STMP password (ex: ********)
EMAIL_PASSWORD
# EMAIL_PASSWORD Is the receiving email the service should send notifications to (ex: xxxx@gmail.com)
TARGET_EMAIL
```

## Configuration
You can overwrite any of the configuration variables by changing the `config.yaml` and re-building the image. To overwrite simple variables, you may declare any config variables as environmental variables and set them in the `Dockerfile`, then re-build the image.  
To learn more about configuration options, see [`config.yaml`](config.yaml)

## About the code
On the first run, the python application will scrape all reservations in the given time window and store them in an SQLAlchemy database that includes ORM for `Schedule` and `Reservation` classes.  
Every subsequent run, the python application will scrape all reservations in the given time window and check for differences against the database. It will email deletions to the target email, then update the database to contain the current schedules.  
Finally, the app removes all schedules and reservations from all previous days. 