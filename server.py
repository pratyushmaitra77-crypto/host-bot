import os
import socket
import threading
from flask import Flask
from waitress import serve
import telebot

# ==========================================
# ১. Flask অ্যাপ সেটআপ
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is Running Perfectly! ✅"

# ==========================================
# ২. আপনার দেওয়া লোকাল আইপি বের করার ফাংশন
# ==========================================
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

# ==========================================
# ৩. সার্ভার চালু করার ফাংশন (Render + Local Fix)
# ==========================================
def run_web_server():
    local_ip = get_local_ip()
    
    # Render এর জন্য ডাইনামিক পোর্ট, লোকাল পিসিতে 5000
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*40)
    print("🚀 SERVER STARTED!")
    print(f"👉 Local URL: http://127.0.0.1:{port}")
    print(f"👉 Network IP: http://{local_ip}:{port}")
    print("="*40 + "\n")
    
    # Waitress সার্ভার চালু করা হচ্ছে
    serve(app, host='0.0.0.0', port=port, threads=8)

# ==========================================
# ৪. টেলিগ্রাম বট সেটআপ
# ==========================================
# টোকেন অবশ্যই Render এর Environment Variable এ সেট করতে হবে
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("⚠️ ERROR: BOT_TOKEN পাওয়া যায়নি! Render Environment Variables চেক করুন।")
else:
    bot = telebot.TeleBot(BOT_TOKEN)

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Hello! আমি Render সার্ভারে সফলভাবে চলছি। ✅")

# ==========================================
# ৫. মেইন এক্সিকিউশন (বট এবং সার্ভার একসাথে)
# ==========================================
if __name__ == '__main__':
    # ১. ব্যাকগ্রাউন্ডে Flask সার্ভার চালু করা
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # ২. মেইন থ্রেডে টেলিগ্রাম বট চালু করা
    print("🤖 Starting Telegram Bot...")
    if BOT_TOKEN:
        try:
            bot.infinity_polling()
        except KeyboardInterrupt:
            print("Bot stopped.")
