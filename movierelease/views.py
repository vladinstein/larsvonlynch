from movierelease import app
import os
import datetime
from datetime import date
from flask import redirect, render_template, request, session, flash
from flask import jsonify
from flask_session import Session
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, insert, update
from sqlalchemy import and_
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError

from movierelease.helpers import is_date, dateformat, lookup, lookup1, lookup2, has_digits, has_letters, login_required

# Configure application

app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
# Fixing bug https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
if app.config["SQLALCHEMY_DATABASE_URI"] and app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
db = SQLAlchemy(app)

class Users(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True, nullable=False)
	hash = db.Column(db.String(255), nullable=False)
	e_mail = db.Column(db.String(255), unique=True, nullable=False)
	month = db.Column(db.Integer, default=1)
	week = db.Column(db.Integer, default=1)
	day_1 = db.Column(db.Integer, default=1)
	day_0 = db.Column(db.Integer, default=1)
	other = db.Column(db.Integer, default=0)

	def __repr__(self):
		return '<User %r>' % self.username

class Movies(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(255), nullable=False)
	date = db.Column(db.String(255), nullable=False)
	movie_id = db.Column(db.Integer, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
	released = db.Column(db.Integer, default=0) 

	def __repr__(self):
		return '<User %r>' % self.username

# Mail server configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)

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

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show a table of movies"""

    # Get user name to pass it to layout template to say hello.
    row = Users.query.filter_by(id=session["user_id"]).first()
    # Get all the movies for that user to put them in a table.
    rows_m = Movies.query.filter_by(user_id=session["user_id"]).all()
    return render_template("index.html", rows_m=rows_m, row=row)

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
    check = Movies.query.filter_by(user_id=session["user_id"], movie_id=moviedb["id"]).first()
    if check:
        flash("This movie is already in your list.")
        return redirect("/")

    # Otherwise, add it to the list
    else:
        mov = Movies(user_id=session["user_id"], title=moviedb["title"], date=moviedb["release_date"], movie_id=moviedb["id"])
        db.session.add(mov)
        db.session.commit()
        return redirect("/")

@app.route("/data")
@login_required
def data():
    """Show the support page"""

    # Get user name to pass it to layout template to say hello.
    row = Users.query.filter_by(id=session["user_id"]).first()
    return render_template("data.html", row=row)

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """Delete movie"""

    #Delete the movie from the db.
    Movies.query.filter_by(id=request.form.get("delete")).delete()
    db.session.commit()
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
        user_pas = Users.query.filter_by(username=request.form.get("username").lower()).all()
        if len(user_pas) != 1:
            flash("The user with this username doesn't exist.")
            return render_template("login.html")
        user_pas = Users.query.filter_by(username=request.form.get("username").lower()).first()
        if not check_password_hash(user_pas.hash, request.form.get("password")):
            flash("Wrong password.")
            return render_template("login.html")

        # Start session for this user:
        user_id = Users.query.filter_by(username=request.form.get("username").lower()).first()
        session["user_id"] = user_id.id
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
        exist = Users.query.filter_by(username=request.form.get("username").lower()).first()
        if exist:
            flash("The user with this username already exists.")
            return render_template("register.html")

        # Check if the e-mail is valid. 
        # https://stackoverflow.com/questions/8022530/how-to-check-for-valid-email-address/28982264#28982264
        try:
            valid = validate_email(request.form.get("e-mail").lower())
            email = valid.email
        except EmailNotValidError:
            flash("The e-mail is not valid.")
            return render_template("register.html")


        # Flash "The user with this e-mail already exists", if this e-mail is already in the db.
        email = Users.query.filter_by(e_mail=request.form.get("e-mail").lower()).first()
        if email:
            flash("The user with this e-mail already exists.")
            return render_template("register.html")

        # Create a hash for the password
        hash = generate_password_hash(request.form.get("password"))

        # Insert username, e-mail and hash into the database
        reg_us = Users(username=request.form.get("username").lower(), hash=hash, e_mail=request.form.get("e-mail").lower())
        db.session.add(reg_us)
        db.session.commit()

        # Start session for this user (take his id from the database)
        this_user = Users.query.filter_by(username=request.form.get("username").lower()).first()
        session["user_id"] = this_user.id
        return redirect("/")
        
    else:
        # If not "post", render template.
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
        update = Users.query.filter_by(id=session["user_id"]).first()
        if request.form.get("month") or days == 30:    
            update.month = 1
        else:
            update.month = 0  
        # If the checkbox "week" is checked or if there was "7" in the "other" field, 
        # set "week" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("week") or days == 7:
            update.week = 1
        else:
            update.week = 0
        # If the checkbox "day_1" is checked or if there was "1" in the "other" field, 
        # set "day_1" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("day_1") or days == 1:
            update.day_1 = 1
        else:
            update.day_1 = 0
        # If the checkbox "day_0" is checked, set "day_0" in the db to "true(1)", otherwise to "false(0)".
        if request.form.get("day_0") or days == 0:
            update.day_0 = 1
        else:
            update.day_0 = 0
        # If there was a value in the "other" field and it was not 30, 7, 1 or 0, set "other" in the db to that value.    
        if request.form.get("other") and request.form.get("ch_other") and not days in {30, 7, 1, 0}:
            update.other = request.form.get("other")
        # If there was a value in the "other" field and it WAS 30, 7, 1 or 0, set "other" to 0 (cause we already used one of the true-false above).
        if request.form.get("other") and request.form.get("ch_other") and days in {30, 7, 1, 0}:
            update.other = 0
        # If there is no input in checkbox "ch_other", set "other" in db to 0.
        if not request.form.get("ch_other"):
            update.other = 0
        db.session.commit()  
            
        return redirect("/settings")
    
    # Else simply show settings
    else:
        # Get user info to show his settings and to greet him.
        row = Users.query.filter_by(id=session["user_id"]).first()
        return render_template("settings.html", row=row)

@app.route("/support")
@login_required
def support():
    """Show the support page"""

    # Get user name to pass it to layout template to say hello.
    row = Users.query.filter_by(id=session["user_id"]).first()
    return render_template("support.html", row=row)
