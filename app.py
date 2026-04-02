from flask import Flask, request, redirect, render_template
import sqlite3
import qrcode
import os

app = Flask(__name__, template_folder="templates")

# Secret key (for future login)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

# Ensure QR folder exists
os.makedirs("static/qrcodes", exist_ok=True)

##########################################################

# Create DB automatically
def init_db():
    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extinguishers (
        id TEXT,
        location TEXT,
        type TEXT,
        expiry_date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

##########################################################

# HOME
@app.route('/')
def index():
    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers")
    data = cursor.fetchall()

    conn.close()

    return render_template('index.html', data=data)

##########################################################

# VIEW EXTINGUISHER
@app.route('/extinguisher/<id>')
def extinguisher(id):
    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers WHERE id=?", (id,))
    data = cursor.fetchone()

    conn.close()

    return render_template('detail.html', data=data)

##########################################################

# ADD DATA + GENERATE QR
@app.route('/add-form', methods=['POST'])
def add_form():
    id = request.form['id']
    location = request.form['location']
    type_ = request.form['type']
    expiry_date = request.form['expiry_date']

    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO extinguishers VALUES (?, ?, ?, ?)",
                   (id, location, type_, expiry_date))

    conn.commit()
    conn.close()

    # 🔥 Use LIVE URL (Render)
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5002")
    url = f"{base_url}/extinguisher/{id}"

    img = qrcode.make(url)

    file_path = os.path.join("static", "qrcodes", f"{id}.png")
    img.save(file_path)

    return redirect('/')

##########################################################

# HEALTH CHECK
@app.route("/check")
def check():
    return "App is running ✅"

##########################################################

# RUN APP
if __name_ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5002)))
