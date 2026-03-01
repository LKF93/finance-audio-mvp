import yfinance as yf
import os
from google import genai
from google.genai import types
from google.cloud import texttospeech
from dotenv import load_dotenv

# 1. Load Keys & Config
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

   # Wir lassen yfinance News weg, wir nutzen Google Search wenn nötig
    news = "News will be fetched via Google Search if required."

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

def generate_psychological_script(data_context, focus_style, time_focus):
    
    use_search = False # Default value, so choosing "Overall Information" does not crash

    # ---------------------------------------------------------
    # TEIL 1: DEIN AUSFÜHRLICHER SYSTEM PROMPT (Wiederhergestellt)
    # ---------------------------------------------------------
    base_system_instructions = """
    You are a professional, objective financial news anchor.
    Your tone is calm, factual, and precise. 
    
    CRITICAL FORMATTING RULES (MUST FOLLOW):
    1. Write in PLAIN TEXT only. NO markdown, NO bold (**), NO code blocks.
    2. Numbers: Read Market Cap naturally (e.g., "4.5 Trillion"). DO NOT read full digits string.
    3. Currency: Always say "US Dollars" or "Euros", never "USD".
    4. Structure: Write in full, spoken paragraphs. No bullet points.

    STYLE RULES:
    - Use short, simple sentences. Perfect for audio reading.
    - No emotional words (like "unfortunately", "skyrocketed").
    - Do not say "Buy" or "Sell".
    - Speak slowly and clearly (use punctuation to create pauses).
    """

    # ---------------------------------------------------------
    # TEIL 2: DEINE INHALTS-STRUKTUREN (Wiederhergestellt)
    # ---------------------------------------------------------
    
    if "Technical" in focus_style:
        mission_briefing = """
        YOUR MISSION: CREATE A TECHNICAL ANALYSIS REPORT.
        
        STRUCTURE:
        1. **Welcome**: Brief technical welcome ("Technical briefing for [Asset]").
        2. **Price Action**: Focus heavily on exact price changes and percentages.
        3. **Key Levels**: Mention 52-Week High/Low vs Current Price.
        4. **Ratios**: Discuss P/E Ratio and Market Cap.
        5. **Outlook**: Data-driven trend conclusion.
        
        NOTE: Ignore soft news headlines unless they explain a massive crash. Focus on math.
        """
        use_search = False
        
    elif "Sentimental" in focus_style:
        # Hier habe ich nur EINE Zeile hinzugefügt: "USE GOOGLE SEARCH". 
        # Sonst weiß dein alter Prompt nicht, dass er das neue Tool benutzen darf.
        mission_briefing = """
        YOUR MISSION: ACT AS A FINANCIAL JOURNALIST, NOT AN ANALYST.
        
        CRITICAL RULES FOR SENTIMENT MODE:
        1. NO LISTING OF RATIOS: Do NOT mention Market Cap, P/E Ratio, or 52-Week Highs. They are forbidden in this mode.
        2. GOOGLE SEARCH IS PRIMARY: 90% of your script must come from Google Search results about news, politics, and sector trends.
        3. THE 'WHY' ONLY: Explain the mood of the market. Is there geopolitical tension? A new government regulation? A strategic merger?
        4. PRICE AS A FOOTNOTE: You may only mention the 'Current Price' ONCE at the very end. Do NOT mention percentage changes for 1-week or 1-month.
        
        STRUCTURE:
        1. **Headline News**: Start with the biggest recent story found via Search.
        2. **The Narrative**: Explain how politics, innovation, or deals are shaping the company's future.
        3. **Sector Mood**: What is happening in the broader industry (e.g., Energy, Tech)?
        4. **Closing**: One-sentence mention of the current price and a final sentiment outlook.
        
        NOTE: Use descriptive language (e.g., "Investors are cautious", "Optimism is rising") instead of mathematical data.
        """
        use_search = True
        
    else:
        # Balanced / Default
        mission_briefing = """
        YOUR MISSION: CREATE A BALANCED DAILY BRIEFING.
        
        INSTRUCTION: Use Google Search to find 1 major headline to explain the price move.
        
        STRUCTURE:
        1. **Welcome**: Standard welcome.
        2. **Current Status**: Current price and context.
        3. **The Big Picture**: Combine Technical Trend with Top News found via Search.
        4. **Context**: Explain the movement briefly.
        5. **Outlook**: Neutral summary.
        
        NOTE: Keep a 50/50 balance between price data and news context.
        """

        use_search = True
    # ---------------------------------------------------------
    # TEIL 3: DEINE ZEIT-STRUKTUREN (Wiederhergestellt)
    # ---------------------------------------------------------
    
    if time_focus == "1 Day":
        time_instruction = """
        TIME CONTEXT: IMMEDIATE SHORT-TERM (Last 24 Hours).
        - Focus ONLY on the 'Current Price' and today's movement.
        - Ignore long-term trends unless extreme.
        - Discuss immediate reaction to latest news.
        """
    elif time_focus == "1 Week":
        time_instruction = """
        TIME CONTEXT: WEEKLY WRAP-UP (Last 5 Days).
        - Focus primarily on the '1-Week Change'.
        - Summarize how the stock performed this week.
        """
    elif time_focus == "1 Month":
        time_instruction = """
        TIME CONTEXT: MONTHLY TREND.
        - Focus on the '1-Month Change'. 
        - Is the stock in an uptrend or downtrend over the last 30 days?
        """
    else: # 1 Year
        time_instruction = """
        TIME CONTEXT: LONG-TERM VIEW (Yearly Performance).
        - Focus on the '1-Year Change' and the '52-Week Range'.
        - Discuss the major trend of the year.
        """

    # ---------------------------------------------------------
    # TEIL 4: ZUSAMMENBAU
    # ---------------------------------------------------------
    final_prompt = f"""
    {base_system_instructions}
    
    {mission_briefing}
    
    {time_instruction}
    
    DATA DOSSIER:
    {data_context}
    
    TASK: Write a 200-word audio script integrating ALL instructions above.
    """
    
    try:
        # Tool Konfiguration (Neue Syntax)
        if use_search:
            tools_config = [types.Tool(google_search=types.GoogleSearch())]
        else:
            tools_config = None

        # API Aufruf
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature = 0.5,
                tools=tools_config,
                safety_settings=[
                    types.SafetySetting(
                        category='HARM_CATEGORY_HARASSMENT',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_HATE_SPEECH',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_DANGEROUS_CONTENT',
                        threshold='BLOCK_NONE'
                    )
                ]
            )
        )
        
        if response.text:
            return response.text
        return "Analysis unavailable."
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"Error generating text: {e}"

def text_to_speech(script_text, speed=1.0):
    if not script_text or "Error" in script_text:
        return None

    try:
        synthesis_input = texttospeech.SynthesisInput(text=script_text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Iapetus" 
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speed 
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