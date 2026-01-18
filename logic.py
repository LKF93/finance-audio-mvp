# logic.py
import yfinance as yf
import os
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# 1. Load the Keys (The credentials to use the tools)
load_dotenv()

# Configure the AI services
# We use 'flash' because it is fast and cheap, perfect for this app.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def get_financial_data(ticker_symbol):
    print(f"🔍 Researching {ticker_symbol}...") 
    stock = yf.Ticker(ticker_symbol)
    
    # 1. Price Action
    try:
        history = stock.history(period="1mo")
        if history.empty:
            current_price = "N/A"
            month_change = 0.0
        else:
            current_price = history['Close'].iloc[-1]
            start_price = history['Close'].iloc[0]
            month_change = ((current_price - start_price) / start_price) * 100
    except Exception as e:
        print(f"⚠️ Error fetching price: {e}")
        current_price = "N/A"
        month_change = 0.0

    # 2. Fundamentals
    info = stock.info
    fundamentals = {
        "Sector": info.get('sector', 'Unknown'),
        "PE Ratio": info.get('trailingPE', 'N/A'),
        "52W High": info.get('fiftyTwoWeekHigh', 'N/A'),
        "Beta": info.get('beta', 'N/A'),
        "Market Cap": info.get('marketCap', 'N/A')
    }

    # 3. News (THE FIX IS HERE)
    try:
        news_items = stock.news
        news_summary = ""
        # We limit to 3 items to save tokens
        for item in news_items[:3]:
            # .get() prevents the crash if 'title' is missing
            title = item.get('title', 'No Title Available')
            publisher = item.get('publisher', 'Unknown Source')
            news_summary += f"- {title} (Source: {publisher})\n"
            
            # Debugging: Print looking for weird data structures
            # print(f"DEBUG ITEM: {item}") 
    except Exception as e:
        print(f"⚠️ Error fetching news: {e}")
        news_summary = "No news data available at this moment."

    # Construct the Dossier
    data_package = (
        f"**ASSET REPORT: {ticker_symbol}**\n"
        f"1. MARKET DATA:\n"
        f"   - Current Price: ${current_price}\n"
        f"   - 1-Month Trend: {month_change:.2f}%\n"
        f"2. FUNDAMENTALS:\n"
        f"   - Sector: {fundamentals['Sector']}\n"
        f"   - P/E Ratio: {fundamentals['PE Ratio']}\n"
        f"   - Volatility (Beta): {fundamentals['Beta']}\n"
        f"3. NEWS HEADLINES:\n{news_summary}\n"
    )
    return data_package

def generate_psychological_script(data_context):
    """
    This function is the 'Writer'.
    It takes the raw data and turns it into a spoken narrative.
    """
    # Defining our LLM model
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # The PROMPT is where your "Psychological" USP happens.
    prompt = f"""
    You are a Stoic Financial Advisor for a podcast.
    
    Here is the realtime market data:
    {data_context}
    
    Your Goal: Create a 2-sentence audio update for this stock.
    
    Guidelines:
    1. If the stock is DOWN: Be reassuring. Focus on the long term. Use phrases like "Buying opportunity" or "Market noise."
    2. If the stock is UP: Be grounded. Don't get hyped. Warn against FOMO (Fear Of Missing Out).
    3. If news is mentioned, briefly explain *why* it matters, but keep it simple.
    4. Do NOT read the numbers like a robot. Say "up about 2 percent" instead of "up 2.14 percent".
    5. Write ONLY the spoken text. No "Here is the summary" or emojis.
    """
    
    response = model.generate_content(prompt)
    return response.text

# In logic.py

def text_to_speech(script_text):
    """
    This function is the 'Speaker'.
    """
    try:
        # NEW SYNTAX for ElevenLabs v1.0+
        # We use a specific Voice ID 'Adam' ID: 'pNInz6obpgDQGcFmaJgB'
        
        audio_generator = client.text_to_speech.convert(
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam Voice ID
            output_format="mp3_44100_128",
            text=script_text,
            model_id="eleven_multilingual_v2"
        )
        
        # The new SDK returns a generator, so we join the chunks into bytes
        return b"".join(audio_generator)
        
    except Exception as e:
        print(f"⚠️ Audio generation failed: {e}")
        return None