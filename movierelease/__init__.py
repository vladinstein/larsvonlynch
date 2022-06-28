from flask import Flask
app = Flask(__name__)

from movierelease import views

if __name__ == "__main__":
        app.run(debug=False)