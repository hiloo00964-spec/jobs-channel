import os
import subprocess
import sys

# التثبيت التلقائي للمكتبات
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import requests
except ImportError:
    install('requests')
    import requests

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
        payload = {
            "contents": [{"parts": [{"text": f"لخص هذه الوظيفة العراقية كنقاط مختصرة (المهنة، الشركة، المكان، التقديم). إذا لم تكن وظيفة أكتب 'تجاهل':\n\n{text}"}]}]
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

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    
    # بصمة متصفح ويندوز حديثة جداً لخداع نظام الحماية
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
    }

    for src in SOURCES:
        try:
            print(f"📡 محاولة اختراق حماية المصدر: {src}")
            # إضافة رقم عشوائي للرابط لتجاوز الكاش ومنع تليجرام من تقديم صفحة قديمة/فارغة
            res = requests.get(f"https://t.me/s/{src}?before={int(time.time())}", headers=headers, timeout=30)
            
            # محاولة سحب الرسائل باستخدام 3 أنماط مختلفة (لضمان اللقط)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            if not messages:
                messages = re.findall(r'<div[^>]*dir="auto"[^>]*>(.*?)</div>', res.text, re.DOTALL)
            if not messages:
                messages = re.findall(r'<div class="js-message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)

            found_in_src = 0
            for msg_html in reversed(messages[-15:]):
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
                    print(f"✅ نجاح النشر من {src}")
                    found_in_src += 1
                    time.sleep(10)
                    break 
            
            if found_in_src == 0:
                print(f"ℹ️ {src}: لم يتم العثور على محتوى جديد (تليجرام قد يكون حجب السيرفر).")
        except Exception as e:
            print(f"⚠️ فشل {src}: {e}")

if __name__ == "__main__":
    main()
