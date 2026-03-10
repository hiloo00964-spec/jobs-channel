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

# إعداد جيميناي مع الموديل الجديد لإنهاء خطأ 404
genai.configure(api_key=GMY_API_KEY)
# استخدمنا 1.5-flash لأنه الأحدث والمستقر حالياً
model = genai.GenerativeModel('gemini-1.5-flash')

# المصادر
SOURCES = ['JobsonIraq', 'iraq_jobs_1', 'vacancies_iraq', 'iraqijobs24']

def summarize_with_gemini(text):
    """تلخيص احترافي وحذف المقدمات والروابط"""
    try:
        prompt = (
            "أنت خبير تلخيص وظائف عراقية. قم بمعالجة النص التالي:\n"
            "1. ابدأ المنشور فوراً بتفاصيل الوظيفة بدون أي مقدمات (امسح عبارة إعلان وظيفة باختصار تماماً).\n"
            "2. إذا كان النص إعلاناً لخدمة وليس وظيفة حقيقية، أجب بكلمة 'إهمال'.\n"
            "3. استخلص فقط: (المهنة، الشركة، المكان، طريقة التقديم).\n"
            "4. احذف أي يوزرات تليجرام أو روابط قنوات أخرى نهائياً.\n"
            "5. أضف هاشتاقات مناسبة في النهاية.\n\n"
            f"النص:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "إهمال"

def clean_job_text(html_text):
    """فلترة الميديا والكلمات الإعلانية"""
    if 'tgme_widget_message_photo' in html_text or 'tgme_widget_message_video' in html_text:
        return ""
    
    blacklist = ["سيفي", "CV", "تصميم", "رصيد", "ممول"]
    for word in blacklist:
        if word in html_text:
            return ""

    text = html_text.replace('</div>', ' ').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<[^>]+>', '', text) 
    return text.strip()

def post_to_telegram(text):
    """إرسال المنشور مع إلغاء معاينة الروابط"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': text, 
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True # إلغاء معاينة الروابط (Preview)
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
                if 'tgme_widget_message_photo' in msg_html or 'tgme_widget_message_video' in msg_html:
                    continue
                
                text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', msg_html, re.DOTALL)
                if not text_match: continue
                
                clean_text = clean_job_text(text_match.group(1))
                if len(clean_text) < 40: continue 
                
                sig = clean_text[:100] 
                if sig in history: continue
                
                all_found_jobs.append({'raw_text': clean_text, 'sig': sig})
        except: continue

    pending_jobs = all_found_jobs[:4]

    for index, job in enumerate(pending_jobs):
        summarized_text = summarize_with_gemini(job['raw_text'])
        
        if "إهمال" in summarized_text or len(summarized_text) < 15:
            continue
        
        final_post = (
            f"{summarized_text}\n\n"
            f"📍 للمزيد اشترك الآن :-\n"
            f"{CHANNEL_LINK}"
        )
        
        if post_to_telegram(final_post):
            with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(job['sig'] + "\n")
            print(f"تم بنجاح نشر الوظيفة {index + 1}")
            time.sleep(10)

if __name__ == "__main__":
    main()
