import streamlit as st
from supabase import create_client
import requests
import os
import qrcode
from io import BytesIO

# Sayfa yapılandırması
st.set_page_config(
    page_title="KnockKnockQR - Akıllı Kapı Zili",
    page_icon="🚪",
    layout="centered"
)

# Supabase Bağlantısı
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        st.stop()

supabase = init_supabase()

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

# URL'den QR / Token parametresini al
query_params = st.query_params
qr_code = query_params.get("qr", None)

# --- DURUM 1: ZİYARETÇİ EKRANI (QR TARATILDIĞINDA AÇILIR) ---
if qr_code:
    # Şık Logo ve Başlık Yerleşimi
    if os.path.exists("logo.png"):
        c1, c2 = st.columns([1, 5])
        with c1:
            st.image("logo.png", use_container_width=True)
        with c2:
            st.markdown("### 🚪 KnockKnockQR")
            st.caption("Akıllı Kapı Zili Sistemi")
    else:
        st.title("🚪 KnockKnockQR - Kapı Zili")
    
    # Supabase'den bu token'a ait evi sorgula
    try:
        response = supabase.table("doors").select("*").eq("qr_code", qr_code).execute()
        door_data = response.data
    except Exception as e:
        st.error(f"Veritabanı sorgulama hatası: {e}")
        st.stop()

    if not door_data:
        st.error("Bu QR koda / token'a ait kayıt bulunamadı.")
        st.stop()

    door = door_data[0]
    owner_name = door.get("owner_name", "Ev Sahibi")
    custom_status = door.get("custom_status", "Müsait")
    chat_id = door.get("telegram_chat_id")

    st.info(f"📌 **Konum / Daire:** {owner_name}")
    if custom_status:
        st.warning(f"🔔 **Ev Sahibinin Notu:** {custom_status}")

    st.markdown("---")
    st.write("Zil çalmak veya ev sahibine mesaj bırakmak için aşağıdaki seçenekleri kullanabilirsiniz:")

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
                    st.error("❌ Telegram bildirimi gönderilemedi, ancak mesajınız kaydedildi.")
            else:
                st.warning("⚠️ Bu kapı için Telegram Chat ID tanımlanmamış.")

# --- DURUM 2: YÖNETİM VE KAYIT PANELİ (PARAMETRESİZ ANA SAYFA) ---
else:
    if os.path.exists("logo.png"):
        c1, c2 = st.columns([1, 5])
        with c1:
            st.image("logo.png", use_container_width=True)
        with c2:
            st.markdown("### 🚪 KnockKnockQR")
            st.caption("Yönetim ve Kayıt Paneli")
    else:
        st.title("🚪 KnockKnockQR - Yönetim ve Kayıt Paneli")
        
    st.write("Bu panel üzerinden yeni bir kapı/token kaydı oluşturabilir ve QR kodunuzu üretebilirsiniz. Her token yalnızca tek bir eve/daireye tanımlıdır.")

    tab1, tab2 = st.tabs(["🏠 Yeni Ev / Token Kaydet", "🖨️ QR Kod Üret ve İndir"])

    with tab1:
        with st.form("registration_form"):
            st.subheader("Yeni Kapı & Token Tanımlama")
            reg_owner = st.text_input("Daire / Ev Sahibi Adı", placeholder="Örn: Daire 7 - Ahmet Yılmaz")
            reg_token = st.text_input("Benzersiz Token / QR Kodu", placeholder="Örn: daire7-xyz123 (Benzersiz olmalıdır)")
            reg_status = st.text_input("Anlık Durum Notu", value="Müsait")
            reg_chat_id = st.text_input("Telegram Chat ID", placeholder="Örn: 123456789")
            
            reg_submitted = st.form_submit_button("Sisteme Kaydet")

            if reg_submitted:
                if not reg_owner or not reg_token or not reg_chat_id:
                    st.error("Lütfen Daire Adı, Token ve Telegram Chat ID alanlarını eksiksiz doldurun!")
                else:
                    try:
                        data = {
                            "qr_code": reg_token,
                            "owner_name": reg_owner,
                            "custom_status": reg_status,
                            "telegram_chat_id": reg_chat_id
                        }
                        supabase.table("doors").upsert(data).execute()
                        st.success(f"✅ '{reg_token}' token'ı başarıyla kaydedildi!")
                    except Exception as e:
                        st.error(f"Kayıt sırasında hata oluştu: {e}")

    with tab2:
        st.subheader("QR Kod Oluşturucu")
        check_token = st.text_input("QR kodu üretmek istediğiniz Token'ı yazın:")
        base_url = st.text_input("Uygulama Temel URL'si", value="https://knockknockqr.streamlit.app")
        
        if check_token:
            full_qr_link = f"{base_url}/?qr={check_token}"
            st.write(f"🔗 **Hedef Bağlantı:** `{full_qr_link}`")
            
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(full_qr_link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buf = BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.image(byte_im, caption=f"Token: {check_token}", width=250)
                st.download_button(
                    label="📥 QR Kodu İndir (PNG)",
                    data=byte_im,
                    file_name=f"qr_{check_token}.png",
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"QR kod üretilirken hata oluştu: {e}")
