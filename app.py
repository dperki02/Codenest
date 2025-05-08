from flask import Flask, render_template, redirect, request, session, url_for
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg BEFORE importing pyplot
import matplotlib.pyplot as plt
import os
import mysql.connector

app = Flask(__name__)
app.secret_key = os.urandom(24)

db_config = {
    'host': 'database-ums.c7ksas0oekmx.us-east-2.rds.amazonaws.com',
    'user': 'admin',
    'password': 'password123',
    'database': 'userdb'
}
# Home page route
@app.route("/")
def home():
    return render_template("home.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session["user"] = user["username"]
                return redirect(url_for('dashboard'))
            else:
                return render_template("login.html", error="Invalid username. Please try again.")
        
        except mysql.connector.Error as err:
            return render_template("login.html", error=f"Database error: {err}")

    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for('home'))


# Registration route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        # Handle Form Submission Implement DB insert logic here
        username = request.form['username']
        password = request.form['password'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            insert_query = """
            INSERT INTO users (username, password, first_name, last_name, email)
            VALUES (%s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query, (username, password, first_name, last_name, email))
            conn.commit()

            cursor.close()
            conn.close()
  
            return render_template('success.html')
        except mysql.connector.Error as err:
            return render_template('register.html', error=f"Database Error: {err}")
    
    return render_template('register.html')

@app.route('/users', methods=['GET'])
def users():
    query = request.args.get('q', '')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        if query:
            sql = """
                SELECT * FROM users 
                WHERE username LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR email LIKE %s
            """
            like_query = f"%{query}%"
            cursor.execute(sql, (like_query, like_query, like_query, like_query))
        else:
            cursor.execute("SELECT * FROM users")

        users = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('admin.html', users=users)

    except mysql.connector.Error as err:
        return f"Error: {err}"
    
# Admin Dashboard
@app.route("/admin_dashboard")
def admin_dashboard():
    if "user" in session:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()

            cursor.close()
            conn.close()

            return render_template("adminprogress.html", users=users)

        except mysql.connector.Error as err:
            return f"Database Error: {err}"
    
    return redirect("/login")


# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, first_name, last_name FROM users WHERE username=%s", (session["user"],))
    user = cursor.fetchone()
    username = f"{user['first_name']} {user['last_name']}"

    cursor.execute("SELECT * FROM user_classes WHERE user_id=%s", (user['id'],))
    workshops = cursor.fetchall()

    class_names = [w['class_name'] for w in workshops]
    progress_values = [w['progress_percent'] for w in workshops]

    plt.figure(figsize=(8, 4))
    bars = plt.bar(class_names, progress_values, color="#5A9")
    plt.ylabel('Progress %')
    plt.title('Overall Progress')
    plt.ylim(0, 120)

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval}%', ha='center')

    progress_chart_path = os.path.join(app.static_folder, "progress_chart.png")
    plt.savefig(progress_chart_path, bbox_inches='tight')
    plt.close()

    chart_url = url_for('static', filename='progress_chart.png')

    cursor.close()
    conn.close()


    return render_template("dashboard.html",
                               username=username,
                               workshops=workshops,
                               progress_chart=chart_url)

@app.route('/workshop/<int:user_class_id>', defaults={'lesson_id': None})
@app.route('/workshop/<int:user_class_id>/<int:lesson_id>')
def workshop_detail(user_class_id, lesson_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Get workshop (user_class) details by id
    cursor.execute("SELECT * FROM user_classes WHERE class_id=%s", (user_class_id,))
    workshop = cursor.fetchone()

    if not workshop:
        cursor.close()
        conn.close()
        return "Workshop not found", 404

    # Fetch lessons based on matching class_name (not class_id)
    cursor.execute("SELECT * FROM lessons WHERE class_id IN "
                   "(SELECT class_id FROM user_classes WHERE class_name=%s)", (workshop['class_name'],))
    lessons = cursor.fetchall()

    selected_lesson = None
    quizzes = []

    if lessons:
        # Choose the specific lesson if provided, else default to first lesson
        if lesson_id:
            selected_lesson = next((lesson for lesson in lessons if lesson['id'] == lesson_id), lessons[0])
        else:
            selected_lesson = lessons[0]

        cursor.execute("SELECT * FROM quizzes WHERE lesson_id=%s", (selected_lesson['id'],))
        quizzes = cursor.fetchall()

     # Fallback video URL if missing or incorrect
    fallback_video_url = "https://www.youtube.com/embed/qz0aGYrrlhU"  # generic video for demo

    if selected_lesson and (not selected_lesson.get('video_url') or "youtube" not in selected_lesson.get('video_url')):
        selected_lesson['video_url'] = fallback_video_url
   

    cursor.close()
    conn.close()

    return render_template("workshop_detail.html",
                           workshop=workshop,
                           lessons=lessons,
                           selected_lesson=selected_lesson,
                           quizzes=quizzes)


# Lessons overview route
@app.route('/lessons')
def lessons():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Classes")
        classes = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('lessons.html', classes=classes)
    except mysql.connector.Error as err:
        return f"Database Error: {err}"

@app.route("/quiz/<int:lesson_id>", methods=['GET', 'POST'])
def quiz_page(lesson_id):
    # FIXED DEMO lesson_id for simplicity
    demo_lesson_id = 1

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Fetch the fixed demo lesson
    cursor.execute("SELECT * FROM lessons WHERE id = %s", (demo_lesson_id,))
    lesson = cursor.fetchone()

    # Fetch fixed demo quiz questions
    cursor.execute("SELECT * FROM quiz_questions WHERE lesson_id = %s", (demo_lesson_id,))
    questions = cursor.fetchall()

    if request.method == 'POST':
        user_id = session.get("user_id", 1)  # demo user_id if not set
        for question in questions:
            qid = question["question_id"]
            correct_answer = question["correct_option"]
            user_answer = request.form.get(f"question_{qid}")

            cursor.execute(
                "INSERT INTO user_quiz_results (user_id, quiz_id, user_answer, is_correct) VALUES (%s, %s, %s, %s)",
                (user_id, qid, user_answer, user_answer == correct_answer)
            )
        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('quiz_result', lesson_id=demo_lesson_id))

    cursor.close()
    connection.close()

    return render_template("quiz.html", lesson=lesson, questions=questions)


@app.route("/quiz_result/<int:lesson_id>")
def quiz_result(lesson_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    user_id = session.get("user_id", 1)  # demo user_id if not set

    cursor.execute("""
        SELECT qz.question, qz.answer AS correct_option, uqr.user_answer, uqr.is_correct
        FROM quizzes qz
        JOIN user_quiz_results uqr ON qz.id = uqr.quiz_id
        WHERE uqr.user_id = %s
        ORDER BY uqr.completed_at DESC LIMIT 10
    """, (user_id,))

    results = cursor.fetchall()
    cursor.close()
    connection.close()

    score = sum(1 for result in results if result['is_correct'])
    total = len(results)

    return render_template("quiz_result.html", results=results, score=score, total=total)



# Analytics Dashboard route (built-in analytics)
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/login")

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Fetch users and their average progress
        cursor.execute("""
            SELECT u.username, AVG(uw.progress_percent) as avg_progress
            FROM users u
            JOIN user_workshops uw ON u.id = uw.user_id
            GROUP BY u.username
        """)
        
        user_data = cursor.fetchall()
        cursor.close()
        conn.close()

        usernames = [user['username'] for user in user_data]
        progresses = [user['avg_progress'] for user in user_data]

        plt.figure(figsize=(10,5))
        plt.bar(usernames, progresses, color="#A78BFA")
        plt.xlabel('Users')
        plt.ylabel('Average Progress (%)')
        plt.title('User Progress Analytics')

        img_path = os.path.join("static", "progress.png")
        plt.savefig(img_path)
        plt.close()

        return render_template("analytics.html", image=url_for('static', filename='progress.png'))

    except mysql.connector.Error as err:
        return f"Database error: {err}"


# Admin route for user management
@app.route("/admin")
def admin():
    if "user" in session:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()

            cursor.close()
            conn.close()

            return render_template("admin.html", users=users)

        except mysql.connector.Error as err:
            return f"Database Error: {err}"
    
    return redirect("/login")

@app.route('/help')
def help():
    return render_template('help.html')


# Running your app
if __name__ == "__main__":
    app.run(debug=True)
