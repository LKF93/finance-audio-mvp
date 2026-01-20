import streamlit as st
import io # MODULE NEEDED: Allows us to treat raw bytes like a file in memory
from logic import get_financial_data, generate_psychological_script, text_to_speech

st.title("☕ Morning Financial Brief")

# --- SESSION STATE (The App's Memory) ---
# Keeps data alive when you click buttons (otherwise Streamlit resets)
if "full_script" not in st.session_state:
    st.session_state.full_script = None
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

tickers = st.multiselect(
    "Select your portfolio:",
    ["NVDA", "VWCE.DE", "GDX", "TSLA", "BTC-USD", "AAPL", "MSFT"],
    default=["NVDA"]
)

if st.button("Generate My Briefing"):
    with st.spinner("🔍 Deep-diving into market data and generating audio..."):
        temp_script = ""
        
        # Loop through selected stocks
        for ticker in tickers:
            data = get_financial_data(ticker)
            if data:
                script = generate_psychological_script(data)
                temp_script += f"Analysis for {ticker}. {script}\n\n"
        
        if temp_script:
            st.session_state.full_script = temp_script
            # Generate audio only once for the combined text
            st.session_state.audio_bytes = text_to_speech(temp_script)
        else:
            st.error("No data found for selected tickers.")

# --- DISPLAY SECTION ---
if st.session_state.audio_bytes and st.session_state.full_script:
    
    st.subheader("🎧 Your Audio Briefing")
    
    # FIX: We use for audio the official MIME-type: 'audio/mpeg'
    st.audio(io.BytesIO(st.session_state.audio_bytes), format='audio/mpeg')
    
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