import streamlit as st
from supabase import create_client
import requests

# Sayfa yapılandırması
st.set_page_config(page_title="KnockKnockQR", page_icon="🚪", layout="centered")

# Supabase bağlantısı
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# URL'den QR kodunu al (Örn: ?qr=12345)
query_params = st.query_params
qr_code = query_params.get("qr", None)

def send_telegram_notification(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if not qr_code:
    st.error("⚠️ Geçersiz veya eksik QR kodu.")
    st.stop()

# Veritabanından kapı bilgilerini çek
response = supabase.table("doors").select("*").eq("qr_code", qr_code).execute()

if not response.data:
    st.error("❌ Bu QR koda ait kayıt bulunamadı.")
    st.stop()

door = response.data[0]
owner_chat_id = door["owner_chat_id"]
door_label = door["door_label"]
status_message = door["status_message"]

st.title(f"🚪 {door_label}")
st.divider()

# Ev sahibinin anlık durumu varsa göster
if status_message:
    st.info(f"📌 **Ev Sahibinin Notu:** {status_message}")

st.subheader("Ev sahibine hızlıca haber ver:")

# Hazır Butonlar
col1, col2 = st.columns(2)

with col1:
    if st.button("🚪 Kapıdayım / Geldim", use_container_width=True):
        msg = "🚪 Ziyaretçi kapıda: *Kapıdayım / Geldim*"
        supabase.table("messages").insert({"qr_code": qr_code, "message_content": msg}).execute()
        send_telegram_notification(owner_chat_id, f"🔔 *{door_label}* kapısından bildirim:\n\n{msg}")
        st.success("✅ Mesaj ev sahibine iletildi!")

with col2:
    if st.button("📦 Kargo / Paket Bırakıldı", use_container_width=True):
        msg = "📦 Ziyaretçi: *Kargo / Paket Bırakıldı*"
        supabase.table("messages").insert({"qr_code": qr_code, "message_content": msg}).execute()
        send_telegram_notification(owner_chat_id, f"🔔 *{door_label}* kapısından bildirim:\n\n{msg}")
        st.success("✅ Mesaj ev sahibine iletildi!")

if st.button("⚠️ Acil Durum / Ses / Su Sızıntısı", use_container_width=True):
    msg = "⚠️ Ziyaretçi: *Acil Durum / Komşu Bildirimi*"
    supabase.table("messages").insert({"qr_code": qr_code, "message_content": msg}).execute()
    send_telegram_notification(owner_chat_id, f"🚨 *{door_label}* kapısından ACİL bildirim:\n\n{msg}")
    st.success("✅ Acil bildirim ev sahibine iletildi!")

st.divider()

# Özel Mesaj Gönderme
custom_msg = st.text_area("✍️ Özel Mesaj Bırak", placeholder="Örn: 5 dakika içinde döneceğim...")
if st.button("Mesajı Gönder", type="primary"):
    if custom_msg.strip():
        formatted_msg = f"✍️ Özel Mesaj: {custom_msg}"
        supabase.table("messages").insert({"qr_code": qr_code, "message_content": formatted_msg}).execute()
        send_telegram_notification(owner_chat_id, f"🔔 *{door_label}* kapısından yeni mesaj:\n\n{formatted_msg}")
        st.success("✅ Mesajınız iletildi!")
    else:
        st.warning("Lütfen boş bir mesaj göndermeyin.")
