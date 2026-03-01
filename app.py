import streamlit as st
from datetime import datetime
import io 
from logic import get_financial_data, generate_psychological_script, text_to_speech

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Finans Raporu", page_icon="📈")

st.title("🎙️ AI Finansal Sesli Rapor")
st.caption("Gerçek zamanlı borsa verileri ve yapay zeka analizleri")

# --- SESSION STATE (Memory) ---
if "full_script" not in st.session_state:
    st.session_state.full_script = None
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # 1. SPEED SLIDER (Hız Ayarı)
    # Intuition: We pass this value directly to the text_to_speech function
    speed_selection = st.select_slider(
        "Ses Okuma Hızı (Speed):",
        options=[0.5, 0.8, 1.0, 1.2, 1.5, 2.0],
        value=1.0, # Default is slightly faster for professional feel
        help="1.0 normal hızdır."
    )
    
    st.divider()
    
    # 2. CONTENT STYLE (İçerik Stili)
    focus_selection = st.radio(
        "Rapor Türü Seçin:",
        ["Genel Özet", "Teknik Analiz", "Piyasa Duyarlılığı (Haber Odaklı)"],
        index=0
    )
    
    # 3. TIMEFRAME (Zaman Dilimi)
    time_focus = st.select_slider(
        "Zaman Odağı:",
        options=["1 Gün", "1 Hafta", "1 Ay", "1 Yıl"],
        value="1 Ay"
    )

# --- MAIN INTERFACE ---

# ANY TICKER INPUT
# Logic: Users can type KCHOL.IS, THYAO.IS, AAPL etc.
ticker_input = st.text_input(
    "Takip Etmek İstediğiniz Hisseleri Girin (Virgül ile ayırın):",
    value="KCHOL.IS, THYAO.IS, TSLA",
    help="Örnek: KCHOL.IS (Koç Holding), BTC-USD (Bitcoin), AAPL (Apple)"
)

# Convert input string to a clean list
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

if st.button("🚀 Raporu Oluştur (Generate)"):
    if not tickers:
        st.error("Lütfen en az bir sembol girin.")
    else:
        with st.spinner("🔍 Veriler analiz ediliyor ve ses dosyası hazırlanıyor..."):
            combined_script = ""
            
            # Loop through the dynamic ticker list
            for ticker in tickers:
                st.write(f"⏳ {ticker} verileri işleniyor...")
                data = get_financial_data(ticker)
                if data:
                    # Generate text using Gemini
                    script = generate_psychological_script(data, focus_selection, time_focus)
                    combined_script += f"{ticker} analizi. {script}\n\n"
                else:
                    st.warning(f"'{ticker}' için veri bulunamadı. Lütfen sembolü kontrol edin.")

            if combined_script:
                st.session_state.full_script = combined_script
                # Generate audio with the selected speed
                st.session_state.audio_bytes = text_to_speech(combined_script, speed=speed_selection)
            else:
                st.error("Hiçbir geçerli veri işlenemedi.")

# --- DISPLAY & DOWNLOAD SECTION ---
if st.session_state.audio_bytes and st.session_state.full_script:
    
    st.success("✅ Raporunuz Hazır!")
    
    st.subheader("🎧 Sesli Raporu Dinle")
    # Using io.BytesIO to handle the raw audio data in memory
    st.audio(io.BytesIO(st.session_state.audio_bytes), format='audio/mpeg')

    # Filename with current date
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Ses Dosyasını İndir (MP3)",
            data=st.session_state.audio_bytes,
            file_name=f"finans_raporu_{today_str}.mp3",
            mime="audio/mpeg"
        )
    with col2:
        st.download_button(
            label="📄 Metni İndir (TXT)",
            data=st.session_state.full_script,
            file_name=f"finans_metni_{today_str}.txt",
            mime="text/plain"
        )
    
    # Expandable section for the text script
    with st.expander("📝 Analiz Metnini Oku"):
        st.write(st.session_state.full_script)