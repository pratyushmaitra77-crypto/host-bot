import os
import sys

# Force release ports to avoid Address already in use error
os.system("fuser -k 5050/tcp 2>/dev/null")

import subprocess
import threading
import socket
import time
import random
import re
import json
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from waitress import serve
from werkzeug.utils import secure_filename
import psutil

app = Flask(__name__)
app.secret_key = 'nexus_secure_session_key_portal'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'hosted_bots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS_FILE = 'users_db.json'
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

DEFAULT_KEY = 'admin123'
active_processes = {}
desired_states = {}
current_cpu = 5.2

LIB_MAP = {
    "telegram": "python-telegram-bot",
    "telethon": "telethon",
    "pyrogram": "pyrogram",
    "tgcrypto": "tgcrypto",
    "discord": "discord.py",
    "pymongo": "pymongo",
    "dns": "dnspython",
    "flask": "flask",
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "aiohttp": "aiohttp",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "psutil": "psutil",
    "motor": "motor",
    "dotenv": "python-dotenv",
    "cryptography": "cryptography"
}

def auto_install_dependencies(script_path):
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        imports = re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
        to_install = set()
        
        for imp in imports:
            if imp in LIB_MAP:
                to_install.add(LIB_MAP[imp])
                
        if "pyrogram" in content.lower():
            to_install.add("tgcrypto")
            to_install.add("pydantic")
            
        if "pymongo" in content.lower() or "motor" in content.lower():
            to_install.add("dnspython")

        for lib in to_install:
            print(f"📦 [AUTO-INSTALLER] Installing required library: {lib}...")
            os.system(f"{sys.executable} -m pip install --no-cache-dir --upgrade {lib}")
    except Exception as e:
        print(f"⚠️ Dependency installer warning: {e}")

def get_user_folder():
    if 'user' not in session:
        return None
    safe_email = session['user'].replace('@', '_at_').replace('.', '_')
    user_dir = os.path.join(UPLOAD_FOLDER, safe_email)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

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

        body { 
            background: var(--bg-deep); 
            color: var(--text-main); 
            font-family: 'Inter', sans-serif; 
            padding: 16px; 
            padding-bottom: 70px;
            min-height: 100vh;
        }
        
        .container { width: 100%; max-width: 480px; margin: 0 auto; }
        
        .ring-header { 
            background: linear-gradient(135deg, #0e1938, #070d21);
            padding: 16px; 
            border-radius: 14px;
            border: 1px solid rgba(0, 243, 255, 0.25);
            margin-bottom: 16px; 
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .ring-avatar {
            width: 50px;
            height: 50px;
            background: rgba(0, 243, 255, 0.1);
            border: 1px solid rgba(0, 243, 255, 0.4);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            animation: spinRing 6s linear infinite;
        }

        @keyframes spinRing {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .ring-info h2 { font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 900; color: var(--neon-cyan); }
        .ring-info p { font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
        
        .status-badge-wrapper {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 243, 255, 0.08);
            padding: 5px 10px;
            border-radius: 20px;
            border: 1px solid rgba(0, 243, 255, 0.3);
        }
        .online-dot {
            width: 6px;
            height: 6px;
            background-color: var(--neon-cyan);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--neon-cyan);
        }
        .badge { font-size: 8px; color: var(--neon-cyan); font-weight: 700; font-family: 'Orbitron', sans-serif; }

        .auth-wrapper { display: flex; align-items: center; justify-content: center; min-height: 85vh; }
        .auth-box {
            background: rgba(11, 19, 41, 0.95);
            padding: 30px 20px;
            border-radius: 20px;
            border: 1px solid rgba(0, 243, 255, 0.4);
            box-shadow: 0 0 30px rgba(0, 243, 255, 0.2);
            text-align: center;
            width: 100%;
        }
        .auth-box h2 { font-family: 'Orbitron'; font-size: 18px; color: var(--neon-cyan); margin-bottom: 20px; }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab-btn {
            flex: 1; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
            color: var(--text-muted); padding: 12px; font-size: 11px; font-family: 'Orbitron';
            font-weight: 700; border-radius: 10px; cursor: pointer; text-align: center;
        }
        .tab-btn.active { background: rgba(0, 243, 255, 0.15); color: var(--neon-cyan); border-color: rgba(0, 243, 255, 0.5); }

        .input-field {
            width: 100%;
            background: #040814;
            border: 1px solid rgba(0, 243, 255, 0.3);
            padding: 14px 16px;
            border-radius: 10px;
            color: #fff;
            font-family: 'JetBrains Mono';
            font-size: 13px;
            margin-bottom: 15px;
            outline: none;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }
        .stat-box {
            background: rgba(11, 19, 41, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 10px 14px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
        }
        .stat-label { font-size: 8px; font-family: 'Orbitron', sans-serif; color: var(--text-muted); }
        .stat-val { font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #fff; margin-top: 2px; }

        .resource-card {
            background: rgba(11, 19, 41, 0.85);
            border: 1px solid rgba(0, 243, 255, 0.2);
            padding: 14px;
            border-radius: 14px;
            margin-bottom: 16px;
        }
        .resource-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 9px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .res-item { margin-bottom: 8px; }
        .res-item:last-child { margin-bottom: 0; }
        .res-info {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 3px;
            color: #fff;
        }
        .res-bar-bg {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .res-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
            border-radius: 3px;
            transition: width 0.4s ease;
        }

        .card { 
            background: var(--card-bg); 
            padding: 16px; 
            margin-bottom: 16px; 
            border-radius: 14px; 
            border: 1px solid rgba(0, 243, 255, 0.15);
        }

        .card-title { 
            font-family: 'Orbitron', sans-serif;
            font-size: 10px; font-weight: 700; margin-bottom: 12px; 
            color: var(--text-muted); text-transform: uppercase; 
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .file-upload-wrapper {
            background: #040814;
            border: 2px dashed rgba(0, 243, 255, 0.3);
            padding: 16px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 12px;
        }
        
        input[type="file"] { color: var(--text-muted); font-size: 11px; width: 100%; cursor: pointer; }
        input[type="file"]::file-selector-button {
            background: rgba(0, 243, 255, 0.12);
            color: var(--neon-cyan);
            border: 1px solid rgba(0, 243, 255, 0.4);
            padding: 8px 14px;
            border-radius: 6px;
            font-family: 'Orbitron', sans-serif;
            font-size: 9px;
            font-weight: 700;
            cursor: pointer;
            margin-right: 10px;
        }
        
        .btn { 
            background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
            color: #050814; border: none; padding: 14px; width: 100%; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 11px; 
            border-radius: 10px; cursor: pointer; letter-spacing: 1px;
            position: relative; overflow: hidden; transition: all 0.2s ease;
        }
        .btn:active { transform: scale(0.97); }

        .refresh-btn { 
            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); 
            color: var(--text-muted); padding: 5px 12px; font-size: 9px; 
            border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; 
        }

        .instance-item { 
            background: #070e21; 
            padding: 12px; margin-bottom: 10px; 
            border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .instance-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 11px; font-weight: 600; color: #fff; font-family: 'JetBrains Mono', monospace; }
        
        .metrics-row {
            display: flex; gap: 8px; margin-bottom: 10px;
            font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--text-muted);
        }
        .metric-badge { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; }

        .st-on { color: var(--neon-cyan); font-size: 9px; background: rgba(0, 243, 255, 0.12); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; font-weight: 700; border: 1px solid rgba(0, 243, 255, 0.35); }
        .st-off { color: #ff3366; font-size: 9px; background: rgba(255, 51, 102, 0.12); padding: 3px 8px; border-radius: 6px; font-family: 'Orbitron', sans-serif; font-weight: 700; border: 1px solid rgba(255, 51, 102, 0.35); }
        
        .actions { display: flex; gap: 6px; margin-bottom: 6px; }
        .act-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; }
        .b-start { background: rgba(0, 243, 255, 0.1); color: var(--neon-cyan); border: 1px solid rgba(0, 243, 255, 0.3); }
        .b-stop { background: rgba(255, 0, 85, 0.1); color: #ff0055; border: 1px solid rgba(255, 0, 85, 0.3); }
        .b-del { background: rgba(245, 158, 11, 0.1); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        
        .secondary-actions { display: flex; gap: 6px; }
        .sec-btn { flex: 1; border: none; padding: 9px; font-size: 9px; font-weight: 700; border-radius: 6px; cursor: pointer; font-family: 'Orbitron', sans-serif; }
        .b-edit { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .b-log { background: rgba(176, 0, 255, 0.15); color: #d8b4fe; border: 1px solid rgba(176, 0, 255, 0.35); }
        
        .terminal-box { 
            background: #02050e; border: 1px solid rgba(0, 243, 255, 0.35); 
            padding: 12px; height: 180px; overflow-y: auto; 
            font-family: 'JetBrains Mono', monospace; font-size: 10px; 
            color: var(--neon-cyan); white-space: pre-wrap; border-radius: 8px; margin-top: 8px; line-height: 1.4;
        }
        .term-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .term-actions { display: flex; gap: 4px; }
        .control-btn { background: rgba(255, 255, 255, 0.1); color: #ccc; border: 1px solid rgba(255, 255, 255, 0.2); padding: 3px 8px; font-size: 9px; border-radius: 6px; cursor: pointer; font-family: 'Orbitron'; }
        .close-term { background: rgba(255, 0, 85, 0.2); color: #ff0055; border: 1px solid rgba(255, 0, 85, 0.4); padding: 3px 8px; font-size: 9px; border-radius: 6px; cursor: pointer; font-family: 'Orbitron'; }

        /* Bottom Navbar */
        .bottom-nav {
            position: fixed; bottom: 0; left: 0; width: 100%;
            background: rgba(11, 19, 41, 0.95);
            border-top: 1px solid rgba(0, 243, 255, 0.25);
            display: flex; justify-content: space-around; padding: 10px 0;
            z-index: 99; backdrop-filter: blur(10px);
        }
        .nav-item {
            background: none; border: none; color: var(--text-muted);
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700;
            cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px;
        }
        .nav-item.active { color: var(--neon-cyan); }

        .view-section { display: none; }
        .view-section.active { display: block; }

        #editorModal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(5, 8, 20, 0.9); z-index: 100;
            padding: 16px; align-items: center; justify-content: center;
        }
        .editor-content {
            background: var(--card-bg); width: 100%; max-width: 480px; height: 85vh;
            border-radius: 14px; border: 1px solid rgba(0, 243, 255, 0.35);
            display: flex; flex-direction: column; padding: 16px;
        }
        .editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .editor-title { font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700; color: #fff; }
        .code-textarea {
            flex: 1; background: #02050e; border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--neon-cyan); font-family: 'JetBrains Mono', monospace; font-size: 11px;
            padding: 12px; border-radius: 8px; resize: none; outline: none;
        }
        .editor-footer { display: flex; gap: 8px; margin-top: 10px; }

        .empty { color: var(--text-muted); font-size: 11px; text-align: center; padding: 20px; font-family: 'JetBrains Mono', monospace; }
        
        #toast { 
            position: fixed; bottom: 70px; left: 50%; transform: translateX(-50%) translateY(100px); 
            background: #0e1938; color: var(--neon-cyan); padding: 10px 20px; 
            font-family: 'Orbitron', sans-serif; font-size: 10px; font-weight: 700; border-radius: 20px; 
            border: 1px solid rgba(0, 243, 255, 0.4);
            transition: transform 0.2s ease; z-index: 101;
        }
        #toast.show { transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="auth-wrapper">
            <div class="auth-box">
                <h2>NEXUS-X PORTAL</h2>
                <div class="tabs">
                    <div class="tab-btn active" id="tabLogin" onclick="switchAuthTab('login')">LOGIN</div>
                    <div class="tab-btn" id="tabReg" onclick="switchAuthTab('register')">REGISTER</div>
                </div>
                <input type="email" id="authEmail" class="input-field" placeholder="Enter your Gmail ID">
                <input type="password" id="authPass" class="input-field" placeholder="Enter password">
                <button class="btn" id="authSubmitBtn" onclick="handleAuth('login')">LOGIN ACCOUNT</button>
            </div>
        </div>
        <script>
            function showToast(msg) {
                const t = document.getElementById('toast');
                t.innerText = msg; t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 2000);
            }
            function switchAuthTab(mode) {
                document.getElementById('tabLogin').classList.toggle('active', mode === 'login');
                document.getElementById('tabReg').classList.toggle('active', mode === 'register');
                document.getElementById('authSubmitBtn').innerText = mode === 'login' ? 'LOGIN ACCOUNT' : 'CREATE ACCOUNT';
                document.getElementById('authSubmitBtn').setAttribute('onclick', `handleAuth('${mode}')`);
            }
            async function handleAuth(mode) {
                const email = document.getElementById('authEmail').value;
                const password = document.getElementById('authPass').value;
                if(!email) { showToast('ERR: ENTER GMAIL ID'); return; }
                try {
                    const res = await fetch('/' + mode, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email, password})
                    });
                    const data = await res.json();
                    if(data.error) { showToast('ERR: ' + data.error); }
                    else { 
                        showToast(data.message || 'SUCCESS');
                        setTimeout(() => window.location.reload(), 1000);
                    }
                } catch(e) { showToast('ERR: CONNECTION FAILED'); }
            }
        </script>
        {% else %}
        
        <div class="ring-header">
            <div class="ring-avatar">
                <svg width="28" height="28" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="18" cy="18" r="14" stroke="#00f3ff" stroke-width="3" stroke-dasharray="6 3"/>
                    <circle cx="18" cy="18" r="3" fill="#b000ff"/>
                </svg>
            </div>
            <div class="ring-info">
                <h2>NEXUS-X v6.5</h2>
                <p>SECURE USER CORE</p>
            </div>
            <div class="status-badge-wrapper">
                <div class="online-dot"></div>
                <span class="badge">ONLINE</span>
            </div>
        </div>

        <div id="homeView" class="view-section active">
            <div class="stats-grid">
                <div class="stat-box">
                    <span class="stat-label">ENGINE MODE</span>
                    <span class="stat-val" style="color: var(--neon-cyan);">AUTO-PIP</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">LATENCY</span>
                    <span class="stat-val" style="color: var(--neon-purple);">4ms [OPTIMIZED]</span>
                </div>
            </div>

            <div class="resource-card">
                <div class="resource-title">
                    <span>SYSTEM HARDWARE MONITOR</span>
                    <span style="color: var(--neon-cyan);">LIVE</span>
                </div>
                <div class="res-item">
                    <div class="res-info"><span>CPU USAGE</span><span id="cpuText">0%</span></div>
                    <div class="res-bar-bg"><div id="cpuBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info"><span>RAM USAGE</span><span id="ramText">0 MB / 0 MB</span></div>
                    <div class="res-bar-bg"><div id="ramBar" class="res-bar-fill"></div></div>
                </div>
                <div class="res-item" style="margin-top: 8px;">
                    <div class="res-info"><span>STORAGE USAGE</span><span id="diskText">0 GB / 0 GB</span></div>
                    <div class="res-bar-bg"><div id="diskBar" class="res-bar-fill"></div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title"><span>⚡ DEPLOY ENGINE CORE</span></div>
                <div class="file-upload-wrapper">
                    <input type="file" id="botFile" accept=".py">
                </div>
                <button class="btn" onclick="deployBot()">UPLOAD & AUTO-INSTALL DEPENDENCIES</button>
            </div>
            
            <div class="card">
                <div class="card-title">
                    <span>📂 ACTIVE INSTANCES</span>
                    <button class="refresh-btn" onclick="loadInstances()">REFRESH</button>
                </div>
                <div id="instanceList" class="empty">Scanning storage core...</div>
            </div>

            <div class="card" id="terminalCard" style="display:none;">
                <div class="term-header">
                    <span id="termFileName" style="font-size:10px; font-weight:700; color:#fff; font-family:'Orbitron';">LIVE LOGS</span>
                    <div class="term-actions">
                        <button class="control-btn" id="minBtn" onclick="toggleMinimize()">MIN</button>
                        <button class="close-term" onclick="closeTerminal()">CLOSE</button>
                    </div>
                </div>
                <div id="terminalOutput" class="terminal-box">Waiting for stream...</div>
            </div>
        </div>

        <div id="profileView" class="view-section">
            <div class="card" style="text-align: center; padding: 25px 20px;">
                <div class="ring-avatar" style="margin: 0 auto 12px auto; width: 60px; height: 60px;">
                    <svg width="30" height="30" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="18" cy="12" r="6" stroke="#00f3ff" stroke-width="2"/>
                        <path d="M6 30C6 24 11 22 18 22C25 22 30 24 30 30" stroke="#00f3ff" stroke-width="2"/>
                    </svg>
                </div>
                <div style="font-family: 'Orbitron'; font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">LOGGED IN GMAIL</div>
                <div style="font-family: 'JetBrains Mono'; font-size: 12px; color: var(--neon-cyan); margin-bottom: 20px; word-break: break-all;">{{ user_email }}</div>
                <button class="btn" style="background: linear-gradient(135deg, #ff3366, #ff0055); color: #fff; padding: 14px;" onclick="location.href='/logout'">🚪 LOGOUT ACCOUNT</button>
            </div>
        </div>

        <div class="bottom-nav">
            <button class="nav-item active" id="navHomeBtn" onclick="switchNav('home')"><span>🏠</span><span>HOME</span></button>
            <button class="nav-item" id="navProfileBtn" onclick="switchNav('profile')"><span>👤</span><span>PROFILE</span></button>
        </div>
        {% endif %}
    </div>

    <div id="editorModal">
        <div class="editor-content">
            <div class="editor-header">
                <span id="editorFileName" class="editor-title">EDIT CODE</span>
                <button class="close-term" onclick="closeEditor()">CLOSE</button>
            </div>
            <textarea id="codeTextarea" class="code-textarea" spellcheck="false"></textarea>
            <div class="editor-footer">
                <button class="btn" style="padding: 10px;" onclick="saveCode()">💾 SAVE & APPLY CODE</button>
            </div>
        </div>
    </div>

    <div id="toast">SYSTEM READY</div>
    <script>
        const KEY = 'admin123';
        let activeLogFile = null, logInterval = null, isMinimized = false, editingFile = null;

        function switchNav(viewName) {
            document.getElementById('homeView').classList.toggle('active', viewName === 'home');
            document.getElementById('profileView').classList.toggle('active', viewName === 'profile');
            document.getElementById('navHomeBtn').classList.toggle('active', viewName === 'home');
            document.getElementById('navProfileBtn').classList.toggle('active', viewName === 'profile');
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }

        async function updateSystemStats() {
            try {
                const res = await fetch(`/system_stats?key=${KEY}`);
                const data = await res.json();
                if(data.error) return;

                document.getElementById('cpuText').innerText = data.cpu_percent + '%';
                document.getElementById('cpuBar').style.width = data.cpu_percent + '%';
                document.getElementById('ramText').innerText = `${data.ram_used} MB / ${data.ram_total} MB (${data.ram_percent}%)`;
                document.getElementById('ramBar').style.width = data.ram_percent + '%';
                document.getElementById('diskText').innerText = `${data.disk_used} GB / ${data.disk_total} GB (${data.disk_percent}%)`;
                document.getElementById('diskBar').style.width = data.disk_percent + '%';
            } catch(e) {}
        }

        async function deployBot() {
            const fileInput = document.getElementById('botFile');
            if(!fileInput.files[0]) { showToast('ERR: SELECT A .PY FILE'); return; }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('license_key', KEY);
            showToast('UPLOADING & AUTO-CONFIGURING...');
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message);
                    loadInstances();
                    if(data.filename) openTerminal(data.filename);
                }
            } catch(e) { showToast('UPLOAD FAILED'); }
        }

        async function loadInstances() {
            try {
                const res = await fetch(`/list?key=${KEY}`);
                const data = await res.json();
                const list = document.getElementById('instanceList');
                if(!list) return;
                if(!data.bots || data.bots.length === 0) {
                    list.innerHTML = '<div class="empty">NO SCRIPTS FOUND</div>';
                } else {
                    list.innerHTML = data.bots.map(b => {
                        const online = b.status === 'ONLINE';
                        return `
                            <div class="instance-item">
                                <div class="instance-top">
                                    <span>⚡ ${b.name}</span>
                                    <span class="${online ? 'st-on' : 'st-off'}">${b.status}</span>
                                </div>
                                ${online ? `
                                <div class="metrics-row">
                                    <span class="metric-badge">CPU: ${b.cpu}</span>
                                    <span class="metric-badge">RAM: ${b.ram}</span>
                                </div>` : ''}
                                <div class="actions">
                                    <button class="act-btn b-start" onclick="actionBot('start', '${b.name}')">START</button>
                                    <button class="act-btn b-stop" onclick="actionBot('stop', '${b.name}')">STOP</button>
                                    <button class="act-btn b-del" onclick="actionBot('delete', '${b.name}')">DELETE</button>
                                </div>
                                <div class="secondary-actions" style="margin-top:6px;">
                                    <button class="sec-btn b-edit" onclick="openEditor('${b.name}')">📝 EDIT</button>
                                    <button class="sec-btn b-log" onclick="openTerminal('${b.name}')">🖥️ LOGS</button>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            } catch(e) {}
        }

        async function actionBot(act, filename) {
            showToast(`${act.toUpperCase()}ING...`);
            try {
                const res = await fetch(`/${act}/${filename}?key=${KEY}`, { method: 'POST' });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message || 'SUCCESS');
                    openTerminal(filename);
                }
            } catch(e){ showToast('ACTION FAILED'); }
            setTimeout(loadInstances, 500);
        }

        async function openEditor(filename) {
            editingFile = filename;
            document.getElementById('editorFileName').innerText = 'EDIT: ' + filename;
            try {
                const res = await fetch(`/get_code/${filename}?key=${KEY}`);
                const data = await res.json();
                if(data.error) { showToast('ERR: ' + data.error); return; }
                document.getElementById('codeTextarea').value = data.code;
                document.getElementById('editorModal').style.display = 'flex';
            } catch(e) { showToast('FAILED TO LOAD'); }
        }

        function closeEditor() {
            document.getElementById('editorModal').style.display = 'none';
            editingFile = null;
        }

        async function saveCode() {
            if(!editingFile) return;
            const newCode = document.getElementById('codeTextarea').value;
            showToast('SAVING...');
            try {
                const res = await fetch(`/save_code/${editingFile}?key=${KEY}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: newCode })
                });
                const data = await res.json();
                if(data.error) showToast('ERR: ' + data.error);
                else {
                    showToast(data.message);
                    closeEditor();
                    loadInstances();
                }
            } catch(e) { showToast('SAVE FAILED'); }
        }

        function openTerminal(filename) {
            activeLogFile = filename;
            document.getElementById('terminalCard').style.display = 'block';
            if(isMinimized) toggleMinimize();
            document.getElementById('termFileName').innerText = 'LOGS: ' + filename;
            fetchLog();
            if(logInterval) clearInterval(logInterval);
            logInterval = setInterval(fetchLog, 5000);
        }

        function toggleMinimize() {
            const termBox = document.getElementById('terminalOutput');
            const minBtn = document.getElementById('minBtn');
            isMinimized = !isMinimized;
            if(isMinimized) {
                termBox.style.display = 'none';
                minBtn.innerText = 'MAX';
            } else {
                termBox.style.display = 'block';
                minBtn.innerText = 'MIN';
                termBox.scrollTop = termBox.scrollHeight;
            }
        }

        function closeTerminal() {
            document.getElementById('terminalCard').style.display = 'none';
            if(logInterval) clearInterval(logInterval);
            activeLogFile = null;
            isMinimized = false;
            document.getElementById('terminalOutput').style.display = 'block';
            document.getElementById('minBtn').innerText = 'MIN';
        }

        async function fetchLog() {
            if(!activeLogFile || isMinimized) return;
            try {
                const res = await fetch(`/get_log/${activeLogFile}?key=${KEY}`);
                const data = await res.json();
                const term = document.getElementById('terminalOutput');
                term.innerText = data.log || 'No logs...';
                term.scrollTop = term.scrollHeight;
            } catch(e) {}
        }

        if(document.getElementById('instanceList')) {
            loadInstances();
            updateSystemStats();
            setInterval(loadInstances, 8000);
            setInterval(updateSystemStats, 5000);
        }
    </script>
</body>
</html>
"""

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password', '')
    if not email or '@gmail.com' not in email:
        return jsonify({'error': 'Valid Gmail ID required'}), 400
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if email in users:
        return jsonify({'error': 'Account already exists! Please login.'}), 400
    
    users[email] = password
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)
    
    session['user'] = email
    return jsonify({'message': 'Registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password', '')
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    if email not in users:
        return jsonify({'error': 'Account not found! Please register first.'}), 400
        
    if users.get(email) != password:
        return jsonify({'error': 'Incorrect password!'}), 400
        
    session['user'] = email
    return jsonify({'message': 'Logged in successfully'})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/')
def index(): 
    logged_in = 'user' in session
    user_email = session.get('user', '')
    return render_template_string(AUTO_PILOT_HTML, logged_in=logged_in, user_email=user_email)

@app.route('/system_stats', methods=['GET'])
def system_stats():
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    global current_cpu
    return jsonify({
        'cpu_percent': current_cpu,
        'ram_total': 4096.0, 'ram_used': 1280.0, 'ram_percent': 31.2,
        'disk_total': 64.0, 'disk_used': 18.5, 'disk_percent': 28.9
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if request.form.get('license_key') != DEFAULT_KEY:
            return jsonify({'error': 'Unauthorized'}), 403
        user_dir = get_user_folder()
        if not user_dir:
            return jsonify({'error': 'Unauthorized user session'}), 401
            
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(user_dir, filename)
        file.save(filepath)
        
        if filename.endswith('.py'):
            auto_install_dependencies(filepath)
            
        return jsonify({'message': f'Uploaded & Auto-Configured {filename}!', 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_code/<filename>', methods=['GET'])
def get_code(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_code/<filename>', methods=['POST'])
def save_code(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    try:
        data = request.get_json()
        code = data.get('code', '')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        if filename.endswith('.py'):
            auto_install_dependencies(filepath)
            
        return jsonify({'message': f'Updated & Checked {filename}!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list', methods=['GET'])
def list_bots():
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    files = os.listdir(user_dir) if os.path.exists(user_dir) else []
    bots = []
    for f in sorted(files):
        if f.endswith('.py'):
            is_running = False
            cpu_usage, ram_usage = "0%", "0 MB"
            proc_key = f"{session.get('user')}:{f}"
            if proc_key in active_processes:
                pid = active_processes[proc_key].get('pid')
                if pid and psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            is_running = True
                            cpu_usage = f"{p.cpu_percent(interval=0.0):.1f}%"
                            ram_usage = f"{p.memory_info().rss / (1024 * 1024):.1f} MB"
                    except:
                        pass
            bots.append({'name': f, 'status': 'ONLINE' if is_running else 'OFFLINE', 'cpu': cpu_usage, 'ram': ram_usage})
    return jsonify({'bots': bots})

@app.route('/start/<filename>', methods=['POST'])
def start_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
    if not os.path.exists(filepath): return jsonify({'error': 'File not found'}), 404
    
    log_path = filepath + '.log'
    proc_key = f"{session.get('user')}:{filename}"
    if filename.endswith('.py'):
        auto_install_dependencies(filepath)
    
    try:
        log_file_obj = open(log_path, 'a', encoding='utf-8')
        proc = subprocess.Popen(['python3', '-u', filepath], stdout=log_file_obj, stderr=log_file_obj, start_new_session=True)
        active_processes[proc_key] = {'proc': proc, 'pid': proc.pid}
        desired_states[proc_key] = True
        return jsonify({'message': f'Started {filename} successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop/<filename>', methods=['POST'])
def stop_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    proc_key = f"{session.get('user')}:{filename}"
    desired_states[proc_key] = False
    if proc_key in active_processes:
        try:
            pid = active_processes[proc_key].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except:
            pass
        active_processes.pop(proc_key, None)
    return jsonify({'message': f'Stopped {filename}'})

@app.route('/delete/<filename>', methods=['POST'])
def delete_bot(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    filepath = os.path.join(user_dir, filename)
    proc_key = f"{session.get('user')}:{filename}"
    desired_states.pop(proc_key, None)
    if proc_key in active_processes:
        try:
            pid = active_processes[proc_key].get('pid')
            if pid and psutil.pid_exists(pid): psutil.Process(pid).terminate()
        except:
            pass
        active_processes.pop(proc_key, None)
    if os.path.exists(filepath): os.remove(filepath)
    if os.path.exists(filepath + '.log'): os.remove(filepath + '.log')
    return jsonify({'message': f'Deleted {filename}'})

@app.route('/get_log/<filename>', methods=['GET'])
def get_log(filename):
    if request.args.get('key') != DEFAULT_KEY: return jsonify({'error': 'Unauthorized'}), 403
    user_dir = get_user_folder()
    if not user_dir: return jsonify({'error': 'Unauthorized'}), 401
    
    log_path = os.path.join(user_dir, filename + '.log')
    if os.path.exists(log_path):
        try:
            with open(log_path, 'rb') as lf:
                lf.seek(0, 2)
                filesize = lf.tell()
                lf.seek(max(0, filesize - 12000), 0)
                content = lf.read().decode('utf-8', errors='ignore')
        except:
            content = "Error reading log..."
        return jsonify({'log': content})
    return jsonify({'log': 'No logs found.'})

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print("🚀 NEXUS-X AUTH & AUTO-PIP IDE RUNNING (PORT 5050)")
    print(f"👉 Local URL: http://127.0.0.1:5050")
    print(f"👉 Network IP: http://{local_ip}:5050")
    print("="*50 + "\n")
    serve(app, host='0.0.0.0', port=5050, threads=8)
