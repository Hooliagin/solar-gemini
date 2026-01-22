"""
News service using the NEW google-genai SDK with Google Search Grounding.
"""
from google import genai
from google.genai import types
from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize client with API key
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def fetch_detailed_news_per_topic(topics: list[str]) -> str:
    """
    Performs separate news searches for EACH topic using Google Search Grounding.
    Uses the new google-genai SDK for live web search.
    """
    if not topics or len(topics) == 0:
        return "Keine News-Topics konfiguriert."
    
    results = []
    
    # Google Search grounding tool
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])
    
    for topic in topics:
        try:
            prompt = (
                f"Suche nach den neuesten Entwicklungen und News zu '{topic}' der letzten 24 Stunden. "
                f"Fokus auf:\n"
                f"- Was ist NEU passiert seit gestern?\n"
                f"- Wichtige Ereignisse, Ankündigungen oder Durchbrüche\n\n"
                f"Erstelle eine kompakte Zusammenfassung (2-3 Sätze) im Briefing-Stil."
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


def fetch_general_news_briefing() -> str:
    """
    Generates a general news briefing using Google Search Grounding.
    """
    try:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])
        
        prompt = (
            "Erstelle ein 3-Minuten-News-Briefing für heute mit folgenden Bereichen:\n\n"
            "1. **Politik** (Deutschland/International): Top 2 wichtigste Entwicklungen seit gestern\n"
            "2. **Wirtschaft**: DAX-Entwicklung + 1 relevante Wirtschaftsnachricht\n"
            "3. **Technologie/Wissenschaft**: 1 interessanter Durchbruch oder Trend\n\n"
            "Stil: Kompakt, sachlich, für gebildete Hörer. Keine Sensationen, nur Relevantes.\n"
            "Fokus: Ereignisse der letzten 24 Stunden."
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        
        if response.text:
            return response.text.strip()
        else:
            return "Allgemeine News konnten nicht abgerufen werden."
            
    except Exception as e:
        logger.error(f"General news fetch failed: {e}")
        return "Fehler beim Abrufen allgemeiner News."


# Legacy function for backward compatibility
def fetch_ai_news_summary(topics: list[str] = None):
    """DEPRECATED: Use fetch_detailed_news_per_topic instead."""
    logger.warning("fetch_ai_news_summary is deprecated, use fetch_detailed_news_per_topic")
    return fetch_detailed_news_per_topic(topics if topics else ["AI", "Tech"])
