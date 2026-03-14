import os
import re
import requests
import time

# --- الإعدادات ---
BOT_TOKEN = os.getenv('TOKNBOT') 
GMY_API_KEY = os.getenv('GMY')
MY_CHANNEL = os.getenv('TARGET_CHANNEL') 
CHANNEL_LINK = os.getenv('MY_CHANNEL_LINK')
DB_FILE = "jobs_history.txt"

def summarize_with_gemini(text):
    """استدعاء مباشر مع توجيهات صارمة بالتلخيص وعدم الرفض"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GMY_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"لخص هذه الوظيفة العراقية كنقاط: (نوع الوظيفة، الشركة، المكان، التقديم). إذا كانت مجرد إعلان لقناة أخرى أجب بكلمة 'تجاهل':\n\n{text}"}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        ans = data['candidates'][0]['content']['parts'][0]['text'].strip()
        return ans if "تجاهل" not in ans else "إهمال"
    except: return "إهمال"

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

    # المصادر الستة
    SOURCES = ['iraq_jobs_1', 'engahmad88', 'J_C_UOT', 'Muhannad_job', 'jobs_for_us', 'YSPjobs']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    for src in SOURCES:
        try:
            print(f"📡 فحص المصدر: {src}")
            res = requests.get(f"https://t.me/s/{src}?v={int(time.time())}", headers=headers, timeout=30)
            
            # استخراج النصوص بنمط أكثر شمولاً
            messages = re.findall(r'<div class="[^"]*message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
            
            published_in_this_src = 0
            for msg_html in reversed(messages[-25:]): # فحص آخر 25 منشور
                clean_text = msg_html.replace('<br/>', '\n').replace('<br>', '\n')
                clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                
                # تجاهل المنشورات القصيرة جداً
                if len(clean_text) < 40: continue
                
                sig = clean_text[:80]
                if sig in history: continue
                
                summarized = summarize_with_gemini(clean_text)
                if summarized == "إهمال": continue
                
                final_post = f"💼 *فرصة عمل جديدة*\n\n{summarized}\n\n📍 للمزيد اشترك الآن :-\n{CHANNEL_LINK}"
                
                if post_to_telegram(final_post):
                    with open(DB_FILE, 'a', encoding='utf-8') as f: f.write(sig + "\n")
                    print(f"✅ تم النشر من {src}")
                    published_in_this_src += 1
                    time.sleep(10)
                    if published_in_this_src >= 2: break # نشر وظيفتين كحد أقصى من كل مصدر لإنعاش القناة
            
            if published_in_this_src == 0:
                print(f"ℹ️ {src}: لم يتم العثور على وظائف نصية جديدة تطابق الفلتر.")
        except Exception as e:
            print(f"⚠️ فشل {src}: {e}")

if __name__ == "__main__":
    main()
