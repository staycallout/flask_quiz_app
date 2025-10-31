from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import requests
from datetime import datetime

# Configuration
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data.db")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change_this_secret_in_production")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")  # set this in environment

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = SECRET_KEY

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# Database helper functions
def query_db(query, args=(), one=False, commit=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    if commit:
        get_db().commit()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# User management
def create_user(username, display_name, password):
    hashed = generate_password_hash(password)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, display_name, password_hash, total_score) VALUES (?, ?, ?, ?)",
            (username, display_name, hashed, 0),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user_by_username(username):
    return query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)

def get_user_by_id(user_id):
    return query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

# Routes
@app.route("/")
def index():
    # Weather widget: accepts ?city=CityName
    city = request.args.get("city", "Surabaya")
    weather_table = None
    weekday = datetime.now().strftime("%A")
    if app.config.get("OPENWEATHER_API_KEY"):
        try:
            base = "https://api.openweathermap.org/data/2.5/forecast"
            params = {"q": city, "appid": app.config["OPENWEATHER_API_KEY"], "units": "metric", "cnt": 24}
            r = requests.get(base, params=params, timeout=5)
            data = r.json()
            # Build a simple 3-day table (today, tomorrow, day after) from data
            days = {}
            for item in data.get("list", []):
                date_txt = item["dt_txt"].split(" ")[0]
                if date_txt not in days:
                    days[date_txt] = {
                        "temps": [],
                        "weathers": []
                    }
                days[date_txt]["temps"].append(item["main"]["temp"])
                days[date_txt]["weathers"].append(item["weather"][0]["description"])
            # take first 3 dates
            keys = sorted(days.keys())[:3]
            weather_table = []
            for k in keys:
                temps = days[k]["temps"]
                avg_temp = sum(temps)/len(temps)
                desc = max(set(days[k]["weathers"]), key=days[k]["weathers"].count)
                weather_table.append({"date": k, "avg_temp": round(avg_temp,1), "desc": desc})
        except Exception as e:
            weather_table = None
    else:
        # No API key set; show placeholder sample data
        weather_table = [
            {"date": datetime.now().strftime("%Y-%m-%d"), "avg_temp": 29.0, "desc": "cerah"},
            {"date": (datetime.now()).strftime("%Y-%m-%d"), "avg_temp": 30.0, "desc": "berawan"},
            {"date": (datetime.now()).strftime("%Y-%m-%d"), "avg_temp": 28.0, "desc": "hujan ringan"},
        ]
    hari = {'Monday':'Senin', 'Tuesday':'Selasa', 'Wednesday':'Rabu', 'Thursday':'Kamis', 'Friday':'Jumat', 'Saturday':'Sabtu', 'Sunday':'Minggu'}
    weekday = hari[weekday]
    return render_template("index.html", weather_table=weather_table, weekday=weekday, city=city)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        display_name = request.form["display_name"].strip()
        password = request.form["password"]
        password2 = request.form["password2"]
        if not username or not password or not display_name:
            flash("Semua kolom harus diisi.", "danger")
            return redirect(url_for("register"))
        if password != password2:
            flash("Kata sandi dan konfirmasi tidak cocok.", "danger")
            return redirect(url_for("register"))
        # check uniqueness
        if get_user_by_username(username):
            flash("Username sudah dipakai. Pilih yang lain.", "danger")
            return redirect(url_for("register"))
        # check unique display_name
        other = query_db("SELECT * FROM users WHERE display_name = ?", (display_name,))
        if other:
            flash("Nama panggilan sudah dipakai. Pilih yang lain.", "danger")
            return redirect(url_for("register"))
        ok = create_user(username, display_name, password)
        if ok:
            flash("Pendaftaran berhasil. Silakan masuk.", "success")
            return redirect(url_for("login"))
        else:
            flash("Terjadi kesalahan saat membuat akun.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["display_name"] = user["display_name"]
            flash("Berhasil masuk.", "success")
            return redirect(url_for("index"))
        else:
            flash("Login gagal. Periksa username dan kata sandi.", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("index"))

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user_id" not in session:
        flash("Silakan masuk untuk mengakses kuis.", "warning")
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    if request.method == "POST":
        qid = int(request.form["question_id"])
        # selected sekarang adalah original index dari pilihan (0-based)
        selected = int(request.form.get("choice", -1))
        q = query_db("SELECT * FROM questions WHERE id = ?", (qid,), one=True)
        correct = (selected == q["answer_index"])
        gained = 1 if correct else 0
        db = get_db()
        db.execute("UPDATE users SET total_score = total_score + ? WHERE id = ?", (gained, user["id"]))
        db.commit()
        # ambil text jawaban benar untuk pesan
        choices_list = q["choices"].split("||")
        correct_text = choices_list[int(q["answer_index"])]
        flash("Benar!" if correct else "Salah. Jawaban benar: {}".format(correct_text), "info")
        return redirect(url_for("quiz"))

    # GET: ambil satu pertanyaan acak
    q = query_db("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1", (), one=True)
    if not q:
        flash("Belum ada pertanyaan di database.", "warning")
        return redirect(url_for("index"))

    # buat list (original_index, choice_text) lalu acak urutannya
    choices = q["choices"].split("||")
    indexed = list(enumerate(choices))  # [(0, 'jawab A'), (1, 'jawab B'), ...]
    random.shuffle(indexed)             # acak urutan pasangan
    # kirim indexed ke template sehingga template dapat men-set value=original_index
    return render_template("quiz.html", question=q, indexed_choices=indexed)


@app.route("/leaderboard")
def leaderboard():
    rows = query_db("SELECT display_name, total_score FROM users ORDER BY total_score DESC LIMIT 50")
    return render_template("leaderboard.html", rows=rows)

@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Silakan masuk.", "warning")
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    return render_template("profile.html", user=user)

# Simple route to serve site info for footer
@app.context_processor
def inject_developer():
    return dict(developer_name="Bambang Widjanarko (Tutor Python Pro)")

if __name__ == "__main__":
    app.run(debug=True)