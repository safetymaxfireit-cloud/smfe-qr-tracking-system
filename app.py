from flask import Flask, request, render_template, Response
import io
import qrcode
import os
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

# 🔥 DATABASE CONNECTION
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

##########################################################
# INIT DATABASE

def init_db():
    conn = get_connection()
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers ORDER BY id")
    data = cursor.fetchall()

    conn.close()

    return render_template('index.html', data=data)

##########################################################
# VIEW EXTINGUISHER

@app.route('/extinguisher/<id>')
def extinguisher(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM extinguishers WHERE id=%s", (id,))
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

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO extinguishers (id, type, location, expiry_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """, (id, type_, location, expiry))

            conn.commit()
            conn.close()

            return render_template("qr.html", id=id)

        except Exception as e:
            return f"🔥 Error: {str(e)}"

    return render_template("add.html")

##########################################################
# QR GENERATION (DYNAMIC)

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
# PRINT MULTIPLE QR

@app.route('/print_qr')
def print_qr():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM extinguishers ORDER BY id")
    data = cursor.fetchall()

    conn.close()

    return render_template("print_qr.html", data=data)

##########################################################

@app.route('/setup-db')
def setup_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # Insert admin user
    cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES ('admin', 'admin123', 'admin')
    ON CONFLICT (username) DO NOTHING
    """)

    conn.commit()
    conn.close()

    return "✅ Database setup done"

##########################################################
# HEALTH CHECK

@app.route("/check")
def check():
    return "App is running ✅"

##########################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
