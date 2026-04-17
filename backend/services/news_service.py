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
    Fetches news for a predefined category (short ticker-style summary).
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
            f"Suche nach den absolut neuesten Entwicklungen (letzte 24 Stunden) zu: {topic}\n"
            f"HEUTIGES DATUM: {today_str}.\n"
            f"FOKUS: Was ist HEUTE passiert? Wenn heute noch nichts vorliegt, nimm GESTERN.\n"
            f"STRIKTE REGEL: Alles was älter als 36 Stunden ist, ist VERBOTEN.\n"
            f"VERBOTEN: Polizeimeldungen, Unfälle oder Belanglosigkeiten.\n"
            f"Erstelle eine Zusammenfassung mit 2-3 Sätzen im Briefing-Stil.\n"
            f"Wenn keine brandaktuellen News vorliegen, antworte AUSSCHLIESSLICH mit 'Keine aktuellen News'."
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


def fetch_interest_section(topic: str) -> str:
    """
    Tiefgehender Zeitungs-Artikel zu einem persönlichen Interesse.
    Liefert Schlagzeile, 1-2 konkrete Entwicklungen mit Zahlen/Namen,
    Hintergrund und Relevanz - wie eine kuratierte Zeitungs-Sektion.
    """
    if not topic or not topic.strip():
        return ""

    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])

    today_str = datetime.now().strftime("%d.%m.%Y")

    prompt = (
        f"Du bist Ressort-Redakteur einer hochwertigen Tageszeitung. "
        f"Das Ressort heißt '{topic}'. Heutiges Datum: {today_str}.\n\n"
        f"RECHERCHE-AUFTRAG:\n"
        f"Finde die 1-2 WICHTIGSTEN, konkretesten Entwicklungen der letzten 24-48 Stunden zu '{topic}'. "
        f"Suche nach Eigennamen, Zahlen, Zitaten, konkreten Ereignissen - nicht nach allgemeinen Trends.\n\n"
        f"HARTE REGELN:\n"
        f"- Alles älter als 48 Stunden: VERBOTEN.\n"
        f"- Keine generischen 'Trend'-Floskeln ohne konkreten Anlass.\n"
        f"- Jede Behauptung muss auf eine konkrete Quelle/Ereignis zurückführbar sein.\n"
        f"- Keine Polizeimeldungen, Klatsch oder Banalitäten.\n\n"
        f"AUSGABE-FORMAT (strikt einhalten, als reiner Text ohne Markdown):\n"
        f"SCHLAGZEILE: <eine prägnante Zeile, was HEUTE/GESTERN passiert ist>\n"
        f"KERN: <3-4 Sätze mit den konkreten Fakten: wer, was, wann, wo, wieviel. "
        f"Nenne Namen, Zahlen, Orte, Zitate. Kein Geschwafel.>\n"
        f"HINTERGRUND: <1-2 Sätze Einordnung: warum passiert das gerade, was ist der Kontext, "
        f"was ist neu gegenüber vorher.>\n"
        f"RELEVANZ: <1 Satz: warum lohnt es sich für jemanden mit Interesse an '{topic}', "
        f"das heute zu wissen - konkrete Implikation, kein Allgemeinplatz.>\n\n"
        f"Wenn KEINE konkreten News der letzten 48h existieren: antworte AUSSCHLIESSLICH mit 'KEINE_NEWS'."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )

        text = (response.text or "").strip()
        if not text or "KEINE_NEWS" in text.upper()[:40]:
            return f"**{topic}:**\nHeute keine relevanten neuen Entwicklungen.\n"

        return f"**Ressort: {topic}**\n{text}\n"

    except Exception as e:
        logger.error(f"Interest section fetch failed for '{topic}': {e}")
        return f"**{topic}:**\nFehler beim Abrufen.\n"


def fetch_detailed_news_per_topic(topics: list[str]) -> str:
    """
    Erstellt für JEDES persönliche Interesse eine eigene Zeitungs-Sektion
    mit Schlagzeile, Kern-Fakten, Hintergrund und Relevanz.
    """
    if not topics or len(topics) == 0:
        return ""

    results = []
    for topic in topics:
        results.append(fetch_interest_section(topic))

    return "\n".join(filter(None, results))


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
