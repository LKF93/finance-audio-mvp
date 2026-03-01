import streamlit as st
from datetime import datetime
import io # MODULE NEEDED: Allows us to treat raw bytes like a file in memory
from logic import get_financial_data, generate_psychological_script, text_to_speech

st.title("Finance Audio Report")

# --- SESSION STATE (The App's Memory) ---
# Keeps data alive when you click buttons (otherwise Streamlit resets)
if "full_script" not in st.session_state:
    st.session_state.full_script = None
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

with st.sidebar:
    st.header("Settings")
    speed_selection = st.select_slider(
        "Reading Speed:",
        options=[0.5, 0.8, 1.0, 1.2, 1.5, 2.0],
        value=1.0, 
        help="1.0 is normal speed. 1.2 is recommended for news."
    )

ticker_input = st.text_input(
    "Enter Ticker Symbols (separate multiple with commas):", 
    value="",
    help="You can type Yahoo financen ticker. Example: AAPL (Apple), ^GSPC (S&P 500), KCHOL.IS (KOÇ HOLDING)"
)

# Logik: Wir machen aus dem Text eine saubere Liste
# .split(",") trennt bei Kommas, .strip() entfernt Leerzeichen, .upper() macht alles groß
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# Choosing audio options
focus_selection = st.radio(
    "Choose your content:",
    ["Overall Information", "Technical Report", "Sentimental Report"],
    index = 0, # Setting default option to Overall Information
    horizontal = True # Buttons are next to each other
)

# Choosing timeline options
time_focus = st.select_slider(
    "Choose a timeframe:",
    options = ["1 Day", "1 Week", "1 Month", "1 Year"],
    value="1 Month" # Default value
)

if st.button("Generate My Briefing"):
    with st.spinner("🔍 Deep-diving into market data and generating audio..."):
        temp_script = ""
        
        # Loop through selected stocks
        for ticker in tickers:
            data = get_financial_data(ticker)
            if data:
                script = generate_psychological_script(data, focus_selection, time_focus)
                temp_script += f"Analysis for {ticker}. {script}\n\n"
        
        if temp_script:
            st.session_state.full_script = temp_script
            # Generate audio only once for the combined text
            st.session_state.audio_bytes = text_to_speech(temp_script, speed=speed_selection)
        else:
            st.error("No data found for selected tickers.")

# --- DISPLAY SECTION ---
if st.session_state.audio_bytes and st.session_state.full_script:
    
    st.subheader("🎧 Your Audio Report")
    
    # FIX: We use for audio the official MIME-type: 'audio/mpeg'
    st.audio(io.BytesIO(st.session_state.audio_bytes), format='audio/mpeg')

    # Optional: Dynamischer Dateiname (wie vorhin besprochen)
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename_base = f"Briefing_{today_str}"
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Audio (MP3)",
            data=st.session_state.audio_bytes, # Download button handles raw bytes fine
            file_name="morning_briefing.mp3",
            mime="audio/mpeg" # Also change here to mpeg
        )
    with col2:
        st.download_button(
            label="📄 Download Script (TXT)",
            data=st.session_state.full_script,
            file_name="morning_briefing.txt",
            mime="text/plain"
        )
    
    # We display the text below
    with st.expander("Read Analyst Script"):
        st.write(st.session_state.full_script) # st.write is safer than st.markdown for plain text