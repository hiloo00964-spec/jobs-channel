import os
import subprocess
import sys

# تثبيت المكتبات المطلوبة
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try: import requests
except: install('requests'); import requests

import re
import time

# --- الإعدادات ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"لخص الوظيفة العراقية (المهنة، الشركة، المكان، التقديم) كنقاط مختصرة. إذا لم تكن وظيفة أكتب 'تجاهل':\n\n{text}"}]}]}
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
        return ans if "تجاهل" not in ans else "إهمال"
    except: return "إهمال"

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        requests.post(url, data=payload)
        return True
    except: return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    
    # نستخدم روابط بديلة لكسر حظر GitHub (روابط الـ Mirror)
    # تليجرام لا يحظر هذه الروابط الوسيطة
    MIRRORS = [
        "https://api.allorigins.win/get?url=https://t.me/s/",
        "https://api.codetabs.com/v1/proxy/?quest=https://t.me/s/"
    ]

    for src in SOURCES:
        try:
            print(f"📡 محاولة كسر الحظر للمصدر: {src}")
            # نحاول عبر الوسيط الأول
            res = requests.get(f"{MIRRORS[0]}{src}", timeout=30)
            page_content = res.json()['contents'] if res.status_code == 200 else ""
            
            # إذا فشل الأول نجرب الثاني
            if not page_content or "tgme_widget_message_text" not in page_content:
                res = requests.get(f"{MIRRORS[1]}{src}", timeout=30)
                page_content = res.text if res.status_code == 200 else ""

            # استخراج الرسائل من المحتوى الذي جلبه "الجسر"
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', page_content, re.DOTALL)
            
            found = False
            for msg_html in reversed(messages[-15:]):
                clean_text = re.sub(r'<[^>]+>', '', msg_html.replace('<br/>', '\n').replace('<br>', '\n')).strip()
                if len(clean_text) < 50: continue
                
                sig = clean_text[:80]
                if sig in history: continue
                
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم كسر الحظر ونشر وظيفة من {src}")
                    found = True
                    break 
            
            if not found: print(f"ℹ️ {src}: لا توجد منشورات جديدة عبر الجسر.")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ فشل الجسر مع {src}: {e}")

if __name__ == "__main__":
    main()
