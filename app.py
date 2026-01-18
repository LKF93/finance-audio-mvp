# app.py
import streamlit as st
from logic import get_financial_data, generate_psychological_script, text_to_speech

st.title("☕ Morning Financial Brief")

# User Input
tickers = st.multiselect(
    "Select your portfolio:",
    ["NVDA", "VWCE.DE", "GDX", "TSLA", "BTC-USD"],
    default=["NVDA"]
)

if st.button("Generate My Briefing"):
    full_script = ""
    
    # Progress bar for UX
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        st.subheader(f"Analyzing {ticker}...")
        
        # 1. Get Data
        data = get_financial_data(ticker)
        
        # 2. AI Synthesis
        script = generate_psychological_script(data)
        full_script += f"Update for {ticker}. {script} <break time='1.0s' /> "
        
        st.write(f"📝 *Draft:* {script}") # Show text for debugging
        progress_bar.progress((i + 1) / len(tickers))

    # 3. Audio Generation
    st.info("Synthesizing Audio...")
    audio_bytes = text_to_speech(full_script)
    
    # 4. Play Audio
    st.audio(audio_bytes, format='audio/mp3')
    st.success("Briefing Ready! 🎧")