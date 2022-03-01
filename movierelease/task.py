# Function that is going to be performed every day
import datetime
from movierelease import app
import dateutil.relativedelta
from datetime import date
from movierelease.views import Users, Movies, mail, db
from flask import render_template
from flask_mail import Message

with app.app_context():
# Select all users
    all_users = Users.query.all()
    # Go through all users one-by-one
    for one_user in all_users:
        # Select all movies for that user
        us_mov = Movies.query.filter_by(user_id=one_user.id).all()
        # Go through all movies one-by-one
        for movie in us_mov:
            interval = 0
            # Depending on the user's setting, send a message (30 days, week, 1 day or particular number of days before the release
            # or on the day of the release)
            # Check the setting, then check the date then set "interval" to 30, 7 or 1.
            if one_user.month:
                if datetime.datetime.strptime(movie.date, "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=30):
                    interval = 30
            if one_user.week:
                if datetime.datetime.strptime(movie.date, "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=7):
                    interval = 7
            if one_user.other:
                if datetime.datetime.strptime(movie.date, "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=one_user.other):
                    interval = one_user.other
            # If interval is not 0, send the message with a particular interval. 
            if interval:
                msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user.e_mail)])
                msg.html = render_template("mail.html", username=one_user.username, movie=movie.title, interval=interval, date=movie.date)
                mail.send(msg)
            # Check the setting for 1 day (tomorrow), check the date, send the message if needed.
            if one_user.day_1:
                if datetime.datetime.strptime(movie.date, "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=1):
                    interval = 1
                    msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user.e_mail)])
                    msg.html = render_template("mail.html", username=one_user.username, movie=movie.title, interval=interval, date=movie.date)
                    mail.send(msg)
            # Check the setting "on the day of the release", check the date, send the message if needed.
            if datetime.datetime.strptime(movie.date, "%Y-%m-%d").date() == date.today():
                mov_rel = Movies.query.filter_by(user_id=one_user.id, movie_id=movie.movie_id).first()
                mov_rel.released = 1
                db.session.commit()
                if one_user.day_0:
                    msg = Message("Lars Von Lynch", sender = "vladinstein@gmail.com", recipients = ["{}".format(one_user.e_mail)])
                    msg.html = render_template("mail.html", username=one_user.username, movie=movie.title, interval=interval, date=movie.date)
                    mail.send(msg)

