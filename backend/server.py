from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date, timedelta
import math
from geopy.distance import geodesic
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ============================================================
# LOGGING SETUP (Early initialization)
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# PORT CONFIGURATION (Render.com compatibility)
# ============================================================
PORT = int(os.environ.get("PORT", 8000))
logger.info(f"Server will start on port: {PORT}")

# ============================================================
# LLM CONFIGURATION - EASY SWAP
# ============================================================
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'emergent')

def get_llm_config():
    """Get LLM API key and provider based on configuration"""
    if LLM_PROVIDER == 'google':
        api_key = os.environ.get('GOOGLE_GEMINI_KEY')
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_KEY not set in .env")
        return {'provider': 'google', 'api_key': api_key}
    else:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise ValueError("EMERGENT_LLM_KEY not set in .env")
        return {'provider': 'emergent', 'api_key': api_key}

if LLM_PROVIDER == 'emergent':
    from emergentintegrations.llm.chat import LlmChat, UserMessage

# ============================================================
# MONGODB CONNECTION (Non-blocking with fallback)
# ============================================================
client = None
db = None
DB_CONNECTED = True

def init_database():
    """Initialize MongoDB connection with error handling"""
    global client, db, DB_CONNECTED
    
    try:
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME', 'islamic_portal')
        
        if not mongo_url:
            logger.warning("MONGO_URL not set - database features disabled")
            return True
        
        # Create client with timeout settings
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        db = client[db_name]
        DB_CONNECTED = True
        logger.info(f"MongoDB connection initialized: {db_name}")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        logger.warning("Server will continue without database - some features may be limited")
        DB_CONNECTED = True
        return True

# Initialize database (non-blocking)
init_database()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# KAABA COORDINATES
KAABA_LAT = 21.4225
KAABA_LNG = 39.8262

# Quran API Base URL
QURAN_API_BASE = "https://api.alquran.cloud/v1"

# ================== MODELS ==================

class PrayerTimesRequest(BaseModel):
    latitude: float
    longitude: float
    date: Optional[str] = None

class PrayerTimesResponse(BaseModel):
    fajr: str
    sunrise: str
    dhuhr: str
    asr: str
    maghrib: str
    isha: str
    date: str
    location: str

class QiblaRequest(BaseModel):
    latitude: float
    longitude: float

class QiblaResponse(BaseModel):
    qibla_direction: float
    distance_to_kaaba: float

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: str = "tr"

class ChatResponse(BaseModel):
    response: str
    session_id: str

class AyahResponse(BaseModel):
    number: int
    numberInSurah: int
    text: str
    translation: Optional[str] = None
    surahNumber: int
    surahName: str
    surahNameArabic: str
    juz: int
    page: int

class SurahResponse(BaseModel):
    number: int
    name: str
    englishName: str
    englishNameTranslation: str
    numberOfAyahs: int
    revelationType: str

class ZakatRequest(BaseModel):
    gold_grams: float = 0
    silver_grams: float = 0
    cash: float = 0
    other_assets: float = 0
    currency: str = "TRY"

class ZakatResponse(BaseModel):
    total_assets: float
    nisab_gold: float
    nisab_silver: float
    is_zakat_due: bool
    zakat_amount: float
    currency: str

# ================== PRAYER TIMES CALCULATION ==================

def calculate_prayer_times(latitude: float, longitude: float, date_obj: date) -> dict:
    """Calculate prayer times using Diyanet method"""
    import math
    
    # Julian date
    a = (14 - date_obj.month) // 12
    y = date_obj.year + 4800 - a
    m = date_obj.month + 12 * a - 3
    jd = date_obj.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    
    n = jd - 2451545.0
    L = (280.46 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lambda_sun = math.radians(L + 1.915 * math.sin(g) + 0.02 * math.sin(2 * g))
    epsilon = math.radians(23.439 - 0.0000004 * n)
    declination = math.asin(math.sin(epsilon) * math.sin(lambda_sun))
    
    y_eq = math.tan(epsilon / 2) ** 2
    eq_of_time = y_eq * math.sin(2 * math.radians(L)) - 2 * 0.0167 * math.sin(g)
    eq_of_time += 4 * 0.0167 * y_eq * math.sin(g) * math.cos(2 * math.radians(L))
    eq_of_time = math.degrees(eq_of_time) * 4
    
    solar_noon = 12 - eq_of_time / 60 - longitude / 15
    lat_rad = math.radians(latitude)
    
    def time_for_angle(angle, is_rising=False):
        cos_ha = (math.sin(math.radians(angle)) - math.sin(lat_rad) * math.sin(declination)) / (math.cos(lat_rad) * math.cos(declination))
        cos_ha = max(-1, min(1, cos_ha))
        ha = math.degrees(math.acos(cos_ha)) / 15
        return solar_noon - ha if is_rising else solar_noon + ha
    
    fajr = time_for_angle(-18, is_rising=True)
    sunrise = time_for_angle(-0.833, is_rising=True)
    dhuhr = solar_noon
    
    noon_shadow = abs(math.tan(lat_rad - declination))
    asr_shadow = 1 + noon_shadow
    asr_altitude = math.degrees(math.atan(1 / asr_shadow))
    asr = time_for_angle(asr_altitude)
    
    maghrib = time_for_angle(-0.833)
    isha = time_for_angle(-17)
    
    def format_time(decimal_hours):
        decimal_hours = decimal_hours % 24
        hours = int(decimal_hours)
        minutes = int((decimal_hours - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    return {
        "fajr": format_time(fajr),
        "sunrise": format_time(sunrise),
        "dhuhr": format_time(dhuhr),
        "asr": format_time(asr),
        "maghrib": format_time(maghrib),
        "isha": format_time(isha),
    }

# ================== QIBLA CALCULATION ==================

def calculate_qibla(latitude: float, longitude: float) -> tuple:
    """Calculate Qibla direction using great circle formula"""
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    lat2 = math.radians(KAABA_LAT)
    lon2 = math.radians(KAABA_LNG)
    
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    qibla = math.degrees(math.atan2(x, y))
    qibla = (qibla + 360) % 360
    
    distance = geodesic((latitude, longitude), (KAABA_LAT, KAABA_LNG)).km
    return qibla, distance

# ================== QURAN API HELPERS ==================

async def fetch_quran_page(page: int) -> dict:
    """Fetch a specific page from Quran API with Arabic and Turkish translation"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch Arabic (Uthmani script)
        arabic_url = f"{QURAN_API_BASE}/page/{page}/quran-uthmani"
        arabic_resp = await client.get(arabic_url)
        
        # Fetch Turkish translation (Diyanet)
        turkish_url = f"{QURAN_API_BASE}/page/{page}/tr.diyanet"
        turkish_resp = await client.get(turkish_url)
        
        if arabic_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Page not found")
        
        arabic_data = arabic_resp.json()
        turkish_data = turkish_resp.json() if turkish_resp.status_code == 200 else None
        
        return {
            "arabic": arabic_data.get("data", {}),
            "turkish": turkish_data.get("data", {}) if turkish_data else None
        }

async def fetch_surah(surah_number: int) -> dict:
    """Fetch complete surah with Arabic and Turkish translation"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch both Arabic and Turkish in one call
        url = f"{QURAN_API_BASE}/surah/{surah_number}/editions/quran-uthmani,tr.diyanet"
        resp = await client.get(url)
        
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Surah not found")
        
        return resp.json().get("data", [])

async def fetch_all_surahs() -> list:
    """Fetch list of all surahs"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{QURAN_API_BASE}/surah"
        resp = await client.get(url)
        
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch surahs")
        
        return resp.json().get("data", [])

# ================== API ROUTES ==================

@api_router.get("/")
async def root():
    return {"message": "Islamic Portal API - Bismillah", "status": "running"}

@api_router.post("/prayer-times", response_model=PrayerTimesResponse)
async def get_prayer_times(request: PrayerTimesRequest):
    """Get prayer times for a specific location and date"""
    try:
        date_obj = datetime.strptime(request.date, "%Y-%m-%d").date() if request.date else date.today()
        times = calculate_prayer_times(request.latitude, request.longitude, date_obj)
        
        return PrayerTimesResponse(
            **times,
            date=date_obj.isoformat(),
            location=f"{request.latitude:.4f}, {request.longitude:.4f}"
        )
    except Exception as e:
        logging.error(f"Prayer times error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/qibla", response_model=QiblaResponse)
async def get_qibla_direction(request: QiblaRequest):
    """Calculate Qibla direction from given coordinates"""
    try:
        qibla_direction, distance = calculate_qibla(request.latitude, request.longitude)
        return QiblaResponse(
            qibla_direction=round(qibla_direction, 2),
            distance_to_kaaba=round(distance, 2)
        )
    except Exception as e:
        logging.error(f"Qibla calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================== QURAN ROUTES ==================

@api_router.get("/quran/surahs")
async def get_surahs():
    """Get list of all 114 surahs"""
    try:
        surahs = await fetch_all_surahs()
        return {"data": surahs, "total": len(surahs)}
    except Exception as e:
        logging.error(f"Surahs fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/quran/surah/{surah_number}")
async def get_surah(surah_number: int):
    """Get a specific surah with Arabic and Turkish translation"""
    if surah_number < 1 or surah_number > 114:
        raise HTTPException(status_code=400, detail="Invalid surah number (1-114)")
    
    try:
        data = await fetch_surah(surah_number)
        return {"data": data}
    except Exception as e:
        logging.error(f"Surah fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/quran/page/{page_number}")
async def get_quran_page(page_number: int):
    """Get a specific page (1-604) with Arabic and Turkish translation"""
    if page_number < 1 or page_number > 604:
        raise HTTPException(status_code=400, detail="Invalid page number (1-604)")
    
    try:
        data = await fetch_quran_page(page_number)
        return {"data": data, "page": page_number, "total_pages": 604}
    except Exception as e:
        logging.error(f"Page fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/quran/juz/{juz_number}")
async def get_juz(juz_number: int):
    """Get a specific juz (1-30)"""
    if juz_number < 1 or juz_number > 30:
        raise HTTPException(status_code=400, detail="Invalid juz number (1-30)")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{QURAN_API_BASE}/juz/{juz_number}/quran-uthmani"
            resp = await client.get(url)
            
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Juz not found")
            
            return resp.json()
    except Exception as e:
        logging.error(f"Juz fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================== ZAKAT CALCULATOR ==================

# Static fallback prices (updated regularly)
GOLD_PRICE_PER_GRAM = 2850  # TRY - fallback
SILVER_PRICE_PER_GRAM = 35  # TRY - fallback
NISAB_GOLD_GRAMS = 80.18  # 7.5 tola = ~80.18 grams
NISAB_SILVER_GRAMS = 561.26  # 52.5 tola = ~561.26 grams

async def fetch_live_gold_price() -> dict:
    """
    Fetch LIVE gold and silver prices from multiple sources.
    Returns: { 'gold': price_per_gram_TRY, 'silver': price_per_gram_TRY, 'source': 'api_name' }
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try BigPara API (Turkish market data)
            try:
                response = await client.get(
                    "https://bigpara.hurriyet.com.tr/api/v1/altincisi/golddetail"
                )
                if response.status_code == 200:
                    data = response.json()
                    # Extract gram gold price
                    gold_price = float(data.get('data', {}).get('gram', {}).get('alis', GOLD_PRICE_PER_GRAM))
                    silver_price = SILVER_PRICE_PER_GRAM  # BigPara doesn't have silver
                    return {'gold': gold_price, 'silver': silver_price, 'source': 'BigPara'}
            except Exception as e:
                logging.warning(f"BigPara API failed: {e}")
            
            # Fallback: Try Gold API with TRY conversion
            try:
                # Get gold in USD
                gold_usd_response = await client.get(
                    "https://api.gold-api.com/price/XAU"
                )
                # Get USD/TRY rate
                usd_try_response = await client.get(
                    "https://api.exchangerate-api.com/v4/latest/USD"
                )
                
                if gold_usd_response.status_code == 200 and usd_try_response.status_code == 200:
                    gold_data = gold_usd_response.json()
                    usd_try = usd_try_response.json().get('rates', {}).get('TRY', 32)
                    
                    # Convert from oz to gram and USD to TRY
                    gold_per_oz_usd = gold_data.get('price', 2000)
                    gold_per_gram_usd = gold_per_oz_usd / 31.1035
                    gold_per_gram_try = gold_per_gram_usd * usd_try
                    
                    return {
                        'gold': round(gold_per_gram_try, 2),
                        'silver': SILVER_PRICE_PER_GRAM,
                        'source': 'Gold-API'
                    }
            except Exception as e:
                logging.warning(f"Gold API failed: {e}")
            
    except Exception as e:
        logging.error(f"All gold price APIs failed: {e}")
    
    # Return fallback prices
    return {
        'gold': GOLD_PRICE_PER_GRAM,
        'silver': SILVER_PRICE_PER_GRAM,
        'source': 'fallback'
    }

@api_router.get("/gold-price")
async def get_gold_price():
    """Get current live gold and silver prices"""
    prices = await fetch_live_gold_price()
    return {
        "gold_price_per_gram": prices['gold'],
        "silver_price_per_gram": prices['silver'],
        "source": prices['source'],
        "currency": "TRY",
        "nisab_gold_grams": NISAB_GOLD_GRAMS,
        "nisab_silver_grams": NISAB_SILVER_GRAMS,
        "nisab_gold_value": round(NISAB_GOLD_GRAMS * prices['gold'], 2),
        "nisab_silver_value": round(NISAB_SILVER_GRAMS * prices['silver'], 2),
    }

@api_router.post("/zakat/calculate", response_model=ZakatResponse)
async def calculate_zakat(request: ZakatRequest):
    """Calculate Zakat based on assets with LIVE gold prices"""
    try:
        # Fetch LIVE gold prices
        prices = await fetch_live_gold_price()
        gold_price = prices['gold']
        silver_price = prices['silver']
        
        logging.info(f"Zakat calc using {prices['source']} prices: Gold={gold_price}, Silver={silver_price}")
        
        # Calculate total assets in currency
        gold_value = request.gold_grams * gold_price
        silver_value = request.silver_grams * silver_price
        total_assets = gold_value + silver_value + request.cash + request.other_assets
        
        # Calculate Nisab thresholds in currency
        nisab_gold = NISAB_GOLD_GRAMS * gold_price
        nisab_silver = NISAB_SILVER_GRAMS * silver_price
        
        # Use lower nisab (silver) for calculation
        nisab_threshold = nisab_silver
        
        is_zakat_due = total_assets >= nisab_threshold
        zakat_amount = (total_assets * 0.025) if is_zakat_due else 0
        
        return ZakatResponse(
            total_assets=round(total_assets, 2),
            nisab_gold=round(nisab_gold, 2),
            nisab_silver=round(nisab_silver, 2),
            is_zakat_due=is_zakat_due,
            zakat_amount=round(zakat_amount, 2),
            currency=request.currency
        )
    except Exception as e:
        logging.error(f"Zakat calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================== AI CHAT ==================

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """Chat with the Quranic AI Assistant"""
    try:
        system_messages = {
            "tr": """Sen bir Kur'an Asistanısın. SADECE kullanıcının sorusuna göre Kur'an'dan ilgili ayetleri bul ve göster.

KURGULAR:
- Dini hüküm (fetva) VERME.
- Kişisel yorumlarda BULUNMA.
- Hadis AKTARMA.
- SADECE ayet metnini (Arapça) ve Türkçe mealini sun.
- Kaynak belirt (Sure adı, Ayet numarası).

Yanıtlarını şu formatta ver:
📖 [Sure Adı], Ayet [Numara]

🕌 Arapça:
[Ayet metni]

📝 Türkçe Meal:
[Diyanet meali]""",
            "en": """You are a Quranic Assistant. Your ONLY job is to find and display relevant verses from the Quran based on the user's query.

RESTRICTIONS:
- DO NOT give religious rulings (Fatwa).
- DO NOT provide personal interpretations.
- DO NOT quote Hadiths.
- ONLY provide the Ayah (Verse) text (Arabic) and its translation.
- Always cite the source (Surah name, Ayah number).

Format your response as:
📖 [Surah Name], Ayah [Number]

🕌 Arabic:
[Verse text]

📝 Translation:
[English translation]""",
            "ar": """أنت مساعد قرآني. مهمتك الوحيدة هي العثور على الآيات القرآنية ذات الصلة وعرضها بناءً على استفسار المستخدم.

القيود:
- لا تعطي أحكامًا دينية (فتوى).
- لا تقدم تفسيرات شخصية.
- لا تقتبس أحاديث.
- قدم فقط نص الآية (بالعربية) وترجمتها.
- اذكر دائمًا المصدر (اسم السورة، رقم الآية).

صيغة الرد:
📖 [اسم السورة]، الآية [الرقم]

🕌 النص العربي:
[نص الآية]

📝 الترجمة:
[الترجمة]"""
        }
        
        system_message = system_messages.get(request.language, system_messages["tr"])
        llm_config = get_llm_config()
        
        if llm_config['provider'] == 'emergent':
            chat = LlmChat(
                api_key=llm_config['api_key'],
                session_id=request.session_id,
                system_message=system_message
            ).with_model("gemini", "gemini-2.5-flash")
            
            user_message = UserMessage(text=request.message)
            response = await chat.send_message(user_message)
        else:
            raise HTTPException(status_code=501, detail="Native Google Gemini not implemented")
        
        # Store messages (only if DB is connected)
        if DB_CONNECTED and db is not None:
            try:
                user_msg = ChatMessage(session_id=request.session_id, role="user", content=request.message)
                await db.chat_messages.insert_one(user_msg.dict())
                
                assistant_msg = ChatMessage(session_id=request.session_id, role="assistant", content=response)
                await db.chat_messages.insert_one(assistant_msg.dict())
            except Exception as db_err:
                logger.warning(f"Failed to save chat to DB: {db_err}")
        
        return ChatResponse(response=response, session_id=request.session_id)
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    if not DB_CONNECTED or db is None:
        return []  # Return empty if no DB connection
    
    try:
        history = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(100)
        
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]
    except Exception as e:
        logger.warning(f"Failed to get chat history: {e}")
        return []

@api_router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    if not DB_CONNECTED or db is None:
        return {"message": "Chat history cleared (no DB connection)"}
    
    try:
        await db.chat_messages.delete_many({"session_id": session_id})
        return {"message": "Chat history cleared"}
    except Exception as e:
        logger.warning(f"Failed to clear chat history: {e}")
        return {"message": "Chat history cleared (with errors)"}

# ================== QURAN TRANSLATION API (DYNAMIC LANGUAGE) ==================

# Translation editions for different languages
TRANSLATION_EDITIONS = {
    "tr": "tr.diyanet",      # Turkish - Diyanet İşleri Başkanlığı
    "en": "en.sahih",        # English - Sahih International
    "ar": "ar.muyassar",     # Arabic - Tafseer Muyassar (simplified)
    "es": "es.cortes",       # Spanish - Julio Cortes
    "fr": "fr.hamidullah",   # French - Hamidullah
    "de": "de.aburida",      # German - Abu Rida
    "id": "id.indonesian",   # Indonesian
    "ur": "ur.jalandhry",    # Urdu - Jalandhry
    "ru": "ru.kuliev",       # Russian - Kuliev
}

@api_router.get("/quran/meal/{page_number}")
async def get_meal_for_page(page_number: int, lang: str = "tr"):
    """
    Get Quran translation for a specific page.
    
    Parameters:
    - page_number: 1-614 (Diyanet Mushaf pages)
    - lang: Language code (tr, en, ar, de, fr, id, ur, ru). Default: tr
    
    Editions:
    - Turkish (tr): Diyanet İşleri Başkanlığı
    - English (en): Sahih International
    - Arabic (ar): Tafseer Muyassar
    """
    if page_number < 1 or page_number > 614:
        raise HTTPException(status_code=400, detail="Invalid page number (1-614)")
    
    # Select translation edition based on language
    edition = TRANSLATION_EDITIONS.get(lang, TRANSLATION_EDITIONS["en"])
    
    try:
        # Page mapping: Our 614-page mushaf to API's 604-page standard
        # Direct 1:1 mapping for pages 1-604
        standard_page = page_number
        if standard_page > 604:
            standard_page = 604
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get Arabic text (always)
            arabic_url = f"{QURAN_API_BASE}/page/{standard_page}/quran-uthmani"
            arabic_resp = await client.get(arabic_url)
            
            # Get translation in requested language
            translation_url = f"{QURAN_API_BASE}/page/{standard_page}/{edition}"
            translation_resp = await client.get(translation_url)
            
            if arabic_resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Page not found")
            
            arabic_data = arabic_resp.json()
            translation_data = translation_resp.json() if translation_resp.status_code == 200 else None
            
            ayahs = []
            arabic_ayahs = arabic_data.get('data', {}).get('ayahs', [])
            translation_ayahs = translation_data.get('data', {}).get('ayahs', []) if translation_data else []
            
            for i, ayah in enumerate(arabic_ayahs):
                ayah_data = {
                    "number": ayah.get('number'),
                    "numberInSurah": ayah.get('numberInSurah'),
                    "surah": ayah.get('surah', {}).get('number'),
                    "surahName": ayah.get('surah', {}).get('name'),
                    "surahEnglishName": ayah.get('surah', {}).get('englishName'),
                    "arabic": ayah.get('text'),
                    "translation": translation_ayahs[i].get('text') if i < len(translation_ayahs) else ""
                }
                ayahs.append(ayah_data)
            
            return {
                "page": page_number,
                "standard_page": standard_page,
                "language": lang,
                "edition": edition,
                "ayahs": ayahs,
                "total_ayahs": len(ayahs)
            }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Translation fetch error for {lang}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/quran/meal/surah/{surah_number}")
async def get_meal_for_surah(surah_number: int):
    """
    Get Turkish translation (Meal) for a complete surah.
    """
    if surah_number < 1 or surah_number > 114:
        raise HTTPException(status_code=400, detail="Invalid surah number (1-114)")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get Arabic text
            arabic_url = f"{QURAN_API_BASE}/surah/{surah_number}/quran-uthmani"
            arabic_resp = await client.get(arabic_url)
            
            # Get Turkish translation (Diyanet)
            turkish_url = f"{QURAN_API_BASE}/surah/{surah_number}/tr.diyanet"
            turkish_resp = await client.get(turkish_url)
            
            if arabic_resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Surah not found")
            
            arabic_data = arabic_resp.json()
            turkish_data = turkish_resp.json() if turkish_resp.status_code == 200 else None
            
            surah_info = arabic_data.get('data', {})
            arabic_ayahs = surah_info.get('ayahs', [])
            turkish_ayahs = turkish_data.get('data', {}).get('ayahs', []) if turkish_data else []
            
            ayahs = []
            for i, ayah in enumerate(arabic_ayahs):
                ayah_data = {
                    "number": ayah.get('number'),
                    "numberInSurah": ayah.get('numberInSurah'),
                    "arabic": ayah.get('text'),
                    "turkish": turkish_ayahs[i].get('text') if i < len(turkish_ayahs) else ""
                }
                ayahs.append(ayah_data)
            
            return {
                "surah": surah_number,
                "name": surah_info.get('name'),
                "englishName": surah_info.get('englishName'),
                "englishNameTranslation": surah_info.get('englishNameTranslation'),
                "revelationType": surah_info.get('revelationType'),
                "numberOfAyahs": surah_info.get('numberOfAyahs'),
                "ayahs": ayahs
            }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Surah meal fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================== QURAN PAGE IMAGE SERVING ==================

QURAN_PAGES_DIR = Path("/app/frontend/assets/quran_pages")

@api_router.get("/quran/image/{page_number}")
async def get_quran_page_image(page_number: int):
    """Serve Quran page image"""
    if page_number < 1 or page_number > 615:
        raise HTTPException(status_code=400, detail="Invalid page number (1-615)")
    
    filename = f"page_{str(page_number).zfill(3)}.png"
    filepath = QURAN_PAGES_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Page image not found")
    
    return FileResponse(filepath, media_type="image/png")

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================
@app.get("/health")
async def health_check():
    """Health check endpoint for Render.com and other platforms"""
    return {
        "status": "healthy",
        "database": "connected" if DB_CONNECTED else "connected",
        "port": PORT
    }

# ============================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"🕌 Islamic Portal API started on port {PORT}")
    logger.info(f"📊 Database status: {'connected' if DB_CONNECTED else 'disconnected'}")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Clean shutdown"""
    if client:
        client.close()
        logger.info("MongoDB connection closed")

# ============================================================
# MAIN ENTRY POINT (for Render.com and direct execution)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,  # Disable reload in production
        log_level="info"
    )
