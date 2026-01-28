"""
News service using the NEW google-genai SDK with Google Search Grounding.
Supports predefined categories + custom user interests.
"""
from google import genai
from google.genai import types
from config import settings
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize client with API key
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# Predefined news categories
PREDEFINED_CATEGORIES = {
    'news_politics': {
        'name': 'Politik',
        'prompt': 'aktuelle politische Nachrichten aus Deutschland und international'
    },
    'news_local': {
        'name': 'Lokale News',
        'prompt': 'lokale Nachrichten und Ereignisse aus {city}'  # city will be replaced
    },
    'news_economy': {
        'name': 'Wirtschaft',
        'prompt': 'Wirtschaftsnachrichten, DAX, Aktienmärkte und Unternehmensnews'
    },
    'news_tech': {
        'name': 'Technologie',
        'prompt': 'Technologie-News, KI, Startups und digitale Innovationen'
    },
    'news_sports': {
        'name': 'Sport',
        'prompt': 'Sportnachrichten, Fußball Bundesliga, internationale Wettkämpfe'
    }
}


def fetch_category_news(category_key: str, city: str = None) -> str:
    """
    Fetches news for a predefined category.
    """
    if category_key not in PREDEFINED_CATEGORIES:
        return ""
    
    category = PREDEFINED_CATEGORIES[category_key]
    topic = category['prompt']
    
    # Replace city placeholder for local news
    if category_key == 'news_local' and city:
        topic = topic.format(city=city)
    elif category_key == 'news_local':
        topic = topic.format(city="Deutschland")
    
    try:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])
        
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        prompt = (
            f"Suche nach den neuesten Entwicklungen zu: {topic}\n"
            f"HEUTIGES DATUM: {today_str}.\n"
            f"REGEL: Wähle NUR Nachrichten, die HEUTE oder GESTERN passiert sind (letzte 24-48h).\n"
            f"VERBOTEN: Alles was vor dem {today_str} (minus 1 Tag) passiert ist.\n"
            f"VERBOTEN: Polizeimeldungen, Unfälle oder Kleinigkeiten, es sei denn sie sind von nationaler Relevanz.\n"
            f"Erstelle eine Zusammenfassung mit 3-4 Sätzen im Briefing-Stil. "
            f"Nenne konkrete Ereignisse, Namen und Fakten. "
            f"Wenn keine aktuellen News vorliegen, antworte AUSSCHLIESSLICH mit 'Keine aktuellen News'. Erfinde nichts und nimm nichts Altes."
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        
        if response.text:
            return f"**{category['name']}:**\n{response.text.strip()}\n"
        else:
            return f"**{category['name']}:**\nKeine Updates verfügbar.\n"
            
    except Exception as e:
        logger.error(f"Category news fetch failed for '{category_key}': {e}")
        return f"**{category['name']}:**\nFehler beim Abrufen.\n"


def fetch_detailed_news_per_topic(topics: list[str]) -> str:
    """
    Performs separate news searches for EACH custom user topic using Google Search Grounding.
    """
    if not topics or len(topics) == 0:
        return ""
    
    results = []
    
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])
    
    for topic in topics:
        try:
            today_str = datetime.now().strftime("%d.%m.%Y")
            
            prompt = (
                f"Suche nach den neuesten Entwicklungen und News zu '{topic}' vom {today_str} (oder letzte 24h). "
                f"Was ist NEU passiert? Wichtige Ereignisse oder Durchbrüche?\n\n"
                f"STRIKTE REGEL: Ignoriere alles was älter als 24 Stunden ist.\n"
                f"Erstelle eine Zusammenfassung mit 3-4 Sätzen im Briefing-Stil. "
                f"Wenn keine aktuellen News vorliegen, antworte AUSSCHLIESSLICH mit 'Keine Updates'."
            )
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            
            if response.text:
                results.append(f"**{topic}:**\n{response.text.strip()}\n")
            else:
                results.append(f"**{topic}:**\nKeine Updates verfügbar.\n")
                
        except Exception as e:
            logger.error(f"News fetch failed for topic '{topic}': {e}")
            results.append(f"**{topic}:**\nFehler beim Abrufen der News.\n")
    
    return "\n".join(results)


def fetch_all_news(user_settings, custom_topics: list[str] = None) -> str:
    """
    Fetches all enabled news categories + custom topics.
    Returns combined news string.
    """
    curated_list = []
    dynamic_list = []
    city = user_settings.weather_city if user_settings else None
    
    # Fetch predefined categories (Curated)
    if user_settings:
        if user_settings.news_politics:
            print("DEBUG: Fetching Politics...", flush=True)
            curated_list.append(fetch_category_news('news_politics'))
        if user_settings.news_local:
            print(f"DEBUG: Fetching Local ({city})...", flush=True)
            curated_list.append(fetch_category_news('news_local', city))
        if user_settings.news_economy:
            print("DEBUG: Fetching Economy...", flush=True)
            curated_list.append(fetch_category_news('news_economy'))
        if user_settings.news_tech:
            print("DEBUG: Fetching Tech...", flush=True)
            curated_list.append(fetch_category_news('news_tech'))
        if user_settings.news_sports:
            print("DEBUG: Fetching Sports...", flush=True)
            curated_list.append(fetch_category_news('news_sports'))
    
    # Fetch custom user interests (Dynamic)
    if custom_topics:
        print(f"DEBUG: Fetching {len(custom_topics)} Custom Topics...", flush=True)
        # Reuse existing function but treat result as dynamic list items
        custom_news_str = fetch_detailed_news_per_topic(custom_topics)
        if custom_news_str:
            dynamic_list.append(custom_news_str)
    
    print("DEBUG: News Content Assembled (Split).", flush=True)
    
    curated_text = "\n".join(filter(None, curated_list)) or "Keine allgemeinen News-Kategorien aktiviert."
    dynamic_text = "\n".join(filter(None, dynamic_list)) or "Keine persönlichen Themen definiert."
    
    return curated_text, dynamic_text


# Legacy function for backward compatibility
def fetch_ai_news_summary(topics: list[str] = None):
    """DEPRECATED: Use fetch_all_news instead."""
    logger.warning("fetch_ai_news_summary is deprecated")
    return fetch_detailed_news_per_topic(topics if topics else ["AI", "Tech"])
