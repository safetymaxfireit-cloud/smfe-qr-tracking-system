from flask import Flask, session, redirect, request, render_template, Response
import io
import qrcode
import os
import psycopg2
import pandas as pd
from functools import wraps

# ================================
# APP CONFIG
# ================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ================================
# AUTH
# ================================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') != role:
                return "❌ Access Denied"
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ================================
# DATABASE INIT
# ================================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extinguishers (
        serial_number SERIAL PRIMARY KEY,
        id TEXT UNIQUE,
        client_name TEXT,
        address TEXT,
        po_number TEXT,
        order_id TEXT,
        type TEXT,
        location TEXT,
        supply_date TEXT,
        expiry_date TEXT,
        remarks TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================================
# GET DATABASE
# ================================
def get_data_from_db(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, client_name, address, po_number, order_id, type, location, supply_date, expiry_date, remarks
    FROM extinguishers WHERE id=%s
    """, (id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))

    conn.close()
    return data

# ================================
# USERS
# ================================
def init_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES ('admin', 'SMFE@369', 'admin')
    ON CONFLICT (username) DO NOTHING
    """)

    conn.commit()
    conn.close()

init_users()

# ================================
# LOGIN
# ================================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (request.form['username'], request.form['password'])
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            session['role'] = user[3]
            return redirect('/')
        return "❌ Invalid Login"

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================================
# HOME
# ================================
@app.route('/')
@login_required
def index():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, client_name, type FROM extinguishers ORDER BY serial_number DESC")
    data = cursor.fetchall()

    conn.close()
    return render_template("index.html", data=data)

# ================================
# VIEW PAGE
# ================================

from datetime import datetime

@app.route('/extinguisher/<id>')
def extinguisher(id):
    data = get_data_from_db(id)
    
    if not data:
        return "❌ Not Found"
    
    from datetime import datetime
    today = datetime.today().date()

    expiry_date = None
    if data.get('expiry_date'):
        try:
            expiry_date = datetime.strptime(data['expiry_date'], "%Y-%m-%d").date()
        except:
            expiry_date = None

    return render_template(
        "template.html",
        data=data,
        today=today,
        expiry_date=expiry_date
    )
    
def view_extinguisher(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, client_name, address, po_number, order_id, type, location, supply_date, expiry_date, remarks
    FROM extinguishers WHERE id=%s
    """, (id,))

    row = cursor.fetchone()

    if not row:
        return "❌ Not Found"

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))

    conn.close()

    return render_template("view.html", data=data)

# ================================
# ADD
# ================================
@app.route('/add', methods=['GET','POST'])
@login_required
def add_extinguisher():
    if request.method == 'POST':
        try:
        # ✅ GET FORM DATA FIRST
            company = request.form['company']
            location = request.form['location']
            type_ = request.form['type']

            client_name = request.form['client_name']
            address = request.form['address']
            po_number = request.form['po_number']
            order_id = request.form['order_id']
            supply_date = request.form['supply_date']
            expiry = request.form['expiry']
            remarks = request.form['remarks']
        
            conn = get_connection()
            cursor = conn.cursor()
# STEP 1: Get next serial number manually
            cursor.execute("""
            SELECT COALESCE(MAX(serial_number), 0) + 1 FROM extinguishers
            """)
            serial_number = cursor.fetchone()[0]
            
# STEP 2: Generate ID
            serial = str(serial_number).zfill(5)
            
            id = f"{company}_FE{serial}_{location.title().replace(' ','')}_{type_.replace(' ','')}"
            
# STEP 3: INSERT WITH ID
            cursor.execute("""
            INSERT INTO extinguishers 
            (id, serial_number, client_name, address, po_number, order_id, type, location, supply_date, expiry_date, remarks)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                id,
                serial_number,
                client_name,
                address,
                po_number,
                order_id,
                type_,
                location,
                supply_date,
                expiry,
                remarks
            ))

            conn.commit()
            conn.close()

            return redirect(f"/single_qr/{id}")

        except Exception as e:
            return f"🔥 Error: {str(e)}"

    return render_template("add.html")

# ================================
# EDIT
# ================================
@app.route('/edit/<id>', methods=['GET','POST'])
@role_required('admin')
def edit_extinguisher(id):
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute("""
        UPDATE extinguishers SET
        client_name=%s,
        address=%s,
        po_number=%s,
        order_id=%s,
        type=%s,
        location=%s,
        supply_date=%s,
        expiry_date=%s,
        remarks=%s
        WHERE id=%s
        """, (
            request.form['client_name'],
            request.form['address'],
            request.form['po_number'],
            request.form['order_id'],
            request.form['type'],
            request.form['location'],
            request.form['supply_date'],
            request.form['expiry'],
            request.form['remarks'],
            id
        ))

        conn.commit()
        conn.close()
        return redirect(f"/extinguisher/{id}")

    cursor.execute("SELECT * FROM extinguishers WHERE id=%s", (id,))
    row = cursor.fetchone()

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))

    conn.close()
    return render_template("edit.html", data=data)

# ================================
# QR
# ================================
@app.route('/qr/<id>')
def qr(id):
    qr_url = f"https://app.safetymaxfire.com/extinguisher/{id}"

    img = qrcode.make(qr_url, box_size=3, border=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(buf.getvalue(), mimetype='image/png')
# ================================
# SINGLE QR
# ================================

@app.route('/single_qr/<id>')
@login_required
def single_qr(id):
    return render_template("single_qr.html", id=id)

# ================================
# LABEL
# ================================
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "static", "fonts", "0222.ttf")

@app.route('/label/<id>')
@login_required
def label(id):
    from PIL import Image, ImageDraw, ImageFont

    qr_url = f"https://app.safetymaxfire.com/extinguisher/{id}"

    # =========================
    # 📐 SIZE (50mm x 30mm @300 DPI)
    # =========================
    DPI = 300
    WIDTH = int(50 * DPI / 25.4)   # 590 px
    HEIGHT = int(30 * DPI / 25.4)  # 354 px

    QR_SIZE = 210   # balanced (prevents cutting)

    # =========================
    # 🔳 QR
    # =========================
    qr = qrcode.make(qr_url)
    qr = qr.resize((QR_SIZE, QR_SIZE))

    # =========================
    # 🧱 CANVAS
    # =========================
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)

    # =========================
    # 🔤 FONTS (Adjusted)
    # =========================
    try:
        title_font = ImageFont.truetype(FONT_PATH, 38)   # slightly smaller
        subtitle_font = ImageFont.truetype(FONT_PATH, 22)
        id_font = ImageFont.load_default()    # clean readable
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        id_font = ImageFont.load_default()

    # =========================
    # 🔴 HEADER (RED + FIXED SPACING)
    # =========================
    draw.text(
        (WIDTH//2, 15),
        "SAFETYMAX",
        fill=(200, 0, 0),   # RED
        anchor="ma",
        font=title_font
    )

    draw.text(
        (WIDTH//2, 55),   # controlled spacing
        "FIRE ENGINEERS",
        fill=(200, 0, 0),
        anchor="ma",
        font=subtitle_font
    )

    # =========================
    # 🔳 QR POSITION (CENTERED)
    # =========================
    qr_x = (WIDTH - QR_SIZE) // 2
    qr_y = 85

    canvas.paste(qr, (qr_x, qr_y))

    # =========================
    # 🔵 ID (VISIBLE + CLEAN)
    # =========================
    draw.text(
        (WIDTH//2, HEIGHT - 35),   # safe margin (no cutting)
        id,
        fill="black",
        anchor="ma",
        font=id_font
    )

    # =========================
    # 📦 EXPORT
    # =========================
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", dpi=(300,300))
    buf.seek(0)

    return Response(buf.getvalue(), mimetype='image/png')
# ================================
# PRINT QR LABELS
# ================================
@app.route('/print_qr', methods=['GET', 'POST'])
@login_required
def print_qr():
    conn = get_connection()
    cursor = conn.cursor()

    # Get all clients for dropdown
    cursor.execute("SELECT DISTINCT client_name FROM extinguishers ORDER BY client_name")
    clients = [row[0] for row in cursor.fetchall()]

    selected_client = request.args.get('client')

    if selected_client:
        cursor.execute(
            "SELECT id FROM extinguishers WHERE client_name=%s ORDER BY serial_number DESC",
            (selected_client,)
        )
    else:
        cursor.execute(
            "SELECT id FROM extinguishers ORDER BY serial_number DESC"
        )

    data = cursor.fetchall()
    conn.close()

    return render_template(
        "print_qr.html",
        data=data,
        clients=clients,
        selected_client=selected_client
    )


# ================================
# BULK UPLOAD
# ================================
@app.route('/bulk_upload', methods=['GET','POST'])
@role_required('admin')
def bulk_upload():
    if request.method == 'POST':
        file = request.files['file']
        df = pd.read_excel(file)

        conn = get_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
            INSERT INTO extinguishers
            (client_name, address, po_number, order_id, type, location, supply_date, expiry_date, remarks)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING serial_number
            """, (
                row['Client Name'],
                row['Address'],
                row['PO Number'],
                row['Order ID'],
                row['Type'],
                row['Location'],
                str(row['Supply Date']),
                str(row['Expiry Date']),
                row['Remarks']
            ))

            serial = cursor.fetchone()[0]
            serial_str = str(serial).zfill(5)

            id = f"SM_FE{serial_str}_{row['Location'].replace(' ','')}_{row['Type'].replace(' ','')}"

            cursor.execute(
                "UPDATE extinguishers SET id=%s WHERE serial_number=%s",
                (id, serial)
            )

        conn.commit()
        conn.close()

        return "✅ Bulk Upload Done"

    return render_template("bulk_upload.html")
    
# ================================
@app.route('/check')
def check():
    return "✅ Running"

# ================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
