from flask import Flask, request, render_template, Response
import io
import sqlite3
import qrcode
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

DB_NAME = "database.db"

# Ensure QR folder exists
#os.makedirs("static/qr", exist_ok=True)

##########################################################
# INIT DATABASE

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extinguishers (
        id TEXT PRIMARY KEY,
        type TEXT,
        location TEXT,
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers")
    data = cursor.fetchall()

    conn.close()

    return render_template('index.html', data=data)

##########################################################
# VIEW EXTINGUISHER

@app.route('/extinguisher/<id>')
def extinguisher(id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM extinguishers WHERE id=?", (id,))
        data = cursor.fetchone()

        conn.close()

        if data is None:
            return f"❌ No data found for ID: {id}"

        return render_template("view.html", data=data)

    except Exception as e:
        return f"🔥 Error: {str(e)}"

##########################################################
# ADD + QR GENERATION

@app.route('/add', methods=['GET', 'POST'])
def add_extinguisher():
    if request.method == 'POST':
        try:
            id = request.form['id']
            type_ = request.form['type']
            location = request.form['location']
            expiry = request.form['expiry']

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO extinguishers (id, type, location, expiry_date)
            VALUES (?, ?, ?, ?)
            """, (id, type_, location, expiry))

            conn.commit()
            conn.close()

            # 🔥 QR GENERATION
            base_url = os.getenv("BASE_URL") or "https://www.safetymaxfire.com"
            qr_url = f"{base_url}/extinguisher/{id}"

            img = qrcode.make(qr_url)

  #          file_path = f"static/qr/{id}.png"
  #          img.save(file_path)

            return render_template("qr.html", id=id)

        except Exception as e:
            return f"🔥 Error: {str(e)}"

    return render_template("add.html")

##########################################################

@app.route('/qr/<id>')
def generate_qr(id):
    base_url = os.getenv("BASE_URL") or "https://www.safetymaxfire.com"
    qr_url = f"{base_url}/extinguisher/{id}"

    img = qrcode.make(qr_url)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(buffer.getvalue(), mimetype='image/png')

##########################################################
# TEST DATA (OPTIONAL - REMOVE LATER)

def add_test_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO extinguishers (id, type, location, expiry_date)
    VALUES ('FE001', 'ABC 5kg', 'Office', '2027-12-31')
    """)

    conn.commit()
    conn.close()

add_test_data()

##########################################################

@app.route('/print_qr')
def print_qr():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM extinguishers")
    data = cursor.fetchall()

    conn.close()

    return render_template("print_qr.html", data=data)

##########################################################

# HEALTH CHECK

@app.route("/check")
def check():
    return "App is running ✅"

##########################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
