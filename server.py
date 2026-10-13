import os, sys, subprocess, threading, time, random, datetime, platform, string, psutil
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
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_processes = {}

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
                            "status": "Running",
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
#     SYSTEM MONITOR (CPU, RAM, STORAGE)
# ═══════════════════════════════════════
current_cpu = 5.0
current_ram = 25.0
current_storage = 12.5

def system_monitor_loop():
    global current_cpu, current_ram, current_storage
    while True:
        try:
            current_cpu = round(psutil.cpu_percent(interval=2), 1)
            mem = psutil.virtual_memory()
            current_ram = round(mem.percent, 1)
            
            # Calculate folder size for storage
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(UPLOAD_FOLDER):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            current_storage = round(total_size / (1024 * 1024), 2) # in MB
        except Exception:
            pass
        time.sleep(3)

threading.Thread(target=system_monitor_loop, daemon=True).start()

# ═══════════════════════════════════════
#          FULL FEATURED UI HTML
# ═══════════════════════════════════════
PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXUS-X // CLOUD IDE & MONITOR</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050814;
            --card-bg: #0b1329;
            --neon-cyan: #00f3ff;
            --neon-purple: #b000ff;
            --neon-pink: #ff007f;
            --text-main: #ffffff;
            --text-muted: #8a99ad;
            --danger: #ff3366;
            --success: #00ff66;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg-deep); color: var(--text-main); font-family: 'Inter', sans-serif; padding: 16px; padding-bottom: 80px; min-height: 100vh; }
        .container { width: 100%; max-width: 500px; margin: 0 auto; }
        
        /* Header with Chorka (Spinner Wheel) */
        .ring-header { background: linear-gradient(135deg, #0e1938, #070d21); padding: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.25); margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 900; color: var(--neon-cyan); text-shadow: 0 0 10px rgba(0,243,255,0.5); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
        
        .spinner-wheel {
            width: 28px; height: 28px;
            border: 3px solid rgba(0, 243, 255, 0.2);
            border-top: 3px solid var(--neon-cyan);
            border-right: 3px solid var(--neon-pink);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        .card { background: var(--card-bg); padding: 16px; margin-bottom: 16px; border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; margin-bottom: 12px; color: var(--text-muted); text-transform: uppercase; display: flex; justify-content: space-between; align-items: center; }
        
        label { font-size: 9px; color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; display: block; margin-bottom: 4px; }
        input[type="file"] { width: 100%; padding: 8px; background: #050814; border: 1px dashed rgba(0,243,255,0.4); border-radius: 8px; color: var(--text-main); margin-bottom: 10px; font-size: 10px; }
        
        /* Colorful Glowing Deploy Button */
        .btn-deploy { 
            background: linear-gradient(135deg, #00f3ff, #b000ff, #ff007f); 
            background-size: 200% 200%;
            color: #ffffff; 
            border: none; 
            padding: 12px; 
            width: 100%; 
            font-family: 'Orbitron', sans-serif; 
            font-weight: 900; 
            font-size: 11px; 
            border-radius: 10px; 
            cursor: pointer; 
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.4);
            animation: gradientShift 4s ease infinite, pulseGlow 2s infinite;
            transition: 0.2s;
        }
        .btn-deploy:active { transform: scale(0.97); }
        @keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 10px rgba(0,243,255,0.3); } 50% { box-shadow: 0 0 20px rgba(255,0,127,0.6); } 100% { box-shadow: 0 0 10px rgba(0,243,255,0.3); } }

        /* Monitor Grid */
        .monitor-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; }
        .metric-box { background: rgba(5, 8, 20, 0.7); padding: 10px; border-radius: 8px; border: 1px solid rgba(0,243,255,0.1); }
        .metric-box h3 { font-family: 'Orbitron', sans-serif; font-size: 11px; color: var(--neon-cyan); margin-top: 4px; }
        .metric-box span { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

        /* Bot List Items */
        .bot-item { background: rgba(5, 8, 20, 0.8); padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid var(--success); }
        .bot-info h4 { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--text-main); }
        .bot-info p { font-size: 8px; color: var(--text-muted); margin-top: 2px; }
        
        .actions { display: flex; gap: 4px; }
        .btn-action { padding: 5px 8px; border-radius: 6px; font-size: 8px; font-family: 'Orbitron', sans-serif; cursor: pointer; text-decoration: none; font-weight: bold; border: none; }
        .btn-start { background: var(--success); color: #050814; }
        .btn-close { background: #ffaa00; color: #050814; }
        .btn-del { background: var(--danger); color: #fff; }
        .btn-log { background: #333; color: var(--neon-cyan); border: 1px solid var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header with Spinning Chorka -->
        <div class="ring-header">
            <div class="ring-info">
                <h2>NEXUS-X CLOUD v6</h2>
                <p>MONGODB SYNCED // LIVE MONITOR</p>
            </div>
            <div class="spinner-wheel"></div>
        </div>

        <!-- Live System Monitor -->
        <div class="card">
            <div class="card-title"><span>System Metrics</span></div>
            <div class="monitor-grid">
                <div class="metric-box">
                    <span>CPU</span>
                    <h3>{{ cpu }}%</h3>
                </div>
                <div class="metric-box">
                    <span>RAM</span>
                    <h3>{{ ram }}%</h3>
                </div>
                <div class="metric-box">
                    <span>STORAGE</span>
                    <h3>{{ storage }} MB</h3>
                </div>
            </div>
        </div>

        <!-- Upload Hub (Bot Script & Requirements) -->
        <div class="card">
            <div class="card-title"><span>Upload & Deploy Center</span></div>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <label>📁 Select Bot Script (.py / .js / .php / .zip)</label>
                <input type="file" name="bot_file" required>
                
                <label>📦 Optional requirements.txt (Python)</label>
                <input type="file" name="req_file">
                
                <button type="submit" class="btn-deploy">🚀 UPLOAD & DEPLOY SCRIPT</button>
            </form>
        </div>

        <!-- Active Bots Management -->
        <div class="card">
            <div class="card-title"><span>Active Projects & Live Logs</span></div>
            {% if bots %}
                {% for bid, info in bots.items() %}
                <div class="bot-item">
                    <div class="bot-info">
                        <h4>{{ info.filename }}</h4>
                        <p>ID: {{ bid }} | Status: <span style="color:var(--success);">{{ info.status }}</span></p>
                    </div>
                    <div class="actions">
                        <a href="/logs/{{ bid }}" target="_blank" class="btn-action btn-log">Logs</a>
                        {% if info.status == 'Running' %}
                            <a href="/close/{{ bid }}" class="btn-action btn-close">Close</a>
                        {% else %}
                            <a href="/start/{{ bid }}" class="btn-action btn-start">Start</a>
                        {% endif %}
                        <a href="/delete/{{ bid }}" class="btn-action btn-del">Del</a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="font-size: 9px; font-family: 'JetBrains Mono'; color: var(--text-muted); text-align: center;">No active projects running.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(PANEL_HTML, bots=active_processes, cpu=current_cpu, ram=current_ram, storage=current_storage)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'bot_file' not in request.files:
        return redirect(url_for('home'))
    file = request.files['bot_file']
    if file.filename == '':
        return redirect(url_for('home'))
    
    # Handle optional requirements.txt
    req_file = request.files.get('req_file')
    if req_file and req_file.filename != '':
        req_filename = secure_filename(req_file.filename)
        req_path = os.path.join(UPLOAD_FOLDER, req_filename)
        req_file.save(req_path)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

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
                "status": "Running",
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Run error: {e}")
            
    return redirect(url_for('home'))

@app.route('/close/<bot_id>')
def close_bot(bot_id):
    if bot_id in active_processes:
        info = active_processes[bot_id]
        kill_process_by_pid(info["pid"])
        active_processes[bot_id]["status"] = "Stopped"
    return redirect(url_for('home'))

@app.route('/start/<bot_id>')
def start_bot(bot_id):
    if bot_id in active_processes:
        info = active_processes[bot_id]
        file_path = info["file_path"]
        filename = info["filename"]
        log_path = info["log_path"]
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
            active_processes[bot_id]["pid"] = process.pid
            active_processes[bot_id]["status"] = "Running"
        except Exception as e:
            print(f"Start error: {e}")
    return redirect(url_for('home'))

@app.route('/logs/<bot_id>')
def view_logs(bot_id):
    if bot_id in active_processes:
        log_path = active_processes[bot_id]["log_path"]
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs = f.read()
            return f"<pre style='background:#050814;color:#00f3ff;padding:16px;font-family:monospace;font-size:11px;'>{logs}</pre>"
    return "No logs found."

@app.route('/delete/<bot_id>')
def delete_bot(bot_id):
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
    serve(app, host='0.0.0.0', port=7860)
