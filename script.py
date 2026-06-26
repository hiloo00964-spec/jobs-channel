import os
import requests
import re
import time
from datetime import datetime

# الإعدادات المسحوبة من GitHub Secrets
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def is_work_time():
    """فحص وقت العمل بتوقيت العراق (UTC+3) من 9 صباحاً إلى 11 مساءً"""
    current_hour = (datetime.utcnow().hour + 3) % 24
    return 9 <= current_hour <= 23

def smart_clean_with_gemini(text):
    """تنظيف ذكي للإعلانات باستخدام جيميناي بالإصدار المستقر v1"""
    try:
        # تحديث الرابط للإصدار المستقر v1 لحل مشكلة الـ 404
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        prompt = (
            "أنت مساعد ذكي لتنظيف إعلانات الوظائف. قم بإعادة صياغة النص التالي مع الالتزام بالقواعد:\n"
            "1. حافظ على النص الأصلي وتفاصيل الوظيفة (المهام، الشروط، الموقع) كما هي دون اختصار.\n"
            "2. احذف فقط روابط القنوات (t.me) ومعرفات القنوات التي تدعو للاشتراك.\n"
            "3. اترك معرفات التواصل (مثل @hr) وروابط استمارات التقديم كما هي.\n"
            "4. إذا كان النص مجرد إعلان لقناة وليس وظيفة، أجب بكلمة 'إهمال'.\n\n"
            f"النص المراد تنظيفه:\n{text}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"⚠️ جيميناي أرجع استجابة غير متوقعة: {data}")
            return text 
    except Exception as e: 
        print(f"⚠️ خطأ أثناء الاتصال بجيميناي: {e}")
        return text

def post_to_telegram(text):
    """نشر الوظيفة في قناة التليجرام مع محاولة الإرسال الآمن"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        final_msg = f"💼 *إعلان وظيفة جديد*\n\n{text}\n\n📍 للمزيد اشترك معنا:\n{CHANNEL_LINK}"
        payload = {
            'chat_id': MY_CHANNEL, 
            'text': final_msg, 
            'parse_mode': 'Markdown', 
            'disable_web_page_preview': True
        }
        r = requests.post(url, data=payload, timeout=15)
        
        if r.status_code == 200:
            return True
            
        # حل ذكي: إذا رفض التليجرام النص بسبب علامات الماركداون، نرسله فوراً كنص عادي
        if "can't parse entities" in r.text:
            print("⚠️ مشكلة في رموز التنسيق، جاري إعادة المحاولة بنص عادي...")
            payload.pop('parse_mode', None) # إزالة التنسيق المعقد
            r = requests.post(url, data=payload, timeout=15)
            if r.status_code == 200:
                return True
                
        print(f"❌ فشل إرسال التليجرام: كود الخطأ {r.status_code} - التفاصيل: {r.text}")
        return False
    except Exception as e: 
        print(f"⚠️ خطأ اتصال بسيرفر التليجرام: {e}")
        return False

def main():
    if not is_work_time():
        print("🌙 خارج وقت العمل المحدد (9 صباحاً - 11 مساءً بتوقيت العراق). تم إيقاف الدورة لحفظ الجهد.")
        return

    print(f"🚀 بدء عملية فحص الوظائف: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("START\n")

    with open(DB_FILE, 'r', encoding='utf-8') as f: 
        history = f.read().splitlines()

    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0'}

    for src in SOURCES:
        try:
            print(f"📡 فحص المصدر: @{src}")
            res = requests.get(f"https://t.me/s/{src}", headers=headers, timeout=30)
            messages = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            for msg_html in reversed(messages[-8:]):
                clean_text = re.sub(r'<[^>]+>', '', msg_html.replace('<br/>', '\n').replace('<br>', '\n')).strip()
                if len(clean_text) < 50: continue
                
                sig = clean_text[:80]
                if sig in history: continue
                
                print(f"✨ معالجة وظيفة جديدة من {src}...")
                processed_text = smart_clean_with_gemini(clean_text)
                
                if "إهمال" in processed_text:
                    print(f"🗑️ جيميناي حدد هذا المنشور كـ 'إهمال' (إعلان وليس وظيفة).")
                    continue
                
                if post_to_telegram(processed_text):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم النشر بنجاح.")
                    time.sleep(5)
                    break 
                else:
                    print(f"⏭️ فشل النشر الحالي، جاري الانتقال للمنشور التالي...")
        except Exception as e:
            print(f"⚠️ خطأ في {src}: {e}")

    print("🏁 انتهت العملية.")

if __name__ == "__main__":
    main()
