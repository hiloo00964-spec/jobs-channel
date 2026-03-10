import os
import re
import requests
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# --- الإعدادات (Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

# إعداد جيميناي
genai.configure(api_key=GMY_API_KEY)

def manage_history_file():
    """مسح ملف الذاكرة تلقائياً كل 3 أيام للحفاظ على خفة البوت"""
    if os.path.exists(DB_FILE):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(DB_FILE))
        if file_age > timedelta(days=3):
            os.remove(DB_FILE)
            print("🔄 تم مسح ملف الذاكرة (عبر 3 أيام) لتجديد البيانات.")
    
    if not os.path.exists(DB_FILE):
        open(DB_FILE, 'w', encoding='utf-8').close()

def get_latest_model():
    """اختيار أحدث موديل متاح تلقائياً"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return m
        return models[0] if models else 'models/gemini-1.5-flash'
    except:
        return 'models/gemini-1.5-flash'

SELECTED_MODEL = get_latest_model()
model = genai.GenerativeModel(SELECTED_MODEL)

def summarize_with_gemini(text):
    """تلخيص احترافي - يبدأ بالخبر فوراً ويمسح الحشو"""
    try:
        prompt = (
            "أنت خبير تلخيص وظائف. اتبع القواعد:\n"
            "1. ابدأ بالخبر فوراً (احذف أي مقدمات مثل إعلان وظيفة باختصار).\n"
            "2. إذا كان النص إعلاناً لخدمة (سيفي، رصيد) وليس وظيفة، أجب بكلمة 'إهمال'.\n"
            "3. استخلص فقط: المهنة، الشركة، المكان، التقديم.\n"
            "4. احذف أي يوزرات (@) أو روابط خارجية.\n"
            "5. أضف هاشتاقات مناسبة في النهاية.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return "إهمال"

def post_to_telegram(text):
    """إرسال بدون معاينة روابط"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': text, 
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except:
        return False

def main():
    print(f"🚀 بدء التشغيل باستخدام موديل: {SELECTED_MODEL}")
    manage_history_file()
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        history = f.read().splitlines()

    all_found_jobs = []
    SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']
    
    for src in SOURCES:
        try:
            res = requests.get(f"https://t.me/s/{src}", timeout=10)
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            
            count_new = 0
            for msg_html in reversed(messages):
                if any(x in msg_html for x in ['photo', 'video']): continue
                
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                # تنظيف أولي سريع
                raw_text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                if len(raw_text) < 40: continue
                
                # التحقق من التكرار
                sig = raw_text[:100]
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': raw_text, 'sig': sig})
                count_new += 1
            print(f"✅ تم فحص {src}: وجدنا {count_new} منشورات جديدة.")
        except Exception as e:
            print(f"⚠️ خطأ في سحب {src}: {e}")

    if not all_found_jobs:
        print("ℹ️ لا توجد وظائف جديدة حالياً لنشرها.")
        return

    # نشر آخر 4 وظائف
    for job in all_found_jobs[:4]:
        summarized = summarize_with_gemini(job['raw_text'])
        if "إهمال" in summarized: continue
        
        final_post = f"{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f:
                f.write(job['sig'] + "\n")
            print("📌 تم نشر وظيفة جديدة.")
            time.sleep(15)

if __name__ == "__main__":
    main()
