from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
import sqlite3
from imdb import IMDb


# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure database
db = sqlite3.connect('movieme.db', check_same_thread=False)
dbcursor = db.cursor()

# Initialize database
with open('schema.sql') as f:
    db.executescript(f.read())

# Create an instance of the IMDb class
ia = IMDb()

lname = ""

@app.route("/")
@login_required
def index():
    """Shows the homepage"""

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide username!")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password!")
            return render_template("login.html")

        # Query database for username
        dbcursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = dbcursor.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            flash("Invalid username and/or password!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide username!")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password!")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            flash("Must provide password confirmation!")
            return render_template("register.html")

        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Password and confirmation must be equal!")
            return render_template("register.html")

        # Query database for username
        dbcursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = dbcursor.fetchall()

        # Ensure username doesn't exist
        if len(rows) != 0:
            flash("Username already exists!")
            return render_template("register.html")

        dbcursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                   (request.form.get("username"), generate_password_hash(request.form.get("password"))))
        db.commit()

        # Query database for username
        dbcursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        rows = dbcursor.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            flash("Invalid username and/or password!")
            return render_template("register.html")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/trending", methods=["GET", "POST"])
@login_required
def trending():
    """Shows trending shows"""

    M = ia.get_popular100_movies()
    M = M[0:20]

    if request.method == "POST":
        if not request.form.get("id"):
            return render_template("trending.html", movies = M)

        dbcursor.execute("SELECT * FROM fav WHERE userid = ? and movieid = ?", (session["user_id"], request.form.get("id"),))
        rows = dbcursor.fetchall()

        if len(rows) != 0:
            flash("Already added!")
            return render_template("trending.html", movies = M)

        dbcursor.execute("INSERT INTO fav (movieid, userid) VALUES (?, ?)",
                   (request.form.get("id"), session["user_id"],))
        db.commit()

        flash("Movie added!")
        return render_template("trending.html", movies = M)

    else:
        return render_template("trending.html", movies = M)


@app.route("/smovie", methods=["GET", "POST"])
@login_required
def smovie():
    """Searches for movies"""
    global lname

    if request.method == "POST":
        # no first search name
        if not request.form.get("name") and lname == "":
            flash("Must provide name!")
            return render_template("s.html")

        # first search name or nem search name
        if request.form.get("name"):
            lname = request.form.get("name")
            MOVIES = ia.search_movie(request.form.get("name"))
            return render_template("smovie.html", movies = MOVIES)

        # add movie to favorites and keep the search name
        if not request.form.get("name") and lname != "":
            MOVIES = ia.search_movie(lname)

            if not request.form.get("id"):
                return render_template("smovie.html", movies = MOVIES)

            dbcursor.execute("SELECT * FROM fav WHERE userid = ? and movieid = ?", (session["user_id"], request.form.get("id"),))
            rows = dbcursor.fetchall()

            if len(rows) != 0:
                flash("Already added!")
                return render_template("smovie.html", movies = MOVIES)

            dbcursor.execute("INSERT INTO fav (movieid, userid) VALUES (?, ?)",
                    (request.form.get("id"), session["user_id"],))
            db.commit()

            flash("Movie added!")
            return render_template("smovie.html", movies=MOVIES)

    else:
        lname = ""
        return render_template("s.html")


@app.route("/sactor", methods=["GET", "POST"])
@login_required
def sactor():
    """Searches for actors"""

    if request.method == "POST":
        if not request.form.get("name"):
            flash("Must provide name!")
            return render_template("s.html")

        ACTORS = ia.search_person(request.form.get("name"))
        return render_template("sactor.html", actors=ACTORS)

    else:
        return render_template("s.html")


@app.route("/favorites", methods=["GET", "POST"])
@login_required
def favorites():
    """ Shows favorite movies """

    dbcursor.execute("SELECT * FROM fav WHERE userid = ?", (session["user_id"],))
    rows = dbcursor.fetchall()

    if len(rows) == 0:
        flash("No favorites!")
        return redirect("/")

    MOVIES = []
    for id in rows:
        MOVIES.append(ia.get_movie(id[0]))
    
    if request.method == "POST":
        if not request.form.get("id"):
            return render_template("favorites.html", movies = MOVIES)

        # removes movie from db
        dbcursor.execute("DELETE FROM fav where userid = ? and movieid = ?", (session["user_id"], request.form.get("id"),))
        db.commit()

        # gets updated list of movies
        dbcursor.execute("SELECT * FROM fav WHERE userid = ?", (session["user_id"],))
        rows = dbcursor.fetchall()

        if len(rows) == 0:
            flash("No favorites!")
            return redirect("/")

        MOVIES = []
        for id in rows:
            MOVIES.append(ia.get_movie(id[0]))

        flash("Movie removed!")
        return render_template("favorites.html", movies = MOVIES)

    else:
        return render_template("favorites.html", movies=MOVIES)
