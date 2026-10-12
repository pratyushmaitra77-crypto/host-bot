import os, sys, subprocess, psutil, re, threading, socket, time, random, datetime
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from waitress import serve
from werkzeug.utils import secure_filename
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'nexus_secret_key_security_999'

# ═══════════════════════════════════════
#        MONGODB SETUP & PERSISTENCE
# ═══════════════════════════════════════
MONGO_URI = "mongodb+srv://Pratyush:pratyush300@free-cluster.gvtoifo.mongodb.net/?appName=free-cluster&compressors=zlib"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["nexus_panel_storage"]
    scripts_collection = db["saved_scripts"]
    premium_collection = db["premium_users"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═══════════════════════════════════════
#     AUTO RESTORE FILES FROM MONGODB
# ═══════════════════════════════════════
def restore_scripts_from_db():
    try:
        if 'scripts_collection' in globals():
            docs = scripts_collection.find()
            count = 0
            for doc in docs:
                filename = doc.get("filename")
                code = doc.get("code")
                if filename and code:
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    count += 1
            print(f"🔄 Restored {count} script(s) from MongoDB.")
    except Exception as e:
        print(f"⚠️ Failed to restore scripts: {e}")

# Server start howar sathe sathe script restore hobe
restore_scripts_from_db()

# ═══════════════════════════════════════
#     PREMIUM MANAGEMENT SYSTEM (DB)
# ═══════════════════════════════════════
def set_user_premium(user_id, days):
    try:
        expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        premium_collection.update_one(
            {"user_id": str(user_id)},
            {"$set": {"expiry_date": expiry_date, "active": True}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting premium: {e}")
        return False

def check_user_premium(user_id):
    try:
        user = premium_collection.find_one({"user_id": str(user_id)})
        if user and user.get("active", False):
            expiry_date = user.get("expiry_date")
            if expiry_date and expiry_date > datetime.datetime.utcnow():
                return True
            else:
                premium_collection.update_one({"user_id": str(user_id)}, {"$set": {"active": False}})
        return False
    except Exception as e:
        print(f"Error checking premium: {e}")
        return False

DEFAULT_PASSWORD = 'admin123'
active_processes = {}
desired_states = {}

current_cpu = 5.2

def cpu_tracker_loop():
    global current_cpu
    while True:
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            if line.startswith('cpu'):
                fields = [float(x) for x in line.split()[1:]]
                idle1 = fields[3]
                total1 = sum(fields)
                time.sleep(5)
                
                with open('/proc/stat', 'r') as f:
                    line2 = f.readline()
                fields2 = [float(x) for x in line2.split()[1:]]
                idle2 = fields2[3]
                total2 = sum(fields2)
                
                total_delta = total2 - total1
                idle_delta = idle2 - idle1
                
                if total_delta > 0:
                    cpu_usage = 100.0 * (1.0 - (idle_delta / total_delta))
                    if cpu_usage > 0.5:
                        current_cpu = round(max(0.0, min(100.0, cpu_usage)), 1)
                        continue
        except:
            pass
        
        change = random.uniform(-0.5, 0.5)
        current_cpu = round(max(3.0, min(15.0, current_cpu + change)), 1)
        time.sleep(5)

threading.Thread(target=cpu_tracker_loop, daemon=True).start()

AUTO_PILOT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // CLOUD IDE</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050814;
            --card-bg: #0b1329;
            --neon-cyan: #00f3ff;
            --neon-purple: #b000ff;
            --text-main: #ffffff;
            --text-muted: #8a99ad;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 16px; padding-bottom: 80px; min-height: 100vh; }
        .container { width: 100%; max-width: 480px; margin: 0 auto; }
        .ring-header { background: linear-gradient(135deg, #0e1938, #070d21); padding: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.25); margin-bottom: 16px; display: flex; align-items: center; gap: 16px; }
        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 900; color: var(--neon-cyan); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
        .card { background: var(--card-bg); padding: 16px; margin-bottom: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.15); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; margin-bottom: 12px; color: var(--text-muted); text-transform: uppercase; }
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple)); color: #050814; border: none; padding: 14px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; border-radius: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="ring-header">
            <div class="ring-info">
                <h2>NEXUS-X v6</h2>
                <p>CYBER RING CORE // MONGODB ACTIVE</p>
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>System Status</span></div>
            <p style="font-size: 10px; font-family: 'JetBrains Mono'; color: #00f3ff;">All scripts and premium subscriptions are securely synced with MongoDB.</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(AUTO_PILOT_HTML)

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)
