import os, sys, subprocess, threading, time, random, datetime, platform
from flask import Flask, render_template_string, request, redirect, url_for, session
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

active_processes = {}
ADMIN_PASSWORD = "admin123"

def kill_process_by_pid(pid):
    try:
        if platform.system() == "Windows":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(pid), 9)
    except Exception:
        try:
            os.kill(pid, 9)
        except Exception:
            pass

# ═══════════════════════════════════════
#     AUTO RESTORE & LAUNCH FROM MONGODB
# ═══════════════════════════════════════
def restore_and_launch_bots():
    try:
        if 'scripts_collection' in globals():
            docs = scripts_collection.find()
            count = 0
            for doc in docs:
                bot_id = doc.get("bot_id")
                filename = doc.get("filename")
                code = doc.get("code")
                if bot_id and filename and code:
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    
                    log_path = os.path.join(UPLOAD_FOLDER, f"log_{bot_id}.txt")
                    log_file = open(log_path, "w")

                    if filename.endswith(".py"):
                        cmd = [sys.executable, file_path]
                    elif filename.endswith(".js"):
                        cmd = ["node", file_path]
                    elif filename.endswith(".php"):
                        cmd = ["php", file_path]
                    else:
                        cmd = [sys.executable, file_path]
                    
                    try:
                        process = subprocess.Popen(
                            cmd,
                            stdout=log_file,
                            stderr=log_file,
                            start_new_session=True if platform.system() != "Windows" else False
                        )
                        active_processes[bot_id] = {
                            "pid": process.pid,
                            "filename": filename,
                            "file_path": file_path,
                            "log_path": log_path,
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        count += 1
                    except Exception as sub_err:
                        print(f"Failed to auto-launch {filename}: {sub_err}")
            print(f"🔄 Restored and launched {count} bot(s) from MongoDB.")
    except Exception as e:
        print(f"⚠️ Failed to restore scripts: {e}")

restore_and_launch_bots()

# ═══════════════════════════════════════
#          HTML TEMPLATES
# ═══════════════════════════════════════
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS-X // ADMIN LOGIN</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --bg-deep: #050814; --card-bg: #0b1329; --neon-cyan: #00f3ff; --neon-purple: #b000ff; --text-main: #ffffff; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 16px; }
        .login-card { background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid rgba(0, 243, 255, 0.25); width: 100%; max-width: 380px; text-align: center; box-shadow: 0 0 20px rgba(0, 243, 255, 0.1); }
        h2 { font-family: 'Orbitron', sans-serif; font-size: 16px; color: var(--neon-cyan); margin-bottom: 20px; }
        input[type="password"] { width: 100%; padding: 12px; background: #050814; border: 1px solid rgba(0,243,255,0.4); border-radius: 8px; color: #fff; margin-bottom: 16px; font-size: 14px; text-align: center; outline: none; }
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple)); color: #050814; border: none; padding: 12px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 12px; border-radius: 8px; cursor: pointer; text-transform: uppercase; }
        .error { color: #ff3366; font-size: 11px; margin-bottom: 12px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>SECURE LOGIN</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Admin Password (admin123)" required autofocus>
            <button type="submit" class="btn">Login to Panel</button>
        </form>
    </div>
</body>
</html>
"""

PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS-X // BOT MANAGER PANEL</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050814;
            --card-bg: #0b1329;
            --neon-cyan: #00f3ff;
            --neon-purple: #b000ff;
            --text-main: #ffffff;
            --text-muted: #8a99ad;
            --danger: #ff3366;
            --success: #00ff66;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 16px; min-height: 100vh; }
        .container { width: 100%; max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #0e1938, #070d21); padding: 20px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.25); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-family: 'Orbitron', sans-serif; font-size: 14px; color: var(--neon-cyan); margin-bottom: 3px; }
        .header p { font-size: 9px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
        .logout-btn { background: rgba(255,51,102,0.2); color: var(--danger); border: 1px solid var(--danger); padding: 6px 12px; border-radius: 6px; font-size: 10px; font-family: 'Orbitron', sans-serif; text-decoration: none; font-weight: bold; }
        .card { background: var(--card-bg); padding: 16px; margin-bottom: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.15); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 700; margin-bottom: 12px; color: var(--neon-cyan); text-transform: uppercase; }
        input[type="file"] { width: 100%; padding: 10px; background: #050814; border: 1px dashed rgba(0,243,255,0.4); border-radius: 8px; color: var(--text-main); margin-bottom: 12px; font-size: 12px; }
        .btn { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple)); color: #050814; border: none; padding: 12px; width: 100%; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; border-radius: 8px; cursor: pointer; text-transform: uppercase; }
        
        /* Full Screen Loading Overlay & Spinner (Chorka Ghura Animation) */
        #loading-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 20, 0.85); display: none;
            flex-direction: column; justify-content: center; align-items: center; z-index: 9999;
        }
        .spinner {
            width: 50px; height: 50px; border: 4px solid rgba(0, 243, 255, 0.1);
            border-top: 4px solid var(--neon-cyan); border-radius: 50%;
            animation: spin 0.8s linear infinite; margin-bottom: 15px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #loading-overlay p { font-family: 'Orbitron', sans-serif; font-size: 12px; color: var(--neon-cyan); letter-spacing: 1px; }

        .bot-item { background: rgba(5, 8, 20, 0.6); padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid var(--success); }
        .bot-info h4 { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text-main); }
        .bot-info p { font-size: 9px; color: var(--text-muted); margin-top: 2px; }
        .actions { display: flex; gap: 6px; }
        .btn-del { background: var(--danger); color: #fff; border: none; padding: 6px 10px; border-radius: 6px; font-size: 10px; font-family: 'Orbitron', sans-serif; cursor: pointer; text-decoration: none; }
        .btn-log { background: #333; color: var(--neon-cyan); border: 1px solid var(--neon-cyan); padding: 6px 10px; border-radius: 6px; font-size: 10px; font-family: 'Orbitron', sans-serif; cursor: pointer; text-decoration: none; }
    </style>
</head>
<body>
    <!-- Loading Overlay -->
    <div id="loading-overlay">
        <div class="spinner"></div>
        <p>DEPLOYING PROJECT TO CLOUD...</p>
    </div>

    <div class="container">
        <div class="header">
            <div>
                <h1>NEXUS-X PANEL</h1>
                <p>MONGODB SYNCED</p>
            </div>
            <a href="/logout" class="logout-btn">Logout</a>
        </div>

        <div class="card">
            <div class="card-title">Upload & Run Bot</div>
            <form action="/upload" method="POST" enctype="multipart/form-data" onsubmit="showLoader()">
                <input type="file" name="bot_file" required>
                <button type="submit" class="btn">🚀 Upload & Run</button>
            </form>
        </div>

        <div class="card">
            <div class="card-title">Active Running Bots</div>
            {% if bots %}
                {% for bid, info in bots.items() %}
                <div class="bot-item">
                    <div class="bot-info">
                        <h4>{{ info.filename }}</h4>
                        <p>ID: {{ bid }} | Started: {{ info.time }}</p>
                    </div>
                    <div class="actions">
                        <a href="/logs/{{ bid }}" target="_blank" class="btn-log">Logs</a>
                        <a href="/delete/{{ bid }}" class="btn-del">Stop</a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="font-size: 11px; color: var(--text-muted); text-align: center;">No active bots running.</p>
            {% endif %}
        </div>
    </div>

    <script>
        function showLoader() {
            document.getElementById('loading-overlay').style.display = 'flex';
        }
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════
#             FLASK ROUTES
# ═══════════════════════════════════════
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = "❌ Incorrect Password! Try again."
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(PANEL_HTML, bots=active_processes)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if 'bot_file' not in request.files:
        return redirect(url_for('home'))
    file = request.files['bot_file']
    if file.filename == '':
        return redirect(url_for('home'))
    
    filename = secure_filename(file.filename)
    if filename.endswith(('.py', '.js', '.php', '.zip')):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code_content = f.read()
            
        bot_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        scripts_collection.update_one(
            {"bot_id": bot_id},
            {"$set": {"bot_id": bot_id, "filename": filename, "code": code_content}},
            upsert=True
        )
        
        log_path = os.path.join(UPLOAD_FOLDER, f"log_{bot_id}.txt")
        log_file = open(log_path, "w")

        if filename.endswith(".py"):
            cmd = [sys.executable, file_path]
        elif filename.endswith(".js"):
            cmd = ["node", file_path]
        elif filename.endswith(".php"):
            cmd = ["php", file_path]
        else:
            cmd = [sys.executable, file_path]
            
        try:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True if platform.system() != "Windows" else False
            )
            active_processes[bot_id] = {
                "pid": process.pid,
                "filename": filename,
                "file_path": file_path,
                "log_path": log_path,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Run error: {e}")
            
    return redirect(url_for('home'))

@app.route('/logs/<bot_id>')
def view_logs(bot_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if bot_id in active_processes:
        log_path = active_processes[bot_id]["log_path"]
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs = f.read()
            return f"<pre style='background:#050814;color:#00f3ff;padding:16px;font-family:monospace;'>{logs}</pre>"
    return "No logs found or bot stopped."

@app.route('/delete/<bot_id>')
def delete_bot(bot_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if bot_id in active_processes:
        info = active_processes[bot_id]
        kill_process_by_pid(info["pid"])
        del active_processes[bot_id]
        try:
            scripts_collection.delete_one({"bot_id": bot_id})
        except:
            pass
    return redirect(url_for('home'))

if __name__ == '__main__':
    import string
    serve(app, host='0.0.0.0', port=7860)
