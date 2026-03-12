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

def is_work_time():
    """توقيت العراق (GMT+3)"""
    current_hour = (datetime.utcnow().hour + 3) % 24
    return 8 <= current_hour < 23

def manage_history_file():
    """تجهيز وإدارة ملف الذاكرة"""
    if os.path.exists(DB_FILE):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(DB_FILE))
        if file_age > timedelta(days=3):
            os.remove(DB_FILE)
            print("🔄 تم تجديد ملف الذاكرة.")
    
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            f.write("INIT_LOG\n")

def get_latest_model():
    """اختيار أحدث موديل متاح تلقائياً"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return m
        return 'models/gemini-1.5-flash'
    except:
        return 'models/gemini-1.5-flash'

SELECTED_MODEL = get_latest_model()
model = genai.GenerativeModel(SELECTED_MODEL)

def summarize_with_gemini(text):
    """تلخيص احترافي باستخدام جيميناي"""
    try:
        prompt = (
            "أنت خبير تلخيص وظائف عراقي. اتبع القواعد:\n"
            "1. ابدأ بالخبر فوراً (مثلاً: تعلن شركة... عن حاجتها لـ...).\n"
            "2. إذا كان النص ليس وظيفة (إعلان قناة، بيع رصيد، عمل سيفي)، أجب بكلمة 'إهمال'.\n"
            "3. استخلص: المهنة، الشركة، المكان، التقديم.\n"
            "4. احذف أي معرفات (@) أو روابط خارجية للمصادر.\n"
            "5. أضف هاشتاقات: #وظائف_العراق #تعيينات #قطاع_خاص.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        return res_text if len(res_text) > 10 else "إهمال"
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return "إهمال"

def post_to_telegram(text):
    """إرسال مع تقرير بالخطأ في حال الفشل"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': text, 
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        r = requests.post(url, data=payload)
        res_data = r.json()
        if r.status_code == 200:
            print("✅ Telegram: تم نشر الوظيفة.")
            return True
        else:
            print(f"❌ Telegram Fail: {res_data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Telegram Critical Error: {e}")
        return False

def main():
    if not is_work_time():
        print(f"🌙 البوت في استراحة (وقت العراق: {(datetime.utcnow().hour + 3) % 24}:00)")
        return

    print(f"🚀 بدء التشغيل بموديل: {SELECTED_MODEL}")
    manage_history_file()
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        history = f.read().splitlines()

    all_found_jobs = []
    SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']
    
    for src in SOURCES:
        try:
            print(f"🔍 فحص مصدر الوظائف: {src}")
            res = requests.get(f"https://t.me/s/{src}", timeout=15)
            # Regex محسن لاستخراج الرسائل النصية فقط وتجنب الميديا
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            
            count_new = 0
            for msg_html in reversed(messages[-10:]): # فحص آخر 10 رسائل من كل مصدر
                # شرط النصوص الصافية: استبعاد أي منشور فيه صورة أو فيديو
                if any(x in msg_html for x in ['photo', 'video', 'video_player']): continue
                
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                # تنظيف النص من وسوم HTML
                raw_text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                if len(raw_text) < 40: continue
                
                sig = raw_text[:100]
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': raw_text, 'sig': sig})
                count_new += 1
            print(f"✅ {src}: وجدنا {count_new} منشورات نصية جديدة.")
        except Exception as e:
            print(f"⚠️ خطأ في سحب {src}: {e}")

    if not all_found_jobs:
        print("ℹ️ لا توجد وظائف جديدة تطابق الشروط حالياً.")
        return

    # نشر الوظائف الجديدة بعد تلخيصها (بحد أقصى 5 في المرة الواحدة)
    for job in all_found_jobs[:5]:
        summarized = summarize_with_gemini(job['raw_text'])
        
        if "إهمال" in summarized or len(summarized) < 20:
            print("⏭️ تم إهمال المنشور (إعلان أو محتوى غير مناسب).")
            continue
        
        final_post = f"{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f:
                f.write(job['sig'] + "\n")
            time.sleep(15) # تأخير بين المنشورات

if __name__ == "__main__":
    main()
