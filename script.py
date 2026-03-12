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

# إعداد جيميناي بأحدث طريقة
genai.configure(api_key=GMY_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def summarize_with_gemini(text):
    try:
        # برومبت (Prompt) بسيط ومباشر لتجنب الرفض التقني
        prompt = f"قم بتلخيص هذه الوظيفة العراقية باختصار (نوع الوظيفة، الشركة، المكان، التقديم) بشكل نقاط واضحة. إذا لم تكن وظيفة أكتب كلمة 'تجاهل' فقط:\n\n{text}"
        response = model.generate_content(prompt)
        # التأكد من استلام نص سليم
        if response and response.text:
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
    # التأكد من وجود ملف التاريخ
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24', 'Iraqi_jobs']
    headers = {'User-Agent': 'Mozilla/5.0'}

    for src in SOURCES:
        try:
            print(f"🔍 فحص: {src}")
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=15)
            # استخراج النصوص فقط
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            for msg_html in reversed(messages[-10:]):
                raw_text = re.sub(r'<[^>]+>', '', msg_html).strip()
                if len(raw_text) < 50: continue
                
                sig = raw_text[:80] # بصمة المنشور
                if sig in history: continue
                
                # إرسال للذكاء الاصطناعي للتلخيص
                summarized = summarize_with_gemini(raw_text)
                
                if summarized != "إهمال":
                    final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                    if post_to_telegram(final_post):
                        with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                        print(f"✅ تم نشر وظيفة من {src}")
                        time.sleep(10)
                        break # نشر وظيفة واحدة من كل مصدر في الدورة الواحدة لتجنب الحظر
        except Exception as e:
            print(f"⚠️ خطأ في {src}: {e}")

if __name__ == "__main__":
    main()
