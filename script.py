import os
import re
import requests
import time
from datetime import datetime
import google.generativeai as genai

# --- الإعدادات (Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

# إعداد جيميناي (تصحيح طريقة الاستدعاء)
genai.configure(api_key=GMY_API_KEY)
model = genai.GenerativeModel('gemini-pro') # استخدام النسخة المستقرة Pro

def summarize_with_gemini(text):
    try:
        prompt = f"قم بتلخيص هذه الوظيفة العراقية باختصار (نوع الوظيفة، الشركة، المكان، التقديم) بشكل نقاط. إذا لم تكن وظيفة أكتب كلمة 'تجاهل':\n\n{text}"
        response = model.generate_content(prompt)
        if response.text:
            res = response.text.strip()
            if "تجاهل" in res: return "إهمال"
            return res
        return "إهمال"
    except Exception as e:
        print(f"⚠️ Gemini API Note: {e}")
        return "إهمال"

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

    # تم حذف JobsonIraq من هنا لأنها قناتك
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0'}

    for src in SOURCES:
        try:
            print(f"🔍 فحص مصدر خارجي: {src}")
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=15)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            for msg_html in reversed(messages[-10:]):
                raw_text = re.sub(r'<[^>]+>', '', msg_html).strip()
                if len(raw_text) < 50: continue
                
                sig = raw_text[:80]
                if sig in history: continue
                
                summarized = summarize_with_gemini(raw_text)
                
                if summarized != "إهمال":
                    final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                    if post_to_telegram(final_post):
                        with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                        print(f"✅ تم النشر بنجاح من {src}")
                        time.sleep(10)
                        break 
        except Exception as e:
            print(f"⚠️ خطأ في {src}: {e}")

if __name__ == "__main__":
    main()
