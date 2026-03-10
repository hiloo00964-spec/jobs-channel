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
    """البحث عن أحدث موديل متوفر لتجنب خطأ 404 وضمان المرونة"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # نفضل فلاش لأنه الأسرع والأكثر توفيراً للحصة (Quota)
        for m in models:
            if '1.5-flash' in m: return m
        return models[0] if models else 'models/gemini-1.5-flash'
    except Exception:
        return 'models/gemini-1.5-flash'

# اختيار الموديل ديناميكياً
SELECTED_MODEL = get_latest_model()
model = genai.GenerativeModel(SELECTED_MODEL)

# المصادر (القنوات التي نسحب منها)
SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']

def summarize_with_gemini(text):
    """تلخيص احترافي: يحذف الحشو والمقدمات واليوزرات"""
    try:
        prompt = (
            "أنت خبير تلخيص وظائف عراقية. قم بمعالجة النص التالي:\n"
            "1. ابدأ المنشور فوراً بتفاصيل الوظيفة (احذف أي مقدمات مثل 'إعلان وظيفة' أو 'إعلان وظيفة باختصار').\n"
            "2. إذا كان النص إعلاناً لخدمة (سيفي، CV، تصميم، رصيد، كارتات) وليس وظيفة حقيقية، أجب بكلمة 'إهمال' فقط.\n"
            "3. استخلص فقط: (المهنة، الشركة، المكان، طريقة التقديم).\n"
            "4. احذف أي يوزرات تليجرام (@) أو روابط قنوات أخرى نهائياً.\n"
            "5. أضف هاشتاقات مناسبة للمحافظة والتخصص في النهاية.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "إهمال"

def clean_job_text(html_text):
    """فلترة الميديا والكلمات الإعلانية قبل المعالجة"""
    # تجاهل الصور والفيديو نهائياً
    if 'tgme_widget_message_photo' in html_text or 'tgme_widget_message_video' in html_text:
        return ""
    
    # قائمة سوداء للكلمات الإعلانية
    blacklist = ["سيفي", "CV", "تصميم", "كارتات", "رصيد", "ممول", "تبادل"]
    for word in blacklist:
        if word in html_text:
            return ""

    # تنظيف الـ HTML
    text = html_text.replace('</div>', ' ').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<[^>]+>', '', text) 
    return text.strip()

def post_to_telegram(text):
    """إرسال المنشور مع إلغاء المعاينة للرابط"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': text, 
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True # إلغاء المعاينة ليكون المنشور أرشق
        }
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except Exception:
        return False

def main():
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    all_found_jobs = []
    for src in SOURCES:
        try:
            res = requests.get(f"https://t.me/s/{src}", timeout=15)
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            
            for msg_html in reversed(messages):
                # فحص الميديا
                if any(x in msg_html for x in ['photo', 'video']): continue
                
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                clean_text = clean_job_text(text_match.group(1))
                if len(clean_text) < 40: continue 
                
                sig = clean_text[:100] 
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': clean_text, 'sig': sig})
        except: continue

    # جلب آخر 4 وظائف جديدة فقط
    pending_jobs = all_found_jobs[:4]

    for index, job in enumerate(pending_jobs):
        summarized_text = summarize_with_gemini(job['raw_text'])
        
        if "إهمال" in summarized_text or len(summarized_text) < 15:
            continue
        
        # الخاتمة الصافية بدون تكرار
        final_post = (
            f"{summarized_text}\n\n"
            f"📍 للمزيد اشترك الآن :-\n"
            f"{CHANNEL_LINK}"
        )
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print(f"تم بنجاح نشر الوظيفة باستخدام {SELECTED_MODEL}")
            time.sleep(15) # انتظار قليلاً بين المنشورات لتجنب الحظر

if __name__ == "__main__":
    main()
