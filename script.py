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
    if os.path.exists(DB_FILE):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(DB_FILE))
        if file_age > timedelta(days=3):
            os.remove(DB_FILE)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("INIT\n")

def get_latest_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return m
        return 'models/gemini-1.5-flash'
    except: return 'models/gemini-1.5-flash'

SELECTED_MODEL = get_latest_model()
model = genai.GenerativeModel(SELECTED_MODEL)

def summarize_with_gemini(text):
    try:
        prompt = (
            "أنت خبير تلخيص وظائف عراقي. استخلص فقط المعلومات التالية بشكل نقاط:\n"
            "- نوع الوظيفة\n- اسم الشركة أو الجهة\n- موقع العمل\n- طريقة التقديم\n"
            "احذف أي روابط خارجية أو معرفات قنوات أخرى. إذا كان النص ليس وظيفة، أجب بكلمة 'إهمال'.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        return res_text if "إهمال" not in res_text else "إهمال"
    except: return "إهمال"

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except: return False

def main():
    if not is_work_time(): return
    manage_history_file()
    
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    all_found_jobs = []
    # قنوات المصدر - تأكد من صحة المعرفات
    SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24', 'Iraqi_jobs']
    
    # رأس HTTP للتظاهر بأننا متصفح حقيقي لتجنب حجب تليجرام
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for src in SOURCES:
        try:
            print(f"🔍 فحص مصدر الوظائف: {src}")
            # أضفنا سطر عشوائي للرابط لتجنب الكاش (Cache) الخاص بتليجرام
            res = requests.get(f"https://t.me/s/{src}?before={int(time.time())}", headers=headers, timeout=20)
            
            # استخراج محتوى الرسائل بشكل أوسع
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            count_new = 0
            for msg_html in reversed(messages[-15:]): # فحص آخر 15 رسالة
                # تنظيف النص
                raw_text = re.sub(r'<[^>]+>', '', msg_html).strip()
                
                # تجاهل المنشورات القصيرة جداً (ليست وظائف غالباً)
                if len(raw_text) < 50: continue
                
                # التحقق من التكرار
                sig = raw_text[:100]
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': raw_text, 'sig': sig})
                count_new += 1
            print(f"✅ {src}: وجدنا {count_new} منشورات محتملة.")
        except Exception as e:
            print(f"⚠️ خطأ في سحب {src}: {e}")

    if not all_found_jobs:
        print("ℹ️ لم يتم العثور على أي منشورات نصية جديدة تطابق الشروط.")
        return

    # النشر
    for job in all_found_jobs[:4]: # نشر 4 وظائف في كل دورة كحد أقصى
        summarized = summarize_with_gemini(job['raw_text'])
        if summarized == "إهمال": continue
        
        final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print("📌 تم نشر وظيفة بنجاح.")
            time.sleep(10)

if __name__ == "__main__":
    main()
