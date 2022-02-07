import os
import requests
import urllib.parse
import datetime

from dateutil.parser import parse
from functools import wraps
from flask import redirect, session 

# https://stackoverflow.com/questions/25341945/check-if-string-has-date-any-format
def is_date(string, fuzzy=True):
    """Check if the string has a date in it"""

    try:
        parse(string, fuzzy=fuzzy)
        return True
    
    except ValueError:
        return False

def dateformat(date):
    """Check if the string has a date of the particular format in it"""

    format = "%Y-%m-%d"
    try:
        datetime.datetime.strptime(date, format)
        return True
    except ValueError:
        return False

# https://stackoverflow.com/questions/19859282/check-if-a-string-contains-a-number
def has_digits(string):
    """Check if the string has digits"""
    return any(char.isdigit() for char in string)

def has_letters(string):
    """Check if the string has letters"""
    return any(char.isalpha() for char in string)

def login_required(f):

    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    https://stackoverflow.com/questions/739654/how-to-make-function-decorators-and-chain-them-together/1594484#1594484
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def lookup(movie):
    """Look up movie and its release date (only the movie name in the request)"""

    # Contact API:
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote_plus(movie)}&region=US"
        response = requests.get(url)
        response.text
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response:
    try:
        moviedata = response.json()
        return moviedata["results"][0]
        
    except (KeyError, TypeError, ValueError, IndexError):
        return None

def lookup1(movie):
    """Look up movie and its release date (for dynamic requests)"""

    # Contact API:
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote_plus(movie)}&region=US"
        response = requests.get(url)
        response.text
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response:
    try:
        moviedata = response.json()
        return moviedata["results"]
    except (KeyError, TypeError, ValueError):
        return None

def lookup2(movie, date):
    """Look up movie and its release date (both the name and the release date in the request)"""

    # Contact API:
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote_plus(movie)}&region=US"
        response = requests.get(url)
        response.text
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response:
    try:
        moviedata = response.json()
        for movie in moviedata["results"]:
            if movie["release_date"] == date:
                return movie

    except (KeyError, TypeError, ValueError):
        return None
