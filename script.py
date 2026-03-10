import os
import re
import requests
import time
import google.generativeai as genai

# --- الإعدادات (Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

# إعداد جيميناي
genai.configure(api_key=GMY_API_KEY)

def get_latest_model():
    """اختيار أحدث موديل متاح في حسابك تلقائياً لضمان المرونة"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return m
        return models[0] if models else 'models/gemini-1.5-flash'
    except:
        return 'models/gemini-1.5-flash'

SELECTED_MODEL = get_latest_model()
model = genai.GenerativeModel(SELECTED_MODEL)

# القنوات المصدر
SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']

def summarize_with_gemini(text):
    """تلخيص احترافي: يحذف الحشو والمقدمات واليوزرات"""
    try:
        prompt = (
            "أنت خبير تلخيص وظائف. قم بمعالجة النص التالي:\n"
            "1. ابدأ بالخبر فوراً (احذف أي مقدمات مثل 'إعلان وظيفة باختصار').\n"
            "2. إذا كان النص إعلان خدمة (سيفي، CV، رصيد) وليس وظيفة، أجب بكلمة 'إهمال'.\n"
            "3. استخلص فقط: المهنة، الشركة، المكان، طريقة التقديم.\n"
            "4. احذف أي يوزرات (@) أو روابط خارجية نهائياً.\n"
            "5. أضف هاشتاقات مناسبة في النهاية.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "إهمال"

def clean_job_text(html_text):
    """فلترة الميديا والكلمات الإعلانية"""
    if any(x in html_text for x in ['photo', 'video']): return ""
    
    blacklist = ["سيفي", "CV", "رصيد", "ممول", "تبادل"]
    for word in blacklist:
        if word in html_text: return ""

    text = html_text.replace('</div>', ' ').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<[^>]+>', '', text) 
    return text.strip()

def post_to_telegram(text):
    """إرسال المنشور بدون معاينة الروابط"""
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
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    all_found_jobs = []
    for src in SOURCES:
        try:
            res = requests.get(f"https://t.me/s/{src}", timeout=10)
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            for msg_html in reversed(messages):
                if any(x in msg_html for x in ['photo', 'video']): continue
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                clean_text = clean_job_text(text_match.group(1))
                if len(clean_text) < 40: continue 
                sig = clean_text[:100]
                if sig in history: continue
                all_found_jobs.append({'raw_text': clean_text, 'sig': sig})
        except: continue

    # نشر آخر 4 وظائف جديدة فقط
    for index, job in enumerate(all_found_jobs[:4]):
        summarized_text = summarize_with_gemini(job['raw_text'])
        if "إهمال" in summarized_text: continue
        
        final_post = f"{summarized_text}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print(f"تم النشر باستخدام {SELECTED_MODEL}")
            time.sleep(15)

if __name__ == "__main__":
    main()
