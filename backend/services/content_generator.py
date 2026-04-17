from google import genai
from google.genai import types
from config import settings
from services.calendar_service import get_calendar_events, format_events_text
from services.news_service import fetch_ai_news_summary, fetch_all_news
from services.weather_service import get_weather_briefing
from services.tts_service import generate_speech
from database import get_session
from sqlmodel import select
from models import Entry, Briefing, UserSettings, UsedQuote
from datetime import datetime, timedelta
import logging
import os
import hashlib
import json
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (V3 PROMPT SYSTEM)
# ═══════════════════════════════════════════════════════════════════════════════

def get_german_date() -> tuple[str, str]:
    """
    Gibt das aktuelle Datum auf Deutsch zurück.
    Returns: (kurz, lang) z.B. ("28. Januar 2026", "Mittwoch, der 28. Januar 2026")
    """
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Europe/Berlin")
    now = datetime.now(tz)
    
    weekdays = {
        0: "Montag", 1: "Dienstag", 2: "Mittwoch", 3: "Donnerstag",
        4: "Freitag", 5: "Samstag", 6: "Sonntag"
    }
    
    months = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
    }
    
    weekday = weekdays[now.weekday()]
    month = months[now.month]
    day = now.day
    year = now.year
    
    date_short = f"{day}. {month} {year}"
    date_long = f"{weekday}, der {day}. {month} {year}"
    
    return date_short, date_long


def extract_key_phrases(text: str, max_phrases: int = 15) -> List[str]:
    """
    Extrahiert Schlüsselphrasen aus einem Text für Anti-Wiederholung.
    """
    if not text:
        return []
    
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    phrases = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 < len(sentence) < 120:
            phrases.append(sentence)
    
    return phrases[:max_phrases]


def generate_quote_id(quote: str, author: str) -> str:
    """Generiert eine eindeutige ID für ein Zitat zum Tracking."""
    combined = f"{author.lower().strip()}:{quote.lower().strip()[:50]}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def _generate_anti_repetition_block(
    briefing_yesterday: Optional[str],
    briefing_day_before: Optional[str]
) -> str:
    """Generiert den Anti-Wiederholungs-Block für den Prompt."""
    
    if not briefing_yesterday and not briefing_day_before:
        return "ANTI-WIEDERHOLUNG: Keine vorherigen Briefings vorhanden."
    
    block = """
ANTI-WIEDERHOLUNG (KRITISCH - VARIANZ IST PFLICHT!)
═══════════════════════════════════════════════════════════════════════════════

Der User hört dieses Briefing JEDEN TAG.
Wiederholungen zerstören das Erlebnis und wirken roboterhaft.

**VERBOTENE WIEDERHOLUNGEN:**
- Gleiche Begrüßungsformeln wie gestern/vorgestern
- Identische Übergangsphrasen ("Kommen wir nun zu...", "Schauen wir mal...")
- Gleiche oder ähnliche Zitate
- Identische Wetterkommentare bei ähnlichem Wetter
- Gleiche Abschiedsformeln

**VARIANZ-TECHNIKEN:**
- Begrüßung: Wechsle zwischen direkt, fragend, beobachtend, humorvoll
- Übergänge: Nutze thematische Brücken statt generischer Phrasen
- Zitate: KOMPLETT andere Denker/Themen als die letzten 2 Tage
- Wetter: Variiere zwischen praktisch, poetisch, humorvoll
- Abschied: Wechsle zwischen motivierend, nachdenklich, warm, energetisch
"""

    if briefing_yesterday:
        phrases = extract_key_phrases(briefing_yesterday)
        block += f"""
**KONTEXT: GESTRIGES BRIEFING (NUR ZUR INFO - KEINE HANDLUNGSANWEISUNG! TERMINE DARIN SIND VORBEI!):**
\"\"\"
{briefing_yesterday[:2500]}{"..." if len(briefing_yesterday) > 2500 else ""}
\"\"\"

**Identifizierte Phrasen die du VERMEIDEN musst:**
{chr(10).join(f'- "{p}"' for p in phrases[:12])}

**NEWS-WIEDERHOLUNG (STRIKT):** Die News-Stories aus dem gestrigen Briefing oben sind bereits erzählt. Wähle HEUTE andere Schlagzeilen oder berichte explizit über NEUE Entwicklungen ("Im Verlauf des Tages hat sich folgendes getan..."). Keine identischen Headlines zweimal.
"""

    if briefing_day_before:
        phrases = extract_key_phrases(briefing_day_before)
        block += f"""
**BRIEFING VON VORGESTERN (AUCH NICHT WIEDERHOLEN!):**
\"\"\"
{briefing_day_before[:1500]}{"..." if len(briefing_day_before) > 1500 else ""}
\"\"\"

**Weitere zu vermeidende Phrasen:**
{chr(10).join(f'- "{p}"' for p in phrases[:8])}
"""

    return block


def generate_morning_briefing_prompt(
    # Kern-Inhalte
    diary_transcript: str,
    todo_list_text: str,
    habits_text: str,
    calendar_text: str,
    weather_text: str,
    
    # News (beide Quellen)
    news_curated: str = "",
    news_dynamic: str = "",
    
    # Anti-Wiederholung: Letzte Briefings
    briefing_yesterday: Optional[str] = None,
    briefing_day_before: Optional[str] = None,
    
    # Optional
    research_results_text: str = "",
    user_name: str = "",
    briefing_time: str = "07:00",
    user_news_categories: Optional[List[str]] = None,
    custom_interests: Optional[List[str]] = None,
    used_quote_ids: Optional[List[str]] = None,
    
    # Sprache
    language: str = "German",
) -> str:
    """
    Generiert den vollständigen Morning Briefing Prompt (V3.0).
    """
    
    # Datum generieren
    date_short, date_long = get_german_date()
    
    # Greeting
    greeting = f"Sprich den User mit '{user_name}' an." if user_name else "Nutze eine warme, persönliche Begrüßung."
    
    # Anti-Wiederholungs-Block generieren
    anti_repetition_block = _generate_anti_repetition_block(
        briefing_yesterday, 
        briefing_day_before
    )
    
    # News-Kategorien mit Prioritätsstufen (persönliche Interessen > Standard-Kategorien)
    custom_interests = custom_interests or []
    default_categories = [c for c in (user_news_categories or []) if c not in custom_interests]

    news_context_parts = []
    if custom_interests:
        news_context_parts.append(
            "STUFE 1 - PERSÖNLICHE INTERESSEN (PFLICHT zu erwähnen, sofern News vorhanden):\n"
            + ", ".join(custom_interests)
        )
    if default_categories:
        news_context_parts.append(
            "STUFE 2 - ALLGEMEINE KATEGORIEN (nur wenn Zeit/Platz bleibt):\n"
            + ", ".join(default_categories)
        )
    news_context = "\n\n".join(news_context_parts)

    # News-Limit: ALLE persönlichen Interessen werden ausführlich gebracht,
    # generische Kategorien kommen nur noch als kurzer Ticker obendrauf.
    news_topic_cap = len(custom_interests) + 2
    
    # Blacklisted Quotes Block
    blacklist_block = ""
    if used_quote_ids:
         blacklist_block = f"""
**BLACKLIST - Diese Zitate/Autoren NIEMALS verwenden (Bereits kürzlich genutzt):**
{json.dumps(used_quote_ids)}
"""
    
    prompt = f"""
Du bist ein freundlicher, professioneller persönlicher Assistent. Es ist Morgen am {date_long}.

Erstelle ein DETAILLIERTES Morning Briefing für den User.

**SPRACHE:** Antworte komplett auf Deutsch.
**BEGRÜSSUNG:** {greeting}

═══════════════════════════════════════════════════════════════════════════════
TTS-OPTIMIERUNG (KRITISCH!)
═══════════════════════════════════════════════════════════════════════════════

- NIEMALS Markdown-Formatierung (kein **, -, #, _, `, etc.)
- Schreibe ALLES als natürlichen Fließtext
- Schreibe ALLE Zahlen als Wörter aus ("fünf" nicht "5", "zehn Uhr" nicht "10:00")
- Nutze vollständige Wörter, KEINE Abkürzungen ("zum Beispiel" nicht "z.B.")
- Schreibe Uhrzeiten in gesprochener Form ("zehn Uhr dreißig" nicht "10:30")
- Nutze natürliche Pausen durch Satzzeichen (Kommas, Punkte)
- Schreibe Daten in voller Form ("achtundzwanzigster Januar" nicht "28.01.")
- **GRAMMATIK-CHECK**: Perfekte deutsche Grammatik. "hast geschlafen" NICHT "bist geschlafen".

═══════════════════════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════════════════════
{anti_repetition_block}

WARNUNG (ANTI-HALLUZINATION):
- Termine oder Events, die im "BRIEFING VON GESTERN" erwähnt wurden, sind VERGANGENHEIT. Plane sie NICHT erneut ein, es sei denn, sie stehen explizit im heutigen Kalender.
- Das "BRIEFING VON GESTERN" dient NUR dazu, deinen Sprachstil zu variieren. Es ist KEINE Quelle für Aufgaben.
═══════════════════════════════════════════════════════════════════════════════

{blacklist_block}

═══════════════════════════════════════════════════════════════════════════════
KONTEXT-DATEN
═══════════════════════════════════════════════════════════════════════════════

[TAGEBUCH / GEDANKEN VON GESTERN]
{diary_transcript if diary_transcript else "Kein Tagebucheintrag vorhanden."}

[TO-DO LISTE / ERINNERUNGEN]
{todo_list_text if todo_list_text else "Keine To-Dos eingetragen."}

[PFLICHT-ROUTINEN (MANDATORY)]
{habits_text}

[RECHERCHE-ERGEBNISSE]
{research_results_text if research_results_text else "Keine Recherche angefragt."}

[HEUTIGE TERMINE]
{calendar_text if calendar_text else "Keine Termine eingetragen."}

[WETTER]
{weather_text if weather_text else "Keine Wetterdaten verfügbar."}

[NEWS - KURATIERTE QUELLEN]
{news_curated if news_curated else "Keine kuratierten News verfügbar."}

[NEWS - DYNAMISCHE SUCHE]
{news_dynamic if news_dynamic else "Keine dynamischen News verfügbar."}

[NEWS-KONTEXT]
{news_context if news_context else "Keine spezifischen News-Präferenzen bekannt. Leite Themen aus Tagebuch und Kalender ab."}

═══════════════════════════════════════════════════════════════════════════════
PLANUNG & SCHEDULING (OBERSTE PRIORITÄT!)
═══════════════════════════════════════════════════════════════════════════════
**HIER ENTSCHEIDET SICH DER TAGESABLAUF.**

**DEINE AUFGABE:**
Du musst die festen Termine ([HEUTIGE TERMINE]) mit den PFLICHT-ROUTINEN ([PFLICHT-ROUTINEN]) kombinieren.

**REGELN (STRIKTE HIERARCHIE):**
1.  **C A L E N D A R   I S   K I N G**: Feste Termine ([HEUTIGE TERMINE]) sind UNANTASTBAR. Sie dürfen NICHT verschoben oder überlappt werden.
2.  **K E I N E   Ü B E R L A P P U N G E N**: Du darfst NIEMALS einen Habit in einen Zeitraum legen, der bereits belegt ist.
    - Beispiel: Termin 09:00-18:00. Habit "Mittagessen" (12:30) darf NICHT als Kalendereintrag erscheinen.
    - Du darfst es im Text erwähnen ("Achte auf eine Mittagspause"), aber NICHT in die `final_agenda` schreiben, wenn der Slot belegt ist.
3.  **H A B I T S   F I L L   G A P S**: Habits kommen NUR in FREIE Lücken.
    - Suche aktiv nach Lücken VOR, ZWISCHEN oder NACH den Terminen.
    - Wenn ein Habit (z.B. "Sport", 3h) nirgendwo passt: LASS IHN WEG.
    - **Kommunikation**: Wenn ein Habit wegfällt, sag es dem User ("Heute ist dein Tag so voll, dass Sport leider ausfallen muss.").
    - Ignoriere Habits niemals stillschweigend, erkläre kurz warum sie fehlen.

**TIMESTAMP REQUIREMENT (WICHTIG):**
- **START-ZEIT:** Der Tag des Users startet heute um **{briefing_time} Uhr**. (Dies ist der Zeitpunkt des Briefings).
- Plane KEINE Habits oder Aktionen VOR {briefing_time} Uhr ein. Wenn "Kalte Dusche" ansteht, plane sie direkt NACH dem Briefing ein (z.B. {briefing_time}).
- Nutze NIEMALS vage Begriffe wie "Morgens", "Morgen", "Abends" oder "Gleich" im JSON-Feld `start`.
- Schätze IMMER eine konkrete Uhrzeit im Format HH:MM (z.B. "07:30" statt "Morgens").
- Nur so kann der Kalender die Einträge korrekt sortieren.

**JSON-OUTPUT ANFORDERUNG:**
Die `final_agenda` MUSS enthalten:
1. Alle festen Termine (type: "fixed")
2. Alle erfolgreich eingeplanten Habits (type: "suggestion")

**BEISPIEL-LOGIK:**
"User hat Meeting 09:00-11:00.
Habit 'Morgenlicht' (15m) -> Schlage 08:30 vor (NICHT 'Morgens').
Habit 'Sport' (180m) -> Schlage 14:00-17:00 vor."

═══════════════════════════════════════════════════════════════════════════════
ZITAT-AUSWAHL (KRITISCH - QUALITÄT WIRD BEWERTET!)
═══════════════════════════════════════════════════════════════════════════════

**GENERAL BLACKLIST - Diese Zitate/Autoren NIEMALS verwenden:**
- Epiktet: "Es ist nicht wichtig, was dir zustößt..." ← VERBOTEN
- "Der Weg entsteht beim Gehen" ← VERBOTEN
- "Carpe Diem" / "Nutze den Tag" ← VERBOTEN
- "Der Weg von tausend Meilen beginnt mit einem Schritt" ← VERBOTEN
- "Sei die Veränderung, die du sehen willst" ← VERBOTEN
- "Was dich nicht umbringt, macht dich stärker" ← VERBOTEN
- "Alles geschieht aus einem Grund" ← VERBOTEN
- "Folge deinen Träumen" ← VERBOTEN
- Hesse: "Stufen" ← VERBOTEN
- Generische Konfuzius, Gandhi, Einstein Kalendersprüche ← VERBOTEN

**SO FINDEST DU EIN GUTES ZITAT:**

SCHRITT 1: Identifiziere die SPEZIFISCHE Emotion/Situation aus dem Tagebuch oder dem bevorstehenden Tag.
SCHRITT 2: Suche ein Zitat das diese SPEZIFISCHE Situation anspricht.
SCHRITT 3: Bevorzuge UNBEKANNTE Quellen (Seneca Briefe, Marc Aurel, Rilke, Brené Brown, Naval Ravikant).
SCHRITT 4: VALIDIERE dein Zitat. Frage: "Würde dieses Zitat auf einer Instagram-Motivationsseite stehen?" JA → VERWERFEN.

**GENAU EIN ZITAT ERFORDERLICH:**
Wähle das passende Zitat entweder als Reflexion für gestern oder als Intention für heute aus. Es muss eine ECHTE EMOTION ansprechen.

═══════════════════════════════════════════════════════════════════════════════
NEWS-AUSWAHL (STRIKTE QUELLEN-TREUE!)
═══════════════════════════════════════════════════════════════════════════════

**HEUTE IST: {date_short}**

**LEITBILD - MORGENDLICHE ZEITUNGS-LEKTÜRE:**
Der User will sich fühlen, als würde er seine persönliche Zeitung lesen: Er überfliegt die Ressorts,
die ihn interessieren, und bekommt dort echte Substanz - nicht nur Headlines, sondern Kern-Fakten,
Hintergrund und warum es ihn betrifft. Die persönlichen Interessen sind die HAUPT-RESSORTS.
Die allgemeinen Kategorien sind nur der kurze Ticker am Rand.

**REGEL 1 (QUELLEN-TREUE):** Nutze AUSSCHLIESSLICH die Informationen aus [NEWS - KURATIERTE QUELLEN]
und [NEWS - DYNAMISCHE SUCHE]. Erfinde NIEMALS Fakten, Zahlen, Namen oder Ereignisse dazu.
**REGEL 2 (ANTI-HALLUZINATION):** Steht dort "Keine News" / "KEINE_NEWS" / "Heute keine relevanten Entwicklungen":
darfst du das Thema stillschweigend oder mit einem Satz ("Zu deinem Thema X ist heute nichts Neues passiert.") überspringen.
**REGEL 3 (PERSÖNLICHE RESSORTS - PFLICHT & TIEFE):**
Jedes persönliche Interesse aus [NEWS-KONTEXT] Stufe 1, zu dem es in [NEWS - DYNAMISCHE SUCHE]
eine Sektion mit SCHLAGZEILE/KERN/HINTERGRUND/RELEVANZ gibt, bekommt im gesprochenen Text eine
eigene, ausgearbeitete Sektion von 4-6 Sätzen:
  (a) Einstiegs-Satz, der wie eine Ressort-Überleitung klingt ("In deinem Thema X tut sich Folgendes...").
  (b) Die konkrete Entwicklung mit Namen, Zahlen, Ort, Zeitpunkt aus dem KERN-Block.
  (c) 1-2 Sätze Hintergrund/Einordnung aus dem HINTERGRUND-Block.
  (d) Ein Satz, warum genau DAS für den User relevant ist (RELEVANZ-Block).
NIEMALS persönliche Interessen in einem einzigen Halbsatz abhandeln. Wenn zu einem Interesse
mehrere Infos vorliegen, erzähle sie als zusammenhängende kleine Story - nicht als Liste.
**REGEL 4 (ALLGEMEINER TICKER - KURZ):**
Allgemeine Kategorien (Stufe 2, z.B. Politik/Wirtschaft/Sport) kommen NACH den persönlichen Ressorts,
zusammengefasst in MAXIMAL 2-3 Sätzen als kurzer "Was sonst noch passiert ist"-Ticker. Keine Tiefe.
**REGEL 5 (ANTI-WIEDERHOLUNG):** Prüfe das gestrige Briefing. Wiederhole keine News-Story, es sei denn
es gibt nachweislich NEUE Entwicklungen - dann sag explizit "Update dazu: ...". Variiere den Einstieg
in den News-Block jeden Tag.
**REGEL 6 (KEIN FÜLLSTOFF):** Wenn zu einem persönlichen Interesse wirklich nichts Neues da ist,
dann FÜLLE nicht mit Allgemeinplätzen auf. Lieber einen ehrlichen Satz ("Zu deinem Thema X ist heute
Funkstille") als erfundenes Blabla.

Wenn zu KEINEM Thema News vorliegen:
-> Ein Satz, dass heute Funkstille ist in deinen Themen, dann direkt zum Wetter.

LIMIT: Persönliche Ressorts haben KEIN Limit - alle Stufe-1-Themen mit Inhalt kommen dran.
Allgemeine Kategorien: maximal 2-3 Sätze gesamt als Ticker.
═══════════════════════════════════════════════════════════════════════════════
KALENDER-EMPFEHLUNGEN (AKTIV, NICHT PASSIV!)
═══════════════════════════════════════════════════════════════════════════════

**VERBOTENE PASSIVE PHRASEN (BLACK LIST):** 
- "Die Entscheidung liegt bei dir"
- "Du hast die Wahl zwischen..."
- "Schau mal, was dir besser gefällt"
- "Je nachdem, wo du dir mehr versprichst"

Das ist PASSIV und VERBOTEN. Du bist ein GUIDE, der den Weg weist.

**IMMER:** Gib eine KONKRETE EMPFEHLUNG basierend auf dem Kontext.

**METHODE:**
1. Analysiere das TAGEBUCH: Was beschäftigt den User gerade? (z.B. "Businessplan" -> braucht Business-Kontakte)
2. Analysiere die EVENTS: Welches passt am besten zum aktuellen Fokus?
3. Gib eine BEGRÜNDETE Empfehlung.

**BEISPIEL (GUT):**
"Heute Abend stehen zwei Events an. Meine klare Empfehlung: Die Agentic Software Night. Das passt perfekt zu deinem App-Projekt, und du könntest dort Leute treffen, die dir beim Businessplan helfen."

═══════════════════════════════════════════════════════════════════════════════
STRUKTUR (FLIESSTEXT - Keine Headlines!)
═══════════════════════════════════════════════════════════════════════════════
1. Warme Begrüßung (Variiere! Nicht wie gestern!)
2. Tiefe Retrospektive (Was wurde geschafft? Emotionen ansprechen!).
3. ZITAT: Platziere das gewählte Zitat (Reflexion oder Intention) an einer passenden Stelle im Text.
4. Der Tagesplan (Termine integrieren).
   - **WICHTIG:** Du musst auch deine VORSCHLÄGE für Habits & To-Dos verbalisieren!
   - Sag z.B.: "Da du am Nachmittag frei hast, habe ich dir um 15 Uhr deinen Sport eingeplant."
   - Erkläre kurz, warum du diesen Slot gewählt hast.
5. Recherche-Ergebnisse (falls vorhanden).
6. News als "Deine Morgenzeitung":
   - Eröffne mit einer kurzen Überleitung ("Jetzt zu deiner Morgenzeitung..." o.ä., variiere täglich).
   - DANN: Für JEDES persönliche Ressort mit Inhalt eine ausgearbeitete Mini-Sektion von 4-6 Sätzen
     (Einstieg, konkrete Fakten, Hintergrund, Relevanz für den User).
   - ZUM SCHLUSS: Maximal 2-3 Sätze "Was sonst noch passiert" aus den allgemeinen Kategorien.
   - Keine Headlines im Fließtext, aber hörbare Ressort-Struktur durch Überleitungen.
7. Wetter & Abschluss (Motivation).

**CONSISTENCY CHECK (KRITISCH):**
Wenn du im Text sagst: "Mach Sport um 10 Uhr", DANN MUSS "Sport" auch im `final_agenda` JSON stehen.
Wenn du sagst: "Kalte Dusche am Morgen", DANN MUSS "Kalte Dusche" im `final_agenda` JSON stehen (z.B. 07:00).
Der User sieht nur das, was im JSON steht. Was nicht im JSON steht, existiert für ihn nicht.

**STRUKTUR-ANWEISUNG:**
Antworte DIREKT im vorgegebenen JSON-Format.
Das "script_content" feld enthält den gesamten gesprochenen Text.
"""
    return prompt


def generate_weekly_briefing_prompt(
    weekly_diary_text: str,
    weekly_calendar_text: str,
    user_name: str = "",
    language: str = "German"
) -> str:
    """
    Generates the WEEKLY Briefing Prompt (Sunday Vision).
    Focus: Review of last 7 days + Preview of next 7 days.
    """
    from datetime import datetime
    
    date_short, date_long = get_german_date()
    # Greeting
    greeting = f"Sprich den User mit '{user_name}' an." if user_name else "Nutze eine warme, persönliche Begrüßung."

    prompt = f"""
Du bist ein strategischer Mentor und persönlicher Assistent. Es ist {date_long}.
Dies ist das WOCHEN-BRIEFING ("Weekly Vision").

Erstelle eine TIEFGEHENDE Reflexion der letzten Woche und eine Strategie für die kommende Woche.

**SPRACHE:** Antworte komplett auf Deutsch.
**BEGRÜSSUNG:** {greeting}

═══════════════════════════════════════════════════════════════════════════════
KONTEXT-DATEN
═══════════════════════════════════════════════════════════════════════════════

[RÜCKBLICK: DEINE GEDANKEN DER LETZTEN WOCHE]
{weekly_diary_text if weekly_diary_text else "Keine Tagebucheinträge vorhanden."}

[VORSCHAU: DEINE NÄCHSTE WOCHE]
{weekly_calendar_text if weekly_calendar_text else "Keine Termine für nächste Woche eingetragen."}

═══════════════════════════════════════════════════════════════════════════════
STRUKTUR & INHALT
═══════════════════════════════════════════════════════════════════════════════

1. **Der Rückblick (Mustererkennung)**
   - Analysiere die Tagebuch-Einträge der Woche.
   - Identifiziere das dominierende Thema oder Gefühl.
   - Feiere kleine Siege (Was lief gut?).
   - Erkenne Stressoren (Was hat Energie gekostet?).
   - Sei empathisch, aber analytisch. "Ich habe bemerkt, dass du Mittwoch sehr gestresst warst..."

2. **Die Wochen-Strategie (Vorschau)**
   - Schau auf die [VORSCHAU] (Kalender).
   - Was ist der wichtigste Tag ("Big Rock") nächste Woche?
   - Gib einen strategischen Rat, wie man diese Woche angeht (z.B. "Dienstag wird voll, sorge Montagabend für Ruhe").
   
3. **Fokus-Ziele**
   - Schlage 1-2 mentale Fokus-Ziele vor (z.B. "Achte diese Woche besonders auf Pausen").

4. **Abschluss**
   - Ein motivierendes Zitat oder ein Gedanke für die Woche.

═══════════════════════════════════════════════════════════════════════════════
TTS-OPTIMIERUNG
═══════════════════════════════════════════════════════════════════════════════
- Schreibe ALLES als natürlichen Fließtext zum Vorlesen.
- Keine Markdown-Listen im Textteil.
- Nutze Pausen (...) für rhetorische Wirkung.

**METADATA OUTPUT (REQUIRED):**
Füge am Ende diesen JSON Block hinzu.
---METADATA---
{{
  "final_agenda": [
     {{ "start": "Monday", "name": "Weekly Focus: Stability", "type": "suggestion" }}
  ]
}}
"""
    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def generate_briefing_content(target_user_id: str, briefing_type: str = "daily"):
    """
    Orchestrates the creation of the morning briefing for a SPECIFIC user.
    briefing_type: "daily" or "weekly"
    """
    logger.info(f"Starting {briefing_type} briefing generation for user {target_user_id}...")
    
    # Validation
    if not settings.GOOGLE_API_KEY:
        logger.error("Missing Google API Key")
        raise ValueError("Google Gemini API Key (GEMINI_API_KEY) is missing.")

    # Gemini client will be initialized later when needed
    logger.debug("API Key validated.")
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    session = None
    try:
        session = next(get_session())
        
        # Get user settings
        statement = select(UserSettings).where(UserSettings.user_id == target_user_id)
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            logger.debug(f"No settings found for user {target_user_id}. Creating defaults.")
            user_settings = UserSettings(user_id=target_user_id)
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)

        # 1. Fetch Calendar
        logger.debug("Fetching Calendar...")
        # TODO: Pass user tokens to calendar service
        calendar_events_list = get_calendar_events(target_user_id)
        calendar_text = format_events_text(calendar_events_list)
        logger.debug(f"Calendar Fetched ({len(calendar_events_list)} events).")
        
        # 2. Fetch User Interests & News
        logger.debug("Querying Interests...")
        from models import Interest
        statement = select(Interest).where(Interest.user_id == target_user_id)
        interests = session.exec(statement).all()
        topic_list = [i.topic for i in interests]
        logger.debug(f"Found custom topics: {topic_list}")
        
        # 3. Fetch yesterday's diary (Last entry from DB for THIS USER)
        logger.debug("Fetching last diary entry...")
        statement = select(Entry).where(Entry.user_id == target_user_id).order_by(Entry.id.desc())
        last_entry = session.exec(statement).first()
        
        diary_transcript = None
        detected_language = "de"

        if last_entry:
            # Check if entry is from YESTERDAY
            # We compare entry.created_at.date() with (now - 1 day).date()
            from datetime import date
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            entry_date = last_entry.created_at.date()

            if entry_date == yesterday:
                diary_transcript = last_entry.transcript
                detected_language = last_entry.language or "de"
                logger.debug(f"Found valid diary entry from yesterday ({entry_date}).")
            else:
                logger.debug(f"Last entry is from {entry_date} (Yesterday was {yesterday}). Ignoring for briefing.")
                diary_transcript = None # Explicitly set to None
        else:
             logger.debug("No diary entries found at all.")

        if not diary_transcript:
            diary_transcript = "DER USER HAT GESTERN KEINEN TAGEBUCH-EINTRAG GEMACHT. Erwähne das kurz und freundlich ('Du hast gestern keinen Eintrag verfasst...'), aber mache kein großes Ding draus."

        logger.debug(f"Detected language: {detected_language}")

        # Get user's name for personalized greeting
        user_name = user_settings.name if user_settings.name else ""
        
        # 3b. Fetch Pending Todos
        logger.debug("Fetching Pending Todos...")
        from services.todo_service import get_pending_todos, get_pending_research
        todos = get_pending_todos(target_user_id, session)
        todo_list_text = "\n".join([f"- {t.task} (Due: {t.due_date.strftime('%Y-%m-%d') if t.due_date else 'Anytime'})" for t in todos])
        if not todo_list_text:
            todo_list_text = "No pending tasks."
        
        # 3c. Fetch Daily Habits
        logger.debug("Fetching Daily Habits...")
        from models import Habit
        habits = session.exec(select(Habit).where(Habit.user_id == target_user_id, Habit.is_active == True)).all()
        habits_text = ""
        if habits:
            habits_lines = []
            for h in habits:
                pref = f" (Preferred: {h.preferred_time})" if h.preferred_time != "any" else ""
                habits_lines.append(f"- [HABIT] {h.name} ({h.duration_minutes} min){pref}: {h.description or ''}")
            habits_text = "\n".join(habits_lines)
        else:
            habits_text = "No daily habits defined."
        logger.debug(f"Found {len(habits)} habits.")

        # Auto-complete Todos (Ephemeral Mode)
        # User requested no persistent storage. We mention them once, then mark as done.
        if todos:
            logger.debug(f"Marking {len(todos)} todos as completed (Ephemeral Mode).")
            for t in todos:
                t.is_completed = True
                session.add(t)
            session.commit()
            
        # 3d. Perform Pending Research (JIT)
        logger.debug("Checking for Research Tasks...")
        research_tasks = get_pending_research(target_user_id, session)
        research_results_text = ""
        
        if research_tasks:
            from services.research_service import perform_research_grounding
            logger.debug(f"Found {len(research_tasks)} research tasks. Executing...")
            
            for task in research_tasks:
                logger.debug(f"Researching '{task.query}'...")
                summary = perform_research_grounding(task.query)
                
                research_results_text += f"\n[REQUEST: {task.query}]\nRESULT: {summary}\n"
                
                # Mark as done
                task.status = "done"
                task.result_summary = summary
                session.add(task)
            
            session.commit()
        else:
            research_results_text = ""
        
        # 4. Fetch Weather (if enabled)
        logger.debug("Checking Weather Settings...")
        weather_text = ""
        if user_settings.weather_enabled:
            logger.debug(f"Fetching Weather for {user_settings.weather_city}...")
            weather_text = get_weather_briefing(user_settings.weather_city)
            logger.debug(f"Weather Fetched ({len(weather_text)} chars).")

        # ═══════════════════════════════════════════════════════════════
        # PREPARE V3 INPUTS
        # ═══════════════════════════════════════════════════════════════
        
        # 1. Fetch Split News
        logger.debug("Fetching Split News...")
        news_curated, news_dynamic = fetch_all_news(user_settings, topic_list)
        logger.debug(f"News Fetched. Curated: {len(news_curated)} chars, Dynamic: {len(news_dynamic)} chars.")

        # 2. Fetch History for Anti-Repetition
        prev_briefings = session.exec(
            select(Briefing)
            .where(Briefing.user_id == target_user_id)
            .order_by(Briefing.created_at.desc())
            .limit(2)
        ).all()
        
        briefing_yesterday = prev_briefings[0].script_content if len(prev_briefings) > 0 else None
        briefing_day_before = prev_briefings[1].script_content if len(prev_briefings) > 1 else None
        
        # 3. Fetch Used Quotes (Last 30 days)
        cutoff_quotes = datetime.utcnow() - timedelta(days=30)
        used_quotes_db = session.exec(
            select(UsedQuote).where(UsedQuote.user_id == target_user_id, UsedQuote.used_at > cutoff_quotes)
        ).all()
        used_quote_ids = [q.quote_id for q in used_quotes_db]
        
        # 4. Map User Settings to Categories (Standard-Kategorien getrennt von persönlichen Interessen!)
        user_news_categories = []
        if user_settings.news_politics: user_news_categories.append("Politik")
        if user_settings.news_tech: user_news_categories.append("Technologie")
        if user_settings.news_economy: user_news_categories.append("Wirtschaft")
        if user_settings.news_local: user_news_categories.append("Lokale News")
        if user_settings.news_sports: user_news_categories.append("Sport")

        # Persönliche Interessen bleiben separat, damit der Prompt sie priorisieren kann
        custom_interests = topic_list or []
        
        # 5. GENERATE PROMPT
        if briefing_type == "weekly":
             # --- WEEKLY LOGIC ---
             logger.debug("Gathering data for WEEKLY briefing...")
             
             # 1. Fetch Diary (Last 7 Days)
             cutoff_date = datetime.utcnow() - timedelta(days=7)
             weekly_entries = session.exec(
                 select(Entry)
                 .where(Entry.user_id == target_user_id, Entry.created_at >= cutoff_date)
                 .order_by(Entry.created_at.asc())
             ).all()
             
             weekly_diary_text = ""
             if weekly_entries:
                 for entry in weekly_entries:
                     date_str = entry.created_at.strftime("%A")
                     weekly_diary_text += f"\n[TAGEBUCH {date_str}]: {entry.transcript[:500]}..." # Limit context
             else:
                 weekly_diary_text = "Keine Einträge in dieser Woche."

             # 2. Fetch Calendar (Next 7 Days)
             weekly_events = get_calendar_events(target_user_id, days=7)
             weekly_calendar_text = format_events_text(weekly_events)
             
             # Overwrite calendar_events_list for storage
             calendar_events_list = weekly_events

             prompt = generate_weekly_briefing_prompt(
                 weekly_diary_text=weekly_diary_text,
                 weekly_calendar_text=weekly_calendar_text,
                 user_name=user_name,
                 language=user_settings.language
             )

        else:
             # --- DAILY LOGIC (Existing) ---
             prompt = generate_morning_briefing_prompt(
                diary_transcript=diary_transcript,
                todo_list_text=todo_list_text,
                habits_text=habits_text,
                calendar_text=calendar_text,
                weather_text=weather_text,
                news_curated=news_curated,
                news_dynamic=news_dynamic,
                briefing_yesterday=briefing_yesterday,
                briefing_day_before=briefing_day_before,
                research_results_text=research_results_text,
                user_name=user_name,
                briefing_time=user_settings.briefing_time,
                user_news_categories=user_news_categories,
                custom_interests=custom_interests,
                used_quote_ids=used_quote_ids,
                language=user_settings.language
            )
        
        from schemas import BriefingResponse
        
        logger.debug("Generating Content with Gemini (Structured Output)...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                 response_mime_type="application/json",
                 response_schema=BriefingResponse
            )
        )
        logger.debug("Gemini Response Received.")
        
        # Parse Strict Response
        import json
        try:
            data_dict = json.loads(response.text)
            briefing_obj = BriefingResponse(**data_dict)
            
            # Extract Script
            script = briefing_obj.script_content
            
            # Save Used Quote (Single)
            q = briefing_obj.quote
            if q:
                qid = generate_quote_id(q.text, q.author)
                logger.debug(f"Tracking Quote: {qid} ({q.author})")
                new_used_quote = UsedQuote(
                    user_id=target_user_id,
                    quote_id=qid,
                    quote_text_snippet=q.text
                )
                session.add(new_used_quote)
            session.commit()

            # Extract Final Agenda
            normalized_agenda = []
            for event in briefing_obj.final_agenda:
                normalized_agenda.append({
                    "start": event.start, 
                    "end": event.end or "",
                    "name": event.name,
                    "calendar": "AI Suggestion" if event.type == "suggestion" else "Calendar",
                    "type": event.type
                })
            
            # Sort & Replace
            normalized_agenda.sort(key=lambda x: x['start'])
            if normalized_agenda:
                 calendar_events_list = normalized_agenda
                 logger.debug("Replaced raw calendar with AI Agenda (Verified Strict).")

        except Exception as e:
            logger.error(f"Failed to parse Structured Output: {e}")
            # Fallback (Should not happen with high temp/valid schema, but good safety)
            script = response.text    
        
        # 7. Generate Audio
        logger.debug("Generating Audio (TTS)...")
        audio_filename = f"briefing_{target_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        user_voice = user_settings.voice_id if user_settings else None
        generate_speech(script, audio_path_abs, language=detected_language, voice_override=user_voice)
        logger.debug(f"Audio saved to {audio_path_abs} (lang: {detected_language}, voice: {user_voice})")
        
        # 8. Upload to Supabase Storage
        logger.debug("Uploading to Supabase...")
        from services.storage_service import upload_file, delete_file
        
        storage_path = f"{target_user_id}/{audio_filename}"
        
        try:
            upload_file(audio_path_abs, storage_path)
            if os.path.exists(audio_path_abs):
                os.remove(audio_path_abs)
                logger.debug("Local file generated and removed after upload.")
        except Exception as e:
            logger.error(f"Upload failed: {e}. Keeping local file as fallback.")
            storage_path = None 

        # 9. Save Briefing to DB
        briefing = Briefing(
            user_id=target_user_id,
            scheduled_for=datetime.now(),
            script_content=script,
            calendar_events=json.dumps(calendar_events_list) if calendar_events_list else None,
            audio_path=storage_path if storage_path else audio_path_abs, 
            status="generated",
            type=briefing_type
        )
        session.add(briefing)
        session.commit()
        session.refresh(briefing)
        session.expunge(briefing) 
        
        logger.info(f"Briefing generated and stored: {storage_path}")
        
        # 10. Auto-Cleanup
        try:
            logger.debug("Running Auto-Cleanup...")
            cutoff_date = datetime.utcnow() - timedelta(days=3)
            
            old_briefings = session.exec(
                select(Briefing).where(
                    Briefing.user_id == target_user_id,
                    Briefing.created_at < cutoff_date
                )
            ).all()
            
            for old_b in old_briefings:
                if old_b.audio_path and "/" in old_b.audio_path and not old_b.audio_path.startswith("/"):
                     delete_file(old_b.audio_path)
                session.delete(old_b)
            
            session.commit()
            logger.debug(f"Cleanup finished. Removed {len(old_briefings)} old briefings.")
            
        except Exception as e:
            logger.error(f"Auto-cleanup failed: {e}")
        
        logger.debug("Briefing generation complete.")
        return briefing
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        if session:
            session.rollback()
        raise e
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    generate_briefing_content()
