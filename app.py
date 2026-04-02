from flask import Flask, request, redirect, render_template, jsonify
import sqlite3
import qrcode
from supabase import create_client
import requests, os

app = Flask(__name__,
template_folder ="templates")


################################################################################


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



@app.route('/')
def index():
    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers")
    data = cursor.fetchall()

    conn.close()

    return render_template('index.html', data=data)

@app.route('/extinguisher/<id>')
def extinguisher(id):
    conn = sqlite3.connect("extinguishers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM extinguishers WHERE id=?", (id,))
    data = cursor.fetchone()

    conn.close()

    return render_template('detail.html', data=data)



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

# 🔥 Generate QR
    url = f"http://192.168.0.103:5002/extinguisher/{id}"
    img = qrcode.make(url)

    file_path = os.path.join("static", "qrcodes", f"{id}.png")
    img.save(file_path)

    return redirect('/')
    
if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')

# ✅ RUN APP
#if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=5002, debug=True)    

################################################################################






# Supabase config
SUPABASE_URL = "https://piaekrlgieptwqymbeur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpYWVrcmxnaWVwdHdxeW1iZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2MjIwMTUsImV4cCI6MjA5MDE5ODAxNX0.a6T13TgIe_enbB3kIO1qAFJzeslbOQk6PJTdrtzyK-s"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ✅ HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")

# ✅ VIEW ASSET
@app.route("/asset/<asset_id>")
def view_asset(asset_id):
    url = f"{SUPABASE_URL}/rest/v1/extinguishers?asset_id=eq.{asset_id}"
    response = requests.get(url, headers=headers)
    data = response.json()

    if not data:
        return "Asset not found"

    asset = data[0]

    return f"""
    <h2>Asset ID: {asset['asset_id']}</h2>
    Client: {asset.get('client_name', '')}<br>
    Type: {asset.get('type', '')}<br>
    Capacity: {asset.get('capacity', '')}<br>
    Expiry: {asset.get('expiry_date', '')}<br><br>

    <form method="POST" action="/update/{asset_id}">
        Technician: <input name="technician"><br>
        Remarks: <input name="remarks"><br>
        <button type="submit">Update Service</button>
    </form>
    """

# ✅ UPDATE ASSET
#@app.route("/update/<asset_id>", methods=["POST"])
#def update(asset_id):
#    technician = request.form.get("technician")
#remarks = request.form.get("remarks")

#    url = f"{SUPABASE_URL}/rest/v1/extinguishers?asset_id=eq.{asset_id}"

#    update_data = {
#        "technician": technician,
#        "remarks": remarks
#    }

#    requests.patch(url, json=update_data, headers=headers)

#    return redirect(f"/asset/{asset_id}")

# ✅ GET ALL DATA
@app.route("/extinguishers")
def get_data():
    data = supabase.table("fire_extinguisher_data").select("*").execute()
    return jsonify(data.data)

# ✅ ADD DATA
@app.route("/add-form", methods=["POST"])
def add_form():
    data = {
        "asset_id": request.form["id"],
        "location": request.form["location"],
        "type": request.form["type"],
        "expiry_date": request.form["expiry_date"]
    }

    supabase.table("fire_extinguisher_data").insert(data).execute()

    return "Added Successfully ✅"

@app.route("/check")
def check():
    return str(os.listdir("templates"))


# ✅ RUN APP
#if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=5002, debug=True)
