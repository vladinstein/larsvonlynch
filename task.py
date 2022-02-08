import os
import dateutil.relativedelta
import datetime
from datetime import date
from flask import render_template
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy import select, update
from sqlalchemy import and_
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from application import app

# Mail server configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)

# Configure sqlalchemy database
engine = create_engine('sqlite:///movies.db')

# And tables
metadata = MetaData(bind=engine)
users = Table('users', metadata, autoload = True)
movies = Table('movies', metadata, autoload = True)

# Function that is going to be performed every day
def test_job():
    with app.app_context():
        # Select all users
        allus_stmt = (select(users))
        with engine.connect() as conn:
            all_users = conn.execute(allus_stmt).mappings().all()
        # Go through all users one-by-one
        for one_user in all_users:
            # Select all movies for that user
            usmov_stmt = (select(movies).where(movies.c.user_id == one_user["id"]))
            with engine.connect() as conn:
                us_mov = conn.execute(usmov_stmt).mappings().all()
            # Go through all movies one-by-one
            for movie in us_mov:
                interval = 0
                # Depending on the user's setting, send a message (30 days, week, 1 day or particular number of days before the release
                # or on the day of the release)
                # Check the setting, then check the date then set "interval" to 30, 7 or 1.
                if one_user["month"]:
                    if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=30):
                        interval = 30
                if one_user["week"]:
                    if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=3):
                        interval = 7
                if one_user["other"]:
                    if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=one_user["other"]):
                        interval = one_user["other"]
                # If interval is not 0, send the message with a particular interval. 
                if interval:
                    msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user["e_mail"])])
                    msg.html = render_template("mail.html", username=one_user["username"] , movie=movie["title"] , interval=interval, date=movie["date"])
                    mail.send(msg)
                # Check the setting for 1 day (tomorrow), check the date, send the message if needed.
                if one_user["day_1"]:
                    if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=1):
                        interval = 1
                        msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user["e_mail"])])
                        msg.html = render_template("mail.html", username=one_user["username"] , movie=movie["title"] , interval=interval, date=movie["date"])
                        mail.send(msg)
                # Check the setting "on the day of the release", check the date, send the message if needed.
                if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today():
                    rel_stmt = (update(movies).where(and_(movies.c.user_id == one_user["id"], movies.c.movie_id == movie["movie_id"])).values(released=1))
                    with engine.connect() as conn:
                        conn.execute(rel_stmt)
                    if one_user["day_0"]:
                        msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user["e_mail"])])
                        msg.html = render_template("mail.html", username=one_user["username"] , movie=movie["title"] , interval=interval, date=movie["date"])
                        mail.send(msg)
        return

# This is going to perform the task above at the same intervals (every day, but can be a different interval)
scheduler = BackgroundScheduler()
job = scheduler.add_job(test_job, trigger='cron', hour='3', minute='22')
scheduler.start()