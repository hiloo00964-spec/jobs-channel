import os
import re
import requests
import time
import google.generativeai as genai

# --- الإعدادات (مطابقة تماماً للصورة اللي دزيتها) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

# إعداد جيميناي للتلخيص وحذف الحشو
genai.configure(api_key=GMY_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# المصادر
SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']

def summarize_with_gemini(text):
    """تلخيص النص وحذف الحشو مع الحفاظ على المعلومات الأساسية"""
    try:
        prompt = (
            "قم بتلخيص نص الوظيفة التالي باختصار شديد جداً. استخرج فقط: (المهنة، الشركة، المكان، وطريقة التقديم). "
            "احذف أي روابط خارجية أو إعلانات للقنوات. "
            "أضف هاشتاقات مناسبة للمحافظة والتخصص في النهاية:\n\n"
            f"{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return text

def clean_job_text(html_text):
    """فلترة الصور والفيديو وتنظيف النصوص"""
    # إذا كان المنشور يحتوي على صورة أو فيديو يتم تجاهله فوراً حسب الاتفاق
    if 'tgme_widget_message_photo' in html_text or 'tgme_widget_message_video' in html_text:
        return ""
    
    # تنظيف الـ HTML
    text = html_text.replace('</div>', ' ').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<[^>]+>', '', text) 
    
    # حذف الهاشتاقات والروابط القديمة قبل التلخيص
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    
    return text.strip()

def post_to_telegram(text):
    """إرسال المنشور النهائي إلى قناتك"""
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
    except Exception as e:
        print(f"Telegram Post Error: {e}")
        return False

def main():
    if not os.path.exists(DB_FILE): open(DB_FILE, 'w').close()
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    all_found_jobs = []
    for src in SOURCES:
        try:
            res = requests.get(f"https://t.me/s/{src}", timeout=15)
            # استخراج كتل الرسائل بالكامل لفحص وجود ميديا
            messages = re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)<div class="tgme_widget_message_footer', res.text, re.DOTALL)
            
            for msg_html in reversed(messages):
                # فحص الميديا (صور/فيديو)
                if 'tgme_widget_message_photo' in msg_html or 'tgme_widget_message_video' in msg_html:
                    continue
                
                # استخراج النص
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                clean_text = clean_job_text(text_match.group(1))
                if len(clean_text) < 40: continue 
                
                sig = clean_text[:100] 
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': clean_text, 'sig': sig})
        except: continue

    # نأخذ فقط آخر 4 وظائف نصية جديدة بكل جولة
    pending_jobs = all_found_jobs[:4]

    for index, job in enumerate(pending_jobs):
        summarized_text = summarize_with_gemini(job['raw_text'])
        
        # التنسيق النهائي مع رابط القناة من السيركت
        final_post = (
            f"{summarized_text}\n\n"
            f"📍 للمزيد اشترك الآن :-\n"
            f"{CHANNEL_LINK}"
        )
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print(f"تم نشر الوظيفة {index + 1} بنجاح.")
            time.sleep(10) # فاصل زمني بسيط
        else:
            print("فشل في النشر.")

if __name__ == "__main__":
    main()
