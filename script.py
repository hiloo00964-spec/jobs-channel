import os
import subprocess
import sys

# تثبيت المكتبات المطلوبة تلقائياً
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try: import requests
except: install('requests'); import requests

import re
import time

# --- الإعدادات ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    """تلخيص مَرن جداً ولا يرفض المنشورات إلا إذا كانت فارغة"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        # طلب تلخيص بسيط بدون شروط "تجاهل" معقدة
        prompt = f"قم بتنظيم هذا النص كإعلان وظيفة مختصر باللغة العربية مع إيموجيات مناسبة. حافظ على المعلومات المهمة:\n\n{text}"
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        return text[:300] # إذا فشل جيميناي، ارجع النص الأصلي مقصوصاً
    except:
        return text[:300]

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': MY_CHANNEL, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except: return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    for src in SOURCES:
        try:
            print(f"📡 فحص المصدر: {src}")
            # محاولة الدخول المباشر (مثل بوت الأخبار)
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=30)
            
            # البحث عن النصوص بأكثر من نمط
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            if not messages:
                messages = re.findall(r'<div[^>]*dir="auto"[^>]*>(.*?)</div>', res.text, re.DOTALL)

            for msg_html in reversed(messages[-10:]): # فحص آخر 10 منشورات
                clean_text = re.sub(r'<[^>]+>', '', msg_html.replace('<br/>', '\n').replace('<br>', '\n')).strip()
                
                # تقليل الحد الأدنى للنص (حتى لو نص قصير يسحبه)
                if len(clean_text) < 30: continue
                
                sig = clean_text[:50] # بصمة قصيرة للمقارنة
                if sig in history: continue
                
                # التلخيص صار مَرن (ينظم النص فقط ولا يحذفه)
                summarized = summarize_with_gemini(clean_text)
                
                final_post = f"💼 *إعلان جديد*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم النشر من {src}")
                    time.sleep(5)
                    break # نشر منشور واحد من كل قناة بكل دورة
        except Exception as e:
            print(f"⚠️ فشل {src}: {e}")

if __name__ == "__main__":
    main()
