import os
import subprocess
import sys

# تثبيت المكتبات المطلوبة تلقائياً
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import requests
except ImportError:
    install('requests')
    import requests

import re
import time

# --- الإعدادات (تأكد من وجودها في Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"أنت خبير توظيف عراقي. لخص الوظيفة التالية (المهنة، الشركة، الموقع، طريقة التقديم) كنقاط مختصرة. إذا لم تكن وظيفة اكتب 'تجاهل':\n\n{text}"}]}]
        }
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        if 'candidates' in data:
            ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return ans if "تجاهل" not in ans else "إهمال"
        return "إهمال"
    except: return "إهمال"

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except: return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    # المصادر الستة
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    
    # رأس طلب متصفح حقيقي (بصمة متصفح أندرويد)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Mobile Safari/537.36'
    }

    for src in SOURCES:
        try:
            print(f"📡 فحص المصدر: {src}")
            # السحب من نسخة الـ RSS المباشرة لتليجرام أو صفحة الويب المبسطة
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=30)
            
            # استخراج النصوص بنمط "القبض العام" (سحب أي نص يقع بين الأوسمة)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            if not messages:
                print(f"ℹ️ {src}: لم تظهر نصوص، جاري تجربة النمط البديل..")
                messages = re.findall(r'<div[^>]*dir="auto"[^>]*>(.*?)</div>', res.text, re.DOTALL)

            for msg_html in reversed(messages[-15:]):
                # تنظيف النص وتحويل <br> لأسطر
                clean_text = msg_html.replace('<br/>', '\n').replace('<br>', '\n')
                clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                
                if len(clean_text) < 50: continue
                
                sig = clean_text[:80]
                if sig in history: continue
                
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم بنجاح النشر من {src}")
                    time.sleep(10)
                    break 
        except Exception as e:
            print(f"⚠️ فشل {src}: {e}")

if __name__ == "__main__":
    main()
