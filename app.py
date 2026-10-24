import streamlit as st
from supabase import create_client
import requests
import os

# Sayfa yapılandırması
st.set_page_config(
    page_title="KnockKnockQR - Kapı Zili",
    page_icon="🚪",
    layout="centered"
)

# Logo Gösterimi
if os.path.exists("logo.png"):
    st.image("logo.png", width=120)

st.title("🚪 KnockKnockQR")

# Supabase Bağlantısı
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Bağlantı ayarı okunamadı: {e}")
    st.stop()

# URL'den QR kodunu al
query_params = st.query_params
qr_code = query_params.get("qr", None)

if not qr_code:
    st.warning("Geçersiz veya eksik QR kodu. Lütfen geçerli bir kapı QR kodunu taratın.")
    st.stop()

# Supabase'den kapı bilgilerini sorgula
try:
    response = supabase.table("doors").select("*").eq("qr_code", qr_code).execute()
    door_data = response.data
except Exception as e:
    st.error(f"Veritabanı sorgulama hatası: {e}")
    st.stop()

if not door_data:
    st.error("Bu QR koda ait kayıt bulunamadı.")
    st.stop()

door = door_data[0]
owner_name = door.get("owner_name", "Ev Sahibi")
custom_status = door.get("custom_status", "Müsait")
chat_id = door.get("telegram_chat_id")

# Kapı / Ev Sahibi Durum Kartı
st.info(f"📌 **Konum / Daire:** {owner_name}")

if custom_status:
    st.warning(f"🔔 **Ev Sahibinin Notu:** {custom_status}")

st.markdown("---")
st.write("Zil çalmak veya ev sahibine mesaj bırakmak için aşağıdaki seçenekleri kullanabilirsiniz:")

# Telegram Bildirim Fonksiyonu
def send_telegram_notification(chat_id, message_text):
    try:
        token = st.secrets["TELEGRAM_BOT_TOKEN"]
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }
        res = requests.post(api_url, json=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        return False

# Ziyaretçi Mesaj Formu
with st.form("visitor_form"):
    visitor_message = st.selectbox(
        "Hızlı Mesaj Seçin:",
        [
            "Kargonuz var, kapıda bekliyor.",
            "Lütfen kapıya bakar mısınız?",
            "Misafiriniz geldi.",
            "Önemli bir teslimat var."
        ]
    )
    custom_note = st.text_input("Veya Özel Notunuz (İsteğe bağlı):")
    
    submitted = st.form_submit_button("🔔 Zili Çal / Mesaj Gönder")
    
    if submitted:
        final_message = custom_note if custom_note else visitor_message
        full_text = f"🚨 *KnockKnockQR Bildirimi!*\n\n📍 *Kapı:* {owner_name}\n💬 *Mesaj:* {final_message}"
        
        # Veritabanına mesajı kaydet
        try:
            supabase.table("messages").insert({
                "qr_code": qr_code,
                "message": final_message
            }).execute()
        except Exception as e:
            pass 

        # Telegram bildirimi gönder
        if chat_id:
            success = send_telegram_notification(chat_id, full_text)
            if success:
                st.success("✅ Mesajınız ev sahibine Telegram üzerinden iletildi!")
            else:
                st.error("❌ Bildirim gönderilemedi, ancak mesajınız kaydedildi.")
        else:
            st.warning("⚠️ Bu kapı için Telegram ID tanımlanmamış, ancak mesaj kaydedildi.")
