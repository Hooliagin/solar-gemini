import google.generativeai as genai
from config import settings
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

def fetch_detailed_news_per_topic(topics: list[str]) -> str:
    """
    Performs separate news searches for EACH topic with focus on last 24 hours.
    Returns a structured summary with one section per topic.
    """
    if not topics or len(topics) == 0:
        return "Keine News-Topics konfiguriert."
    
    results = []
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    for topic in topics:
        try:
            prompt = (
                f"Suche nach den neuesten Entwicklungen zu '{topic}' der letzten 24 Stunden. "
                f"Fokus auf:\n"
                f"- Was ist NEU passiert seit gestern?\n"
                f"- Wichtige Ereignisse, Ankündigungen oder Durchbrüche\n"
                f"- Qualitätsquellen bevorzugen (keine Clickbait)\n\n"
                f"Erstelle eine kompakte Zusammenfassung (2-3 Sätze) im Briefing-Stil. "
                f"Falls nichts Relevantes gefunden wurde, sage: 'Keine bedeutenden Updates zu {topic}.'"
            )
            
            # Use google_search tool (dict format for google.generativeai SDK)
            tools = [{'google_search': {}}]
            response = model.generate_content(prompt, tools=tools)
            
            if response.text:
                results.append(f"**{topic}:**\n{response.text.strip()}\n")
            else:
                results.append(f"**{topic}:**\nKeine Updates verfügbar.\n")
                
        except Exception as e:
            logger.error(f"News fetch failed for topic '{topic}': {e}")
            results.append(f"**{topic}:**\nFehler beim Abrufen der News.\n")
    
    return "\n".join(results)


def fetch_general_news_briefing() -> str:
    """
    Optional: Generates a general news briefing covering politics, economy, and tech.
    Called only if user has general_news_enabled = True.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = (
            "Erstelle ein 3-Minuten-News-Briefing für heute mit folgenden Bereichen:\n\n"
            "1. **Politik** (Deutschland/International): Top 2 wichtigste Entwicklungen seit gestern\n"
            "2. **Wirtschaft**: DAX-Entwicklung + 1 relevante Wirtschaftsnachricht\n"
            "3. **Technologie/Wissenschaft**: 1 interessanter Durchbruch oder Trend\n\n"
            "Stil: Kompakt, sachlich, für gebildete Hörer. Keine Sensationen, nur Relevantes.\n"
            "Fokus: Ereignisse der letzten 24 Stunden."
        )
        
        # Use google_search tool (dict format for google.generativeai SDK)
        tools = [{'google_search': {}}]
        response = model.generate_content(prompt, tools=tools)
        
        if response.text:
            return response.text.strip()
        else:
            return "Allgemeine News konnten nicht abgerufen werden."
            
    except Exception as e:
        logger.error(f"General news fetch failed: {e}")
        return "Fehler beim Abrufen allgemeiner News."


# Legacy function for backward compatibility
def fetch_ai_news_summary(topics: list[str] = None):
    """
    DEPRECATED: Use fetch_detailed_news_per_topic instead.
    Kept for compatibility during migration.
    """
    logger.warning("fetch_ai_news_summary is deprecated, use fetch_detailed_news_per_topic")
    return fetch_detailed_news_per_topic(topics if topics else ["AI", "Tech"])
