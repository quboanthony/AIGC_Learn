from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from gradio import Interface, inputs, outputs
import openai
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SECRET_KEY"] = os.urandom(24)
db = SQLAlchemy(app)
login_manager = LoginManager(app)

openai.api_key = open("k.txt",mode='r').read().strip()

# 设置管理员用户名和密码
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

conversation_history = ""

# User database model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    api_tokens = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("user_dashboard"))
        else:
            flash("Username already exists. Please choose another.")
            return redirect(url_for("register"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        elif user is not None and user.password == password:
            login_user(user)
            return redirect(url_for("user_dashboard"))  # Update this line
        else:
            flash("Invalid username or password.")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if current_user.username != ADMIN_USERNAME:
        flash("You are not authorized to access this page.")
        return redirect(url_for("login"))
    users = User.query.all()
    return render_template("admin_dashboard.html", users=users)

@app.route("/admin_recharge/<int:user_id>")
@login_required
def admin_recharge(user_id):
    if current_user.username != ADMIN_USERNAME:
        flash("You are not authorized to perform this action.")
        return redirect(url_for("login"))
    user = User.query.get(user_id)
    user.api_tokens += 100
    db.session.commit()
    flash(f"Successfully recharged 100 tokens for user {user.username}.")
    return redirect(url_for("admin_dashboard"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def chatbot_query(prompt):
    global conversation_history
    user = User.query.filter_by(id=current_user.id).first()

    if user.api_tokens > 0:
        user.api_tokens -= 1
        db.session.commit()

        # Update the conversation history with the user's message
        conversation_history += f"User: {prompt}\nAI:"

        # Use the openai.ChatCompletion.create() method for GPT-3.5-turbo
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": conversation_history}],
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.5,
        )

        # Update the conversation history with the AI's response
        response_text = response['choices'][0]['message']['content']
        conversation_history += f" {response_text.strip()}\n"

        return response_text.strip()

    else:
        return "Insufficient API tokens."

@app.route("/chat_interact", methods=["POST"])
@login_required
def chat_interact():
    prompt = request.form["prompt"]
    response = chatbot_query(prompt)
    return {"response": response}

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/user_dashboard")
@login_required
def user_dashboard():
    user = User.query.filter_by(id=current_user.id).first()
    return render_template("user_dashboard.html", api_tokens=user.api_tokens)


if __name__ == "__main__":
    app.run(debug=True, port=5001)