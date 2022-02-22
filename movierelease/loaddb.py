from movierelease import app
from movierelease.views import db
with app.app_context():
    db.create_all()