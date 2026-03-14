import os
import re
import requests
import time
import xml.etree.ElementTree as ET

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
            "contents": [{"parts": [{"text": f"لخص هذه الوظيفة العراقية كنقاط (نوع الوظيفة، الشركة، المكان، التقديم). إذا لم تكن وظيفة أجب بكلمة 'تجاهل':\n\n{text}"}]}]
        }
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
        return ans if "تجاهل" not in ans else "إهمال"
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

    # المصادر باستخدام جسر RSS (تجاوز حظر تليجرام)
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']

    for src in SOURCES:
        try:
            print(f"📡 سحب البيانات عبر RSS للمصدر: {src}")
            # نستخدم خدمة rsshub أو rss-bridge المفتوحة لتجاوز الحظر
            rss_url = f"https://rsshub.app/telegram/channel/{src}"
            res = requests.get(rss_url, timeout=30)
            
            # قراءة محتوى الـ XML
            root = ET.fromstring(res.text)
            items = root.findall('.//item')

            for item in items[:10]: # فحص آخر 10 منشورات
                title = item.find('title').text if item.find('title') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                
                # دمج العنوان والوصف للحصول على النص الكامل
                full_text = f"{title}\n{description}"
                # تنظيف النص من أكواد HTML
                clean_text = re.sub(r'<[^>]+>', '', full_text).strip()
                
                if len(clean_text) < 50: continue
                
                sig = clean_text[:80]
                if sig in history: continue
                
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ نجاح النشر من {src}")
                    time.sleep(10)
                    break
        except Exception as e:
            print(f"⚠️ المصدر {src} غير متاح حالياً عبر RSS: {e}")

if __name__ == "__main__":
    main()
