from flask import Flask, session, redirect, url_for, request, render_template, Response
import io
import qrcode
import os
import psycopg2

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect('/login')

            if session.get('role') != required_role:
                return "❌ Access Denied"

            return f(*args, **kwargs)
        return decorated_function
    return decorator

#Secret Key
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

#Session Fix (For Render/HTTPS)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
        client_name TEXT,
        address TEXT,
        po_number TEXT,
        type TEXT,
        location TEXT,
        expiry_date TEXT,
        remarks TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

##########################################################

# USERS TABLE 

def init_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # Default admin
    cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES ('admin', 'SMFE@369', 'admin')
    ON CONFLICT (username) DO NOTHING
    """)

    conn.commit()
    conn.close()

init_users()

###########################################################
# CREATE USER
@app.route('/create-user')
def create_user():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES
    ('creator', 'SMFE@369', 'head'),
    ON CONFLICT (username) DO NOTHING
    """)

    conn.commit()
    conn.close()

    return "Users Created"

##########################################################
# LOGIN ROUTE

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user'] = username
            session['role'] = user[3]
            return redirect('/')
        else:
            return "❌ Invalid login"

    return render_template("login.html")


##########################################################
# LOGOUT ROUTE

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

##########################################################

# HOME

@app.route('/')
@login_required
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
@login_required
def add_extinguisher():
    if request.method == 'POST':
        try:
            id = request.form['id']
            client_name = request.form['client_name']
            address = request.form['address']
            po_number = request.form['po_number']
            type_ = request.form['type']
            location = request.form['location']
            expiry = request.form['expiry']
            remarks = request.form['remarks']

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO extinguishers (id, client_name, address, po_number, type, location, expiry_date, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """, (id, client_name, address, po_number, type_, location, expiry, remarks))

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
    base_url = "https://app.safetymaxfire.com"
    qr_url = f"{base_url}/extinguisher/{id}"

    img = qrcode.make(qr_url)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(buffer.getvalue(), mimetype='image/png')

##########################################################
# PRINT MULTIPLE QR

@app.route('/print_qr')
@login_required
def print_qr():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM extinguishers ORDER BY id")
    data = cursor.fetchall()

    conn.close()

    return render_template("print_qr.html", data=data)

##########################################################
#EDIT ROUTE
@app.route('/edit/<id>', methods=['GET', 'POST'])
@role_required('head')   # Only head can edit
def edit_extinguisher(id):
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':       
        type_ = request.form['type']
        location = request.form['location']
        expiry = request.form['expiry']

        cursor.execute("""
        UPDATE extinguishers
        SET type=%s, location=%s, expiry_date=%s
        WHERE id=%s
        """, (type_, location, expiry, id))

        conn.commit()
        conn.close()

        return redirect(f"/extinguisher/{id}")

    cursor.execute("SELECT * FROM extinguishers WHERE id=%s", (id,))
    data = cursor.fetchone()
    conn.close()

    return render_template("edit.html", data=data)
    
##########################################################
# HEALTH CHECK

@app.route("/check")
def check():
    return "App is running ✅"

##########################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
