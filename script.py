import os
import re
import requests
import time
from datetime import datetime

# --- الإعدادات (Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') # تأكد أنه @JobsonIraq في السكرت
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    """استدعاء مباشر لجيميناي مع تعطيل فلاتر الحماية لضمان الرد"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"لخص هذه الوظيفة العراقية باختصار (نوع الوظيفة، الشركة، المكان، التقديم) بشكل نقاط. إذا لم يكن النص وظيفة (إعلان قناة مثلاً) أجب بكلمة 'تجاهل':\n\n{text}"}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        if 'candidates' in data and 'content' in data['candidates'][0]:
            ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return ans if "تجاهل" not in ans else "إهمال"
        return "إهمال"
    except:
        return "إهمال"

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except:
        return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START_LOG\n")
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        history = f.read().splitlines()

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    # هوية متصفح كاملة لتجنب الحجب
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    for src in SOURCES:
        try:
            print(f"🔍 جاري فحص المصدر: {src}")
            # سحب القناة مع باراميتر زمني لمنع الكاش
            res = requests.get(f"https://t.me/s/{src}?v={int(time.time())}", headers=headers, timeout=25)
            
            # Regex أكثر مرونة للبحث عن أي نص داخل الرسالة
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            if not messages:
                # محاولة ثانية بـ Regex بديل في حال تغير الكود
                messages = re.findall(r'<div class="js-message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)

            found_count = 0
            for msg_html in reversed(messages[-15:]):
                # تنظيف النص بعمق
                clean_text = re.sub(r'<br\s*/?>', '\n', msg_html) # الحفاظ على السطور
                clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                
                if len(clean_text) < 40: continue
                
                # استخدام أول 100 حرف كبصمة فريدة
                sig = clean_text[:100]
                if sig in history: continue
                
                # التلخيص والنشر
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f:
                        f.write(sig + "\n")
                    print(f"✅ تم النشر بنجاح من {src}")
                    found_count += 1
                    time.sleep(10) # تأخير لتجنب السبام
                    break # منشور واحد من كل مصدر في كل دورة
            
            if found_count == 0:
                print(f"ℹ️ {src}: لم يتم العثور على محتوى جديد حالياً.")
                
        except Exception as e:
            print(f"⚠️ فشل الاتصال بالمصدر {src}: {e}")

if __name__ == "__main__":
    main()
