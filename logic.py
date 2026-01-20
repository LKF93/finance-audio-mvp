import yfinance as yf
import os
import google.generativeai as genai
from google.cloud import texttospeech
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv

# 1. Load Keys & Config
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Google Cloud Auth
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

def format_large_number(num):
    """Turns for example 4865000000 into -> 4.87 Billion"""
    if num is None or num == 'N/A':
        return "N/A"
    
    try:
        num = float(num)
        if num >= 1_000_000_000_000:
            return f"{num / 1_000_000_000_000:.2f} Trillion"
        elif num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f} Billion"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f} Million"
        else:
            return f"{num:.2f}"
    except:
        return str(num)

def get_financial_data(ticker_symbol):
    """
    Gets historical financial data (1 week, 1 month, 1 year).
    """
    print(f"🔍 Researching {ticker_symbol}...") 
    stock = yf.Ticker(ticker_symbol)
    
    # Make currency readable
    currency_raw = stock.info.get('currency', 'USD')
    currency_spoken = "US Dollars" if currency_raw == "USD" else currency_raw 

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
        
    except:
        return None

    info = stock.info
        
    # Formatting numbers for the LLM
    market_cap_clean = format_large_number(info.get('marketCap', 0))
    pe_ratio_clean = info.get('trailingPE', 'N/A')
    
    # PE Ratio runden, falls es eine Zahl ist
    if pe_ratio_clean != 'N/A':
        try:
            pe_ratio_clean = f"{float(pe_ratio_clean):.2f}"
        except:
            pass

    # Basic data and financial ratios
    fundamentals = {
        "Summary": info.get('longBusinessSummary', 'N/A')[:500],
        "PE Ratio": info.get('trailingPE', 'N/A'),
        "Market Cap": info.get('marketCap', 'N/A'),
        "52W High": info.get('fiftyTwoWeekHigh', 'N/A'),
        "52W Low": info.get('fiftyTwoWeekLow', 'N/A'),
    }

    # News Headlines
    news = ""
    try:
        for item in stock.news[:3]:
            news += f"- {item.get('title')}\n"
    except:
        news = "No recent news found."

    # Data package for the prompt
    return f"""
    ASSET: {ticker_symbol}
    CURRENCY_SPOKEN: {currency_spoken}
    
    [PRICE DATA]
    Current Price: {current_price:.2f} {currency_spoken}
    1-Week Change: {chg_1w:.2f}%
    1-Month Change: {chg_1m:.2f}% (Was: {price_1m:.2f})
    1-Year Change: {chg_1y:.2f}% (Was: {price_1y:.2f})
    
    [KEY METRICS]
    Market Cap: {fundamentals['Market Cap']} {currency_spoken}
    P/E Ratio: {fundamentals['PE Ratio']}
    
    [NEWS]
    {news}
    """

def generate_psychological_script(data_context):
    # Choose the model for text generation
    model = genai.GenerativeModel('gemini-3-flash-preview') 
    
    # --- SYSTEM PROMPT (Neutral & Clear) ---
    prompt = f"""
    You are a professional, objective financial news anchor.
    Your tone is calm, factual, and precise. You do NOT give advice. You do NOT use hype.
    
    DATA DOSSIER:
    {data_context}
    
    TASK: Write a structured market report (approximately 500 words) for audio reading.
    
    CRITICAL FORMATTING RULES:
    1. Read Market Cap exactly as written in the dossier (e.g., "4.5 Trillion"). Do NOT read full digits.
    2. Numbers: Read Market Cap exactly as written in the dossier (e.g., "4.5 Trillion"). Do NOT read full digits.
    3. Write in PLAIN TEXT only. 
    4. DO NOT use markdown formatting. 
    5. DO NOT use bolding (**text**) or code blocks (`text`) for numbers. 
    6. DO NOT use lists or bullet points. Write in full paragraphs.

    STRUCTURE:
    1. **Welcome**: Shortly welcome the user and say that this is todays financial audio for his or her portfolio.
    2. **Current Status**: Start with the current price and the currency.
    3. **Historical Context**: 
       - Explicitly state the price changes. Example: "One month ago, the stock was trading at 80 USD, and has since risen to 100 USD, an increase of 25 percent."
       - Cover the 1-week, 1-month, and 1-year trends clearly.
    4. **News & Context**: Briefly mention relevant news or political factors affecting the asset based on the provided headlines.
    5. **Financial Ratios**: Mention the P/E ratio and Market Cap neutrally.
    6. **Outlook**: End with a cautious, data-backed trend observation (e.g., "The data suggests a consolidation phase..."). No wild predictions.
    
    STYLE RULES:
    - Use short, simple sentences.
    - Avoid complex jargon.
    - No emotional words (like "unfortunately", "surprisingly", "skyrocketed"). Use "increased", "decreased", "remained stable".
    - Do not say "Buy" or "Sell".
    - Speak slowly and clearly (use punctuation to create pauses).
    """
    
    # Safety Settings (so LLM doesnt stop when political context appears)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        if response.parts:
            return response.text
        return "Data analysis currently unavailable."
    except Exception as e:
        return f"Error: {e}"

def text_to_speech(script_text):
    if not script_text or "Error" in script_text:
        return None

    try:
        synthesis_input = texttospeech.SynthesisInput(text=script_text)

        # HIER IST DER WECHSEL AUF DAS BESTE MODELL:
        # We use the model "Chirp 3 HD". 
        # Der Name der Stimme sagt Google automatisch, dass es das teure, gute Modell nutzen soll.
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Puck"  # Fenrir = Tief, seriös, männlich
            # Alternativen: 
            # "en-US-Chirp3-HD-Puck" (Männlich, etwas weicher)
            # "en-US-Chirp3-HD-Kore" (Weiblich, sehr klar)
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            # WICHTIG BEI CHIRP: Lass die Geschwindigkeit auf 1.0.
            # Chirp macht Pausen automatisch sehr natürlich. Wenn wir hier drehen, klingt es künstlich.
            speaking_rate=1.0 
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