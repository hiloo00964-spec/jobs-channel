import os
import re
import requests
import time
from datetime import datetime

# --- الإعدادات (Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    """استدعاء جيميناي عبر الرابط المباشر لضمان العمل 100%"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"لخص هذه الوظيفة العراقية باختصار (نوع الوظيفة، الشركة، المكان، التقديم) بشكل نقاط. إذا لم تكن وظيفة أكتب 'تجاهل':\n\n{text}"
                }]
            }]
        }
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        if 'candidates' in data:
            ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return ans if "تجاهل" not in ans else "إهمال"
        return "إهمال"
    except:
        return "إهمال"

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        requests.post(url, data=payload)
        return True
    except:
        return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    # المصادر المطلوبة
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for src in SOURCES:
        try:
            print(f"🔍 فحص مصدر خارجي: {src}")
            # إضافة رقم عشوائي للرابط لتجاوز الكاش
            res = requests.get(f"https://t.me/s/{src}?v={int(time.time())}", headers=headers, timeout=20)
            
            # استخراج النصوص بطريقة أكثر مرونة (البحث عن أي نص داخل حاوية الرسالة)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            found_in_src = 0
            for msg_html in reversed(messages[-15:]): # فحص آخر 15 رسالة
                # تنظيف النص من كل وسوم HTML والروابط
                raw_text = re.sub(r'<[^>]+>', '', msg_html).strip()
                raw_text = re.sub(r'http\S+', '', raw_text) # حذف الروابط لزيادة دقة الفحص
                
                if len(raw_text) < 40: continue
                
                # بصمة المنشور (أول 60 حرف)
                sig = raw_text[:60]
                if sig in history: continue
                
                # التلخيص
                summarized = summarize_with_gemini(raw_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم نشر وظيفة من: {src}")
                    found_in_src += 1
                    time.sleep(10)
                    break # منشور واحد من كل قناة بكل دورة
            
            if found_in_src == 0:
                print(f"ℹ️ {src}: لا توجد منشورات نصية مطابقة حالياً.")

        except Exception as e:
            print(f"⚠️ فشل فحص {src}: {e}")

if __name__ == "__main__":
    main()
