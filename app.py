from flask import Flask, render_template, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = "your_secure_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///codenest.db"
db = SQLAlchemy(app)

# User database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    progress = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

# Home page route
@app.route("/")
def home():
    return render_template("home.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and bcrypt.checkpw(request.form["password"].encode('utf-8'), user.password):
            session["user"] = user.username
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for('home'))


# Registration route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed_pw = bcrypt.hashpw(request.form["password"].encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=request.form["username"],
                        email=request.form["email"],
                        password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html", username=session["user"])
    return redirect("/login")

# Lessons overview route
@app.route("/lessons")
def lessons():
    if "user" in session:
        lesson_list = ["HTML Basics", "CSS Fundamentals", "JavaScript Essentials", "Python Beginner", "Flask Framework"]
        return render_template("lessons.html", lessons=lesson_list)
    return redirect("/login")

# Analytics Dashboard route (built-in analytics)
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/login")

    users = User.query.all()
    usernames = [user.username for user in users]
    progresses = [user.progress for user in users]

    plt.figure(figsize=(10,5))
    plt.bar(usernames, progresses, color="#A78BFA")
    plt.xlabel('Users')
    plt.ylabel('Progress (%)')
    plt.title('User Progress Analytics')

    img_path = os.path.join("static", "progress.png")
    plt.savefig(img_path)
    plt.close()

    return render_template("analytics.html", image=url_for('static', filename='progress.png'))

# Admin route for user management
@app.route("/admin")
def admin():
    if "user" in session:
        users = User.query.all()
        return render_template("admin.html", users=users)
    return redirect("/login")

# Running your app
if __name__ == "__main__":
    app.run(debug=True)
