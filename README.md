# Lars Von Lynch
This application notifies its users about the upcoming movie releases. Each user creates a list of movies that he wants to follow (movies, that hasn't been released yet) and then gets notified by e-mail before each of the movies gets released (or on the day of the release). The users can adjust when exactly they want to be notified (30 days/7 days/1 day/any other number of days before the release or/and on the day of the release).

## How it works
* The user adds a movie to his list.
* By default every user is going to be notified 30 days, 7 days, 1 day before the release as well as on the day of the release. This can be changed by going to the settings page and checking/unchecking the boxes. It is possible to also add one custom notification (any number of days before the release).
* Every day at 8 AM UTC the app performs a pediodical task to check if it needs to notify any of the users about any of the upcoming releases. If it does, it sends an e-mail to the user saying which movie is going to be released, how many days are left until the release and specifying the date of the release. 

## Files

### Root directory:

1. **setup.py** indicates that there is a python package
2. **task.py** is a file with a periodic task. We run this task using Heroku Scheduler every day at 8 AM UTC. (Originally, APScheduler was used, but it's problematic to use it with free Heroku Account). This task checks if it needs to send any notifications and then sends them via e-mail if needed. 
3. **loaddb.py** is used to create tables in Postgres database on Heroku from classes described in views.py file.
4. **.gitignore** indicates what files should be ignored by git. **requerements.txt** contains all the libraries used in the project. **Procfile** specifies the commands that are executed by the app on startup. 

### App directory (movierelease/movierelease)
1. **views.py** is the main file of the application. It specifies all the routes used in the application: *index ("/")*, *add*, *delete*, *login*, *logout*, *register*, *search*, *settings*, *support*. 
    * *index* route shows the table with the movies that this user has added to his list; 
    * *add* and *delete* routes add and delete movies from the database/user's list respectively; 
    * *login*, *logout* and *register* are used to take care of each users registration and the session;
    * *search* sends dynamic API requests to a movie database "**themoviedb.org**" and returns a jsonify object so that the user can see a dynamic drop-down list of the movies with names similar to what he's typing (or what he copied and pasted);
    * in the *settings*, the user can adjust notification settings (when he wants to recieve e-mails);
    * *support* route describes how to use the app.
2. **helpers.py** contains functions used in the application. 
3. **\_\_init\_\_.py** is where the Flask application object is created. We also run the application in this file.

### Templates

1. Most of the templates are used in the respective routes (with addition of **layout.html**): 
    * **index.html**
    * **login.html**
    * **register.html**
    * **settings.html**
    * **support.html**
2. **mail.html** is used in the notification e-mails.

### Static 

1. **styles.css** self-explanatory
2. **lynch.jpg** is a picture used in the e-mails.

### Notes

1. The database management system used is PostgreSQL. I was useing SQLite at first, but it was impossible to use it with the free Heroku account. Another thing I had to change was the library used to interact with the database. At first I was using SQLAlchemy Core (with "engine" object and by creating tables manually without using classes for the tables). In order to work with Heroku I needed to create classes for the tables and Flask-SQLAlchemy seemed like a best and simplest solution for that. 

2. To get the movies info (release dates in particular) the app sends API requests to **themoviedb.org**. Functions *"lookup"* and *"lookup2"* in **helpers.py** are used for that purpose (depending on if the user typed the name of the movie and pressed enter or selected it from the drop-down list).  

3. Flask-Mail is used to send e-mails. 