from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/")
def main():
  return render_template("index.html")
  
  #export FLASK_APP=app.py in command line
  
  #<a href="{{ url_for('more') }}">See more...</a>
