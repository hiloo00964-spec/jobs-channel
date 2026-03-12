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

def summarize_with_gemini(text):
    """استدعاء جيميناي عبر رابط مباشر لتجنب خطأ 404 وضمان التلخيص"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"أنت خبير تعيينات عراقي. لخص النص التالي كنقاط (نوع الوظيفة، الشركة، الموقع، التقديم). إذا لم يكن المنشور وظيفة (مثل إعلان قناة أو نصيحة) أجب بكلمة 'تجاهل' فقط:\n\n{text}"
                }]
            }]
        }
        res = requests.post(url, json=payload, timeout=20)
        data = res.json()
        
        # استخراج النص من الاستجابة
        if 'candidates' in data and data['candidates']:
            output = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return output if "تجاهل" not in output else "إهمال"
        return "إهمال"
    except Exception as e:
        print(f"⚠️ تنبيه الذكاء الاصطناعي: {e}")
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

    # المصادر الجديدة التي طلبتها
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for src in SOURCES:
        try:
            print(f"🔍 فحص مصدر خارجي: {src}")
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=15)
            # استخراج محتوى الرسائل النصية
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            count_found = 0
            for msg_html in reversed(messages[-12:]):
                # تنظيف النص من وسوم HTML
                raw_text = re.sub(r'<[^>]+>', '', msg_html).strip()
                if len(raw_text) < 50: continue
                
                # منع التكرار (استخدام أول 80 حرف كبصمة)
                sig = raw_text[:80]
                if sig in history: continue
                
                # التلخيص بواسطة جيميناي
                summarized = summarize_with_gemini(raw_text)
                
                if summarized != "إهمال" and len(summarized) > 15:
                    final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                    if post_to_telegram(final_post):
                        with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                        print(f"✅ تم النشر بنجاح من {src}")
                        count_found += 1
                        time.sleep(12)
                        break # نشر وظيفة واحدة من كل مصدر لضمان التنوع
            if count_found == 0:
                print(f"ℹ️ {src}: لا توجد وظائف نصية جديدة.")
        except Exception as e:
            print(f"⚠️ خطأ في {src}: {e}")

if __name__ == "__main__":
    main()
