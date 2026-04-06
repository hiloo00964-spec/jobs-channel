import os
import requests
import re
import time

# --- الإعدادات (تأكد من وجودها في GitHub Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def smart_clean_with_gemini(text):
    """استخدام جيميناي لتنظيف النص الأصلي بذكاء دون حذفه"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        
        # الأمر الجديد: تنظيف وليس تلخيص
        prompt = (
            "أنت مساعد ذكي لتنظيف إعلانات الوظائف. قم بإعادة صياغة النص التالي مع الالتزام بالقواعد:\n"
            "1. حافظ على النص الأصلي وتفاصيل الوظيفة (المهام، الشروط، الموقع) كما هي دون اختصار.\n"
            "2. احذف فقط روابط القنوات (t.me) ومعرفات القنوات التي تدعو للاشتراك (مثل: تابعنا هنا، اشترك بالقناة).\n"
            "3. اترك معرفات التواصل (مثل @hr) وروابط استمارات التقديم (Google Forms) كما هي.\n"
            "4. إذا كان النص مجرد إعلان لقناة أخرى وليس وظيفة، أجب بكلمة 'إهمال'.\n\n"
            f"النص المراد تنظيفه:\n{text}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        
        if 'candidates' in data:
            cleaned_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return cleaned_text
        return text # في حال فشل جيميناي نرسل النص الأصلي
    except:
        return text

def post_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # تم تفعيل Markdown وتجهيز التوقيع
        final_msg = f"💼 *إعلان وظيفة جديد*\n\n{text}\n\n📍 للمزيد اشترك معنا:\n{CHANNEL_LINK}"
        payload = {'chat_id': MY_CHANNEL, 'text': final_msg, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except: return False

def main():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")
    with open(DB_FILE, 'r', encoding='utf-8') as f: history = f.read().splitlines()

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

    for src in SOURCES:
        try:
            print(f"📡 فحص المصدر: {src}")
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=30)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            for msg_html in reversed(messages[-8:]): # فحص آخر 8 منشورات
                clean_text = re.sub(r'<[^>]+>', '', msg_html.replace('<br/>', '\n').replace('<br>', '\n')).strip()
                
                if len(clean_text) < 50: continue
                
                sig = clean_text[:80] # بصمة أطول لضمان عدم التكرار
                if sig in history: continue
                
                # إرسال النص لجيميناي للتنظيف الذكي
                processed_text = smart_clean_with_gemini(clean_text)
                
                if "إهمال" in processed_text:
                    continue
                
                if post_to_telegram(processed_text):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم نشر المنشور بعد التنظيف من {src}")
                    time.sleep(10) # انتظار بسيط بين المنشورات
                    break 
        except Exception as e:
            print(f"⚠️ خطأ في {src}: {e}")

if __name__ == "__main__":
    main()
