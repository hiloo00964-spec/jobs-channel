import os
import re
import requests
import time

# --- الإعدادات (استدعاء من Secrets) ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') # تأكد أنه @JobsonIraq
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    """استدعاء جيميناي عبر الرابط المباشر لتجاوز مشاكل الإصدارات والـ 404"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"استخلص معلومات الوظيفة التالية (المهنة، الشركة، المكان، التقديم) بشكل نقاط مختصرة. إذا لم تكن وظيفة حقيقية أجب بكلمة 'تجاهل':\n\n{text}"}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
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
    """إرسال المنشور المنسق للقناة"""
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
    # التأكد من وجود ملف التاريخ
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f: f.write("LOG_START\n")
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        history = f.read().splitlines()

    # المصادر الجديدة التي طلبتها
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    
    # رأس طلب متصفح (User-Agent) حديث لتجنب حظر تليجرام
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for src in SOURCES:
        try:
            print(f"🚀 فحص عميق للمصدر: {src}")
            # تجاوز الكاش للحصول على أحدث المنشورات
            res = requests.get(f"https://t.me/s/{src}?v={int(time.time())}", headers=headers, timeout=25)
            
            # البحث عن نصوص الرسائل باستخدام نمط مرن جداً
            messages = re.findall(r'<div class="[^"]*message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            found_new = False
            for msg_html in reversed(messages[-15:]):
                # تنظيف النص من أكواد HTML
                clean_text = msg_html.replace('<br/>', '\n').replace('<br>', '\n')
                clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                
                # تجاهل المنشورات القصيرة جداً (ليست وظائف غالباً)
                if len(clean_text) < 50: continue
                
                # نظام البصمة لمنع التكرار (أول 80 حرف)
                sig = clean_text[:80]
                if sig in history: continue
                
                # التلخيص عبر الذكاء الاصطناعي
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                # صياغة المنشور النهائي بنفس ميزاتك السابقة
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f:
                        f.write(sig + "\n")
                    print(f"✅ تم بنجاح نشر وظيفة من {src}")
                    found_new = True
                    time.sleep(10) # انتظار لتجنب حظر تليجرام
                    break # نشر وظيفة واحدة من كل مصدر لضمان التنوع
            
            if not found_new:
                print(f"ℹ️ {src}: لا توجد وظائف نصية جديدة تطابق الشروط حالياً.")

        except Exception as e:
            print(f"⚠️ فشل في معالجة المصدر {src}: {e}")

if __name__ == "__main__":
    main()
