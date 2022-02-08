import os
import datetime
import dateutil.relativedelta
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, redirect, render_template, request, session, flash
from flask import jsonify
from flask_session import Session
from flask_mail import Mail, Message
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy import select, insert, update
from sqlalchemy import and_
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import is_date, dateformat, lookup, lookup1, lookup2, has_digits, has_letters, login_required

# Configure application
app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

# Mail server configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)

# Function that is going to be performed every day
def test_job():
    with app.app_context():
        # Select all users
        n = 1 
        print ("loaded scheduler", n)
        n = n + 1
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
                    if datetime.datetime.strptime(movie["date"], "%Y-%m-%d").date() == date.today() + dateutil.relativedelta.relativedelta(days=4):
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
job = scheduler.add_job(test_job, trigger='cron', hour='21', minute='59')
scheduler.start()

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter?
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure sqlalchemy database
engine = create_engine('sqlite:///movies.db')

# And tables
metadata = MetaData(bind=engine)
users = Table('users', metadata, autoload = True)
movies = Table('movies', metadata, autoload = True)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show a table of movies"""

    # Get all the movies for that user to put them in a table.
    us_stmt = (select(users).where(users.c.id == session["user_id"]))
    with engine.connect() as conn:
        rows = conn.execute(us_stmt).mappings().all()
    mov_stmt = (select(movies).where(movies.c.user_id == session["user_id"]))
    with engine.connect() as conn:
        rows_m = conn.execute(mov_stmt).mappings().all()
    return render_template("index.html", rows_m=rows_m, rows=rows)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add movie"""

    # Check if any inputs are blank
    if not request.form.get("movie-choice"):
        flash("Please, enter the name of the movie.")
        return redirect("/")

    # Check if there is a space. 
    if len(request.form.get("movie-choice").rsplit(' ', 1)) == 2:
        # Check if there is a date ("or" is there to fix a bug that accured when movies had numbers, "is_date" didn't see the date then, so 
        # I  had to add "or" to check for a movie that has a date in it's name and a date of the release on the right)
        # Check that what is left on the right side after the space is a date in particular format
        if (is_date(request.form.get("movie-choice")) or is_date(request.form.get("movie-choice").rsplit(' ', 1)[1]))\
        and dateformat(request.form.get("movie-choice").rsplit(' ', 1)[1]):         
            # If all conditions are true, the user used the datalist (name + date). Split the name and the date
            # and use lookup.
            moviechoice = request.form.get("movie-choice").rsplit(' ', 1) 
            moviedb = lookup2(moviechoice[0], moviechoice[1])
        else:
            # If there's a date and a space, but after separation it's not the date of our particular format
            # that means the user manually typed the name of the movie that had a date and a space in it.
            # Like "23rd August 2008", so just lookup the name. 
            moviedb = lookup(request.form.get("movie-choice"))
    else:
        # If there is no date in the field, the user used manual input, so we just lookup the name of the movie.
        # If there was a date, but no space, the user typed the name of the movie that was itself a date
        # Like "11/11/11", so just lookup the name.
        moviedb = lookup(request.form.get("movie-choice"))     
    # Check that lookup2 or lookup didn't return None. If not, add movie to the database.
    try:
        moviedb["id"]
    except TypeError:
        # Otherwise, the movie doesn't exist
        flash("This movie doesn't exist in this version of reality.")
        return redirect("/")
    # Check if the movie has already been released (or being released today)
    if datetime.datetime.strptime(moviedb["release_date"], "%Y-%m-%d").date() < date.today():
        flash("This movie has already been released.")
        return redirect("/")
    elif datetime.datetime.strptime(moviedb["release_date"], "%Y-%m-%d").date() == date.today():
        flash("This movie is being released today.")
        return redirect("/")
    # Check if the movie is already in the list
    dbl_stmt = (select(movies)).where(and_(movies.c.user_id == session["user_id"], movies.c.movie_id == moviedb["id"]))
    with engine.connect() as conn:
        check = conn.execute(dbl_stmt).first()
    if check: 
        flash("This movie is already in your list.")
        return redirect("/")
    # Otherwise, add it to the list
    else:
        mov_stmt = (insert(movies).values(user_id=session["user_id"], title=moviedb["title"], date=moviedb["release_date"], movie_id=moviedb["id"]))
        with engine.connect() as conn:
            conn.execute(mov_stmt)
        return redirect("/")

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """Delete movie"""

    # Delete the movie fromthe db.
    del_stmt = (movies.delete().where(movies.c.id == request.form.get("delete")))
    with engine.connect() as conn:
        conn.execute(del_stmt)
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in user"""

    # Forget any user id
    session.clear()

    # User reached via POST.
    if request.method == "POST":

        # Check if any inputs are blank
        if not request.form.get("username") or not request.form.get("password"):
            flash("Please, fill in all the required fields.")
            return render_template("login.html")

        # Check password and username
        pas_stmt = (select(users).where(users.c.username == request.form.get("username").lower()))
        with engine.connect() as conn:
            user_pas = conn.execute(pas_stmt).all()
            if len(user_pas) != 1:
                flash("The user with this username doesn't exist.")
                return render_template("login.html")
            user_pas = conn.execute(pas_stmt)
            if not check_password_hash(user_pas.first().hash, request.form.get("password")):
                flash("Wrong password.")
                return render_template("login.html")

        # Start session for this user:
        id_stmt = (select(users).where(users.c.username == request.form.get("username").lower())) 
        with engine.connect() as conn:
            user_id = conn.execute(id_stmt)
            session["user_id"] = user_id.first().id
            return redirect("/")
    # If it's not "post", then render template
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user id
    session.clear()
    
    # Redirect user to login
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # If that was a "post" request
    if request.method == "POST":

        # Check if any inputs are blank or if passwords do not match.
        if not request.form.get("username") or not request.form.get("e-mail") or not request.form.get("password")\
        or not request.form.get("confirmation"):
            flash("Please, fill in all the required fields.")
            return render_template("register.html")
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("The passwords do not match.")
            return render_template("register.html")

        # Check is the password is at least 8 symbols long and has both digits and letters. Flash warning message, if not.
        if not has_digits(request.form.get("password")) or not has_letters(request.form.get("password")):
            flash("The password must contain letterns and numbers.")
            return render_template("register.html")
        if len(request.form.get("password")) < 8:
            flash("The password must be at least 8 characters long.")
            return render_template("register.html")

        # Flash "username already exists", if it already exists
        exist_stmt = (select(users).where(users.c.username == request.form.get("username").lower()))
        with engine.connect() as conn:
            exist = conn.execute(exist_stmt).first()
        if exist:
            flash("The user with this username already exists.")
            return render_template("register.html")
        
        # Flash "The user with this e-mail already exists", if this e-mail is already in the db.
        email_stmt = (select(users).where(users.c.e_mail == request.form.get("e-mail").lower()))
        with engine.connect() as conn:
            email = conn.execute(email_stmt).first()
        if email:
            flash("The user with this e-mail already exists.")
            return render_template("register.html")
        
        # Create a hash for the password
        hash = generate_password_hash(request.form.get("password"))

        # Insert username, e-mail and hash into the database
        hash_stmt = (insert(users).values(username=request.form.get("username").lower(), hash=hash, e_mail=request.form.get("e-mail").lower()))
        with engine.connect() as conn:
            conn.execute(hash_stmt)
        
        # Start session for this user (take his id from the database)
        id_stmt = (select(users).where(users.c.username == request.form.get("username").lower()))
        with engine.connect() as conn:
            user_id = conn.execute(id_stmt)
            session["user_id"] = user_id.first().id
            return redirect("/")
    else:
        # If not "post", render temlate.
        return render_template("register.html")

@app.route("/search")
def search():
    """Search for the movie in a database via API requests"""

    moviedb = lookup1(request.args.get("q"))
    return jsonify(moviedb)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Change notification settings"""

    # If that was a "post" request
    if request.method == "POST":

        # Check if the number of days is a positive integer
        days = -1
        # If the user entered something in the "other" field
        if request.form.get("other"):
            # If what he entered, countains not only digits, flash a warning
            if not request.form.get("other").isdigit():
                flash("Wrong format. Please, enter the number of days.")
                return redirect("/settings")
            # Else, set the variable "days" equal to the number he entered.
            else :
                days = int(request.form.get("other"))
        # If the checkbox "month" is checked or if there was "30" in the "other" field, 
        # set "month" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("month") or days == 30:
            mon_stmt = (update(users).where(users.c.id == session["user_id"]).values(month=1))
        else:
            mon_stmt = (update(users).where(users.c.id == session["user_id"]).values(month=0))
        # If the checkbox "week" is checked or if there was "7" in the "other" field, 
        # set "week" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("week") or days == 7:
            week_stmt = (update(users).where(users.c.id == session["user_id"]).values(week=1))
        else:
            week_stmt = (update(users).where(users.c.id == session["user_id"]).values(week=0))
        # If the checkbox "day_1" is checked or if there was "1" in the "other" field, 
        # set "day_1" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("day_1") or days == 1:
            day_1_stmt = (update(users).where(users.c.id == session["user_id"]).values(day_1=1))
        else:
            day_1_stmt = (update(users).where(users.c.id == session["user_id"]).values(day_1=0))
        # If the checkbox "day_0" is checked, set "day_0" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("day_0") or days == 0:
            day_0_stmt = (update(users).where(users.c.id == session["user_id"]).values(day_0=1))
        else:
            day_0_stmt = (update(users).where(users.c.id == session["user_id"]).values(day_0=0))
        # If there was a value in the "other" field and it was not 30, 7, 1 or 0, set "other" in the db to that value.    
        if request.form.get("other") and request.form.get("ch_other") and not days in {30, 7, 1, 0}:
            oth_stmt = (update(users).where(users.c.id == session["user_id"]).values(other=request.form.get("other")))
            with engine.connect() as conn:
                conn.execute(oth_stmt)
        # If there was a value in the "other" field and it WAS 30, 7, 1 or 0, set "other" to 0 (cause we already used one of the true-false above).
        if request.form.get("other") and request.form.get("ch_other") and days in {30, 7, 1, 0}:
            oth_stmt = (update(users).where(users.c.id == session["user_id"]).values(other=0))
            with engine.connect() as conn:
                conn.execute(oth_stmt)
        # If there is no input in checkbox "ch_other", set "other" in db to 0.
        if not request.form.get("ch_other"):
            nooth_stmt = (update(users).where(users.c.id == session["user_id"]).values(other=0))
            with engine.connect() as conn:
                conn.execute(nooth_stmt)
        with engine.connect() as conn:
            conn.execute(mon_stmt)
            conn.execute(week_stmt)
            conn.execute(day_1_stmt)
            conn.execute(day_0_stmt)
            
        return redirect("/settings")
    
    # Else simply show settings
    else:

        set_stmt = (select(users).where(users.c.id == session["user_id"]))
        with engine.connect() as conn:
            rows = conn.execute(set_stmt).mappings().all()

        return render_template("settings.html", rows=rows)

@app.route("/support")
@login_required
def support():
    """Show the support page"""

    return render_template("support.html")

if __name__ == "__main__":
        app.run(debug=True, use_reloader=False)