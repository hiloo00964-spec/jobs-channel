import os
import re
import requests
import time
import random
import google.generativeai as genai

# --- الإعدادات ---
# تم التعديل ليقرأ من التوكنات الموجودة في إعداداتك (Secrets)
MY_CHANNEL = os.getenv('TARGET_CHANNEL', '@JobsonIraq') 
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
DB_FILE = "jobs_history.txt"

# إعداد جيميناي للتلخيص
genai.configure(api_key=GMY_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# المصادر
SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']

def summarize_with_gemini(text):
    """تلخيص النص وحذف الحشو باستخدام جيميناي"""
    try:
        prompt = f"قم بتلخيص نص الوظيفة التالي باختصار شديد (نقاط واضحة: المهنة، الشركة، المكان، طريقة التقديم) واحذف أي كلام زائد أو إعلانات للقنوات الأخرى:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return text # في حال فشل جيميناي يعود النص الأصلي

def clean_job_text(html_text):
    # فلترة: إذا كان المنشور يحتوي على صورة أو فيديو (داخل الـ HTML الخاص بتليجرام) نرجعه فارغاً ليتم تجاهله
    if 'tgme_widget_message_photo' in html_text or 'tgme_widget_message_video' in html_text:
        return ""
    
    # تنظيف النصوص
    text = html_text.replace('</div>', ' ').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<[^>]+>', '', text) # حذف أي وسم HTML متبقي
    
    # حذف الروابط والهاشتاقات القديمة لضمان نظافة النص قبل التلخيص
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    
    return text.strip()

def post_to_telegram(text):
    try:
        if not BOT_TOKEN:
            print("خطأ: TOKNBOT فارغ!")
            return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': text, 
            'parse_mode': 'Markdown', # جيميناي غالباً يعطي تنسيق Markdown
            'disable_web_page_preview': True
        }
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram Post Error: {e}")
        return False

def main():
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    all_found_jobs = []
    for src in SOURCES:
        try:
            # نسحب الصفحة كاملة للتحقق من وجود ميديا (صور/فيديو)
            res = requests.get(f"https://t.me/s/{src}", timeout=15)
            # استخراج كتل الرسائل كاملة
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            
            for msg_html in reversed(messages):
                # فحص الميديا: إذا وجدنا وسم صورة أو فيديو نتخطى الرسالة فوراً
                if 'tgme_widget_message_photo' in msg_html or 'tgme_widget_message_video' in msg_html:
                    continue
                
                # استخراج النص فقط من داخل الرسالة
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                clean_text = clean_job_text(text_match.group(1))
                if len(clean_text) < 40: continue # وظائف حقيقية وليست مجرد كلمات
                
                sig = clean_text[:100] # بصمة المنشور لمنع التكرار
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': clean_text, 'sig': sig})
        except: continue

    # التعديل: نأخذ فقط آخر 4 منشورات نصية جديدة
    pending_jobs = all_found_jobs[:4]

    for index, job in enumerate(pending_jobs):
        # تلخيص النص عن طريق جيميناي
        summarized_text = summarize_with_gemini(job['raw_text'])
        
        final_post = f"{summarized_text}\n\n✅ للاشتراك:\n{MY_CHANNEL}"
        
        success = post_to_telegram(final_post)
        if success:
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print(f"تم نشر الوظيفة {index + 1} بنجاح.")
            # فاصل بسيط بين المنشورات (10 ثواني) للحفاظ على الترتيب وتوفير الدقائق
            if index < len(pending_jobs) - 1:
                time.sleep(10)
        else:
            print("فشل النشر.")

if __name__ == "__main__":
    main()
