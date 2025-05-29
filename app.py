import os
import pyttsx3
import requests
import google.generativeai as genai
import speech_recognition as sr
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random
from flask_socketio import SocketIO

genai.configure(api_key="---")  # Replace with actual API key
GNEWS_API_KEY = "---"  # Replace with actual API key

# Initialize Speech Recognizer
recognizer = sr.Recognizer()

app = Flask(__name__, template_folder=".")
app.secret_key = "supersecretkey"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bcrypt = Bcrypt(app)

#Default
domain="general"
discussion=True

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'system@25'  # Enter your MySQL password
app.config['MYSQL_DB'] = 'VNR'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

# ✅ FIXED: Ensure queries are run inside `app.app_context()`
with app.app_context():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users")
    print(cursor.fetchall())  # Check if it fetches any user data
    cursor.close()

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return User(user["id"], user["email"])
    return None

def get_current_user():
    if current_user.is_authenticated:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT name, email, discussion_enabled FROM users WHERE email = %s", (current_user.email,))
        user = cursor.fetchone()
        cursor.close()  # ✅ Close cursor properly
        return user
    return None

@app.route('/')
def home():
    return send_from_directory(os.getcwd(), "home.html")

# ✅ FIXED: Password is now hashed before storing
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        selected_domain = request.form['domain']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO users (name, email, password, selected_domain) VALUES (%s, %s, %s, %s)", 
                        (name, email, hashed_password, selected_domain))
            mysql.connection.commit()
            cursor.close()

        flash("Registration successful! You can now login.", "success")
        return redirect(url_for('login'))
    
    return send_from_directory(os.getcwd(), "reg.html")

# ✅ FIXED: Use bcrypt to verify password
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id, email, password FROM users WHERE email=%s", (email,))
            user_data = cursor.fetchone()
            cursor.close()

        if user_data and bcrypt.check_password_hash(user_data["password"], password):
            user = User(user_data["id"], user_data["email"])
            login_user(user)

            flash("Login successful!", "success")
            return redirect(url_for('reporter'))
        else:
            flash("Invalid email or password!", "danger")

    return send_from_directory(os.getcwd(), "login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))  # ✅ FIXED redirect issue

@app.route('/get_news_domain')
@login_required  
def get_news_domain():
    user_id = current_user.get_id()
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT selected_domain, discussion_enabled FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        return jsonify({"domain": result["selected_domain"], "discussion_enabled": bool(result["discussion_enabled"])})
    
    return jsonify({"domain": "general", "discussion_enabled": False})


@app.route('/update_news_domain', methods=['POST'])
@login_required
def update_news_domain():
    global domain
    data = request.json
    domain = data.get("domain")

    if not domain:
        return jsonify({"error": "Missing news domain"}), 400  # Bad request

    user_id = current_user.get_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        cursor = mysql.connection.cursor()
        query = "UPDATE users SET selected_domain = %s WHERE id = %s"
        cursor.execute(query, (domain, user_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"message": "News domain updated successfully"})

    except Exception as e:
        print(f"Error updating domain: {e}")
        return jsonify({"error": "Failed to update news domain"}), 500

@app.route('/update_discussion_setting', methods=['POST'])
def update_discussion_setting():
    global discussion
    data = request.json  # ✅ Get JSON data from frontend
    print("Received Data:", data)  # Debug incoming data

    discussion_enabled = int(data.get("discussion_enabled", 0))  # Convert to int (1 or 0)

    try:
        with app.app_context():
            cursor = mysql.connection.cursor()

            # Verify user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (current_user.id,))
            existing_user = cursor.fetchone()

            if not existing_user:
                print("Error: User not found in database")
                return jsonify({"error": "User not found"}), 404  

            # Update discussion setting
            cursor.execute("UPDATE users SET discussion_enabled = %s WHERE id = %s",
                           (discussion_enabled, current_user.id))
            mysql.connection.commit()
            rows_affected = cursor.rowcount  # Check if update happened
            cursor.close()

            if rows_affected == 0:
                print("Error: No rows were updated. Check user ID.")
                return jsonify({"error": "Update failed. No changes made."}), 400

            discussion = discussion_enabled  # Update global variable
            print(f"✅ Discussion setting updated for user {current_user.id} to {discussion_enabled}")
            return jsonify({"message": "Discussion setting updated successfully"})

    except Exception as e:
        import traceback
        print(f"❌ Error updating discussion setting: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to update discussion setting: {str(e)}"}), 500



@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(os.getcwd(), filename)

@app.route('/reporter')
@login_required
def reporter():
    user = get_current_user()
    if user:
        return render_template("index.html", name=user['name'], email=user['email'])
    return redirect('/login')

engine = pyttsx3.init()

@app.route('/process_speech', methods=['POST'])
def process_speech():
    """Processes user speech and fetches news or generates an AI discussion response."""
    try:
        data = request.get_json()
        if not data or "text" not in data:
            print("❌ Error: No speech text received!")
            return jsonify({"error": "No speech text received"}), 400

        user_text = data["text"].strip().lower()
        print(f"🗣 Received Speech: {user_text}")


        # Check if user is asking for news
        if "news" in user_text or "tell me the news" in user_text or "next news" in user_text or "latest news" in user_text:
            response = fetch_news()  # Fetch new news article
        elif "what" in user_text or "tell me about" in user_text or "about" in user_text:  
            response = discuss_with_gemini(user_text)  # AI discussion based on user query
        else:
            response = discuss_with_gemini(user_text)

        if not response or response.strip() == "":
            response = "I'm sorry, I don't have enough information on that topic."

        print(f"🤖 AI Response: {response}")
        return jsonify({"reply": response})

    except Exception as e:
        print(f"❌ Error processing speech: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


def summarize_text(text):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"Summarize the following news story in a very short and very simple and understandable, engaging, and impactful way: {text}. Give it in simple text form."
    response = model.generate_content(prompt)
    return response.text if response else "Could not generate summary."


# Store previously reported news articles
last_reported_titles = []
selected_article="General"
def fetch_news():
    global selected_article
    """Fetches the latest unique news from the selected domain."""
    user_id = current_user.get_id()
    if not user_id:
        print("❌ Error: User not authenticated.")
        return "Please log in to get personalized news."

    try:
        # Fetch the selected domain from MySQL
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT selected_domain FROM users WHERE id = %s", (user_id,))
        user_domain = cursor.fetchone()
        cursor.close()

        domain = user_domain["selected_domain"] if user_domain else "general"
        print(f"🔍 Fetching news for domain: {domain}")

        url = f"https://gnews.io/api/v4/top-headlines?category={domain}&lang=en&country=in&apikey={GNEWS_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])

        if not articles:
            return f"No {domain} news available right now."

        # Filter out previously reported news
        new_articles = [article for article in articles if article["title"] not in last_reported_titles]

        if not new_articles:
            return "No new news available at the moment. Please try again later."

        # Randomly select a news article to report
        selected_article = random.choice(new_articles)
        news_text = f"{selected_article['title']}. {selected_article['description']}"

        # Summarize the news for a short, engaging response
        summarized_news = summarize_text(news_text)

        # Store reported news title
        last_reported_titles.append(selected_article["title"])
        
        return summarized_news

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching news: {e}")
        return "Failed to fetch news."
 
def discuss_with_gemini(question):
    global selected_article
    """Generates AI response using Gemini AI."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"User asked: {question}. Provide a detailed but very easy-to-understand, simple and very very short response with respective the news '{selected_article}' OR just give general response.The response should be not more that 30 words."
        response = model.generate_content(prompt)

        if response and hasattr(response, "text") and response.text.strip():
            response=response.text
            print(f"✅ AI Response: {response}")
            return response
        else:
            print("❌ AI returned an empty response! Using a fallback answer.")
            return "I don't have enough information on that, but I can try to summarize if you'd like."

    except Exception as e:
        print(f"❌ Error with AI Response: {e}")
        return "I'm currently unable to fetch the response. Please try again later."


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000, debug=True)
