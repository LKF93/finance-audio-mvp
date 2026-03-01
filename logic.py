import yfinance as yf
import os
from google import genai
from google.genai import types
from google.cloud import texttospeech
from dotenv import load_dotenv

# 1. Load Keys & Config
load_dotenv()

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Google Cloud Auth for Text-to-Speech
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

def format_large_number(num):
    """
    Converts raw numbers into Turkish financial terms (Milyon, Milyar, Trilyon).
    Ensures the AI reads the scale correctly.
    """
    if num is None or num == 'N/A':
        return "N/A"
    
    try:
        num = float(num)
        if num >= 1_000_000_000_000:
            return f"{num / 1_000_000_000_000:.2f} Trilyon"
        elif num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f} Milyar"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f} Milyon"
        else:
            return f"{num:.2f}"
    except:
        return str(num)

def get_financial_data(ticker_symbol):
    """
    Fetches data for ANY ticker from Yahoo Finance.
    Localized for Turkish currency (TRY) and Borsa Istanbul (.IS).
    """
    print(f"🔍 Researching: {ticker_symbol}...") 
    stock = yf.Ticker(ticker_symbol)
    
    # Handle Currency localization
    currency_raw = stock.info.get('currency', 'TRY')
    if currency_raw == "USD": 
        currency_spoken = "Amerikan Doları"
    elif currency_raw == "TRY": 
        currency_spoken = "Türk Lirası"
    else: 
        currency_spoken = currency_raw 

    try:
        hist = stock.history(period="1y")
        if hist.empty:
            return None
        current_price = hist['Close'].iloc[-1]
        
        def get_change(days_ago):
            if len(hist) > days_ago:
                past_price = hist['Close'].iloc[-days_ago]
                change_pct = ((current_price - past_price) / past_price) * 100
                return past_price, change_pct
            return current_price, 0.0

        price_1w, chg_1w = get_change(5)
        price_1m, chg_1m = get_change(20)
        price_1y, chg_1y = get_change(250)
        
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return None

    info = stock.info
    market_cap_clean = format_large_number(info.get('marketCap', 0))
    
    # Data package formatted for the Turkish Prompt
    return f"""
    ASSET: {ticker_symbol}
    CURRENCY: {currency_spoken}
    
    [PRICE DATA]
    Current Price: {current_price:.2f} {currency_spoken}
    1-Week Change: %{chg_1w:.2f}
    1-Month Change: %{chg_1m:.2f} (Previous: {price_1m:.2f})
    1-Year Change: %{chg_1y:.2f} (Previous: {price_1y:.2f})
    
    [METRICS]
    Market Cap: {market_cap_clean}
    P/E Ratio: {info.get('trailingPE', 'N/A')}
    """

def generate_psychological_script(data_context, focus_style, time_focus):
    """
    Generates the news script using Gemini. 
    Localized for Turkish but instructed in English for maximum precision.
    """
    # 1. Determine if Google Search is needed
    # We use search for Sentiment and Balanced to get the "Why"
    use_search = True if ("Sentimental" in focus_style or "Genel" in focus_style or "Piyasa" in focus_style) else False

    # 2. CORE SYSTEM INSTRUCTIONS
    base_system_instructions = """
    You are a professional financial news anchor for a Turkish broadcast.
    TONE: Calm, authoritative, and factual.
    LANGUAGE: Write exclusively in TURKISH.
    
    STRICT FORMATTING:
    - PLAIN TEXT ONLY. No markdown (no **), no bold, no bullet points.
    - Currency: Say 'Türk Lirası' or 'Amerikan Doları'.
    - Numbers: Use 'Milyon' or 'Milyar'.
    """

    # 3. DYNAMIC MISSION BRIEFING (The Heart of the Logic)
    # We use specific prompts to force the 90/10 or 50/50 balance
    
    if "Technical" in focus_style:
        # 100% Data focused
        mission = """
        MISSION: TECHNICAL ANALYSIS REPORT.
        - FOCUS: 100% on hard financial data and ratios.
        - CONTENT: Discuss price ranges, 52-week highs/lows, P/E ratios, and percentage changes.
        - STRUCTURE: Welcome -> Detailed Price Action -> Key Ratios -> Technical Outlook.
        - INSTRUCTION: Be precise with every number provided in the Dossier.
        """
    
    elif "Sentimental" in focus_style or "Piyasa" in focus_style:
        # 90% Story/News, 10% Numbers
        mission = """
        MISSION: MARKET SENTIMENT STORY (NARRATIVE).
        - FOCUS: 90% on NEWS and STORY, only 10% on numbers.
        - SEARCH: Use Google Search to find the latest headlines/rumors.
        - CONTENT: Explain WHY the stock is moving. What is the mood of the investors?
        - NUMBER LIMIT: Mention the 'Current Price' ONLY ONCE. Ignore all other ratios (P/E, Market Cap) unless they are part of a news story.
        - STRUCTURE: Breaking News Headline -> Narrative/Context -> Brief Price Anchor -> Outlook.
        """
    
    else: # Balanced / Genel Özet
        # 50/50 Balance
        mission = """
        MISSION: BALANCED DAILY BRIEFING.
        - FOCUS: 50% Technical Data, 50% News Headlines.
        - CONTENT: Connect the current price movement to 1 major news event found via Search.
        - STRUCTURE: Welcome -> Price Update -> News Context -> Financial Summary.
        - INSTRUCTION: Give the most important numbers (Price, 1-Month change) and the most important headline.
        """

    # 4. CONSTRUCT FINAL PROMPT
    final_prompt = f"""
    {base_system_instructions}
    {mission}
    
    TIME CONTEXT: {time_focus}
    
    DATA DOSSIER:
    {data_context}
    
    TASK: Write a 200-word professional Turkish audio script. Follow the FOCUS percentages strictly.
    """
    
    try:
        # Using the Search Tool
        tools_config = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                tools=tools_config
            )
        )
        return response.text if response.text else "Analiz oluşturulamadı."
    except Exception as e:
        return f"Gemini Error: {e}"

def text_to_speech(script_text, speed=1.0):
    """
    Converts Turkish text to high-quality MP3 audio.
    Supports dynamic speed (0.5 to 2.0).
    """
    if not script_text or "Error" in script_text:
        return None

    try:
        synthesis_input = texttospeech.SynthesisInput(text=script_text)

        # SELECTING THE TURKISH VOICE
        # 'tr-TR-Wavenet-D' is a professional male voice. 
        # Alternatives: 'tr-TR-Wavenet-A' (female), 'tr-TR-Wavenet-C' (female)
        voice = texttospeech.VoiceSelectionParams(
            language_code="tr-TR",
            name="tr-TR-Wavenet-D" 
        )

        # DYNAMIC SPEED CONFIGURATION
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speed  # Controlled via app.py slider
        )

        response = tts_client.synthesize_speech(
            input=synthesis_input, 
            voice=voice, 
            audio_config=audio_config
        )

        return response.audio_content

    except Exception as e:
        print(f"⚠️ TTS Error: {e}")
        return None