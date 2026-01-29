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
**BRIEFING VON GESTERN (NICHT WIEDERHOLEN!):**
\"\"\"
{briefing_yesterday[:2500]}{"..." if len(briefing_yesterday) > 2500 else ""}
\"\"\"

**Identifizierte Phrasen die du VERMEIDEN musst:**
{chr(10).join(f'- "{p}"' for p in phrases[:12])}
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
    user_news_categories: Optional[List[str]] = None,
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
    
    # News-Kategorien für kontextuelle News-Suche
    news_context = ""
    if user_news_categories:
        categories_str = ", ".join(user_news_categories)
        news_context = f"Der User interessiert sich für: {categories_str}"
    
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
{anti_repetition_block}
═══════════════════════════════════════════════════════════════════════════════

{blacklist_block}

═══════════════════════════════════════════════════════════════════════════════
KONTEXT-DATEN
═══════════════════════════════════════════════════════════════════════════════

[TAGEBUCH / GEDANKEN VON GESTERN]
{diary_transcript if diary_transcript else "Kein Tagebucheintrag vorhanden."}

[TO-DO LISTE / ERINNERUNGEN]
{todo_list_text if todo_list_text else "Keine To-Dos eingetragen."}

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

**SO FINDEST DU GUTE ZITATE:**

SCHRITT 1: Identifiziere die SPEZIFISCHE Emotion/Situation
SCHRITT 2: Suche ein Zitat das diese SPEZIFISCHE Situation anspricht
SCHRITT 3: Bevorzuge UNBEKANNTE Quellen (Seneca Briefe, Marc Aurel, Rilke, Brené Brown, Naval Ravikant)
SCHRITT 4: VALIDIERE dein Zitat. Frage: "Würde dieses Zitat auf einer Instagram-Motivationsseite stehen?" JA → VERWERFEN.

**ZWEI ZITATE ERFORDERLICH:**

ZITAT 1 - REFLEXIONS-ZITAT (Rückblick auf Gestern/Tagebuch):
├── Analysiere das TAGEBUCH → Identifiziere die dominante Emotion:
│   • Erfolg/Leistung → Zitat über Bedeutung jenseits von Erfolg
│   • Stress/Überforderung → Zitat über Perspektive, Loslassen
│   • Unsicherheit/Hilflosigkeit → Zitat über Fragen stellen, Anfänge
│   • Einsamkeit → Zitat über Verbindung, Menschlichkeit
│   • Wachstum/Lernen → Zitat über die Reise, Neugier
├── Wähle ein Zitat das diese Emotion DIREKT anspricht (ECHTE EMOTION!).
└── PLATZIERUNG: Nach der Retrospektive.

ZITAT 2 - INTENTIONS-ZITAT (Vorausschau auf Heute/Kalender):
├── Analysiere den KALENDER → Bestimme den Tagestyp (Meeting, Deep Work, Admin, etc.)
├── Wähle ein Zitat das zum Tagestyp PASST
└── PLATZIERUNG: Vor dem Tagesplan / Als Übergang.

═══════════════════════════════════════════════════════════════════════════════
TO-DO INTEGRATION (PFLICHT - NICHT OPTIONAL!)
═══════════════════════════════════════════════════════════════════════════════
**METHODE - Die Gap-Analyse:**
1. Liste alle festen Termine
2. Identifiziere freie Zeitblöcke
3. Ordne JEDES To-Do einem spezifischen Zeitslot zu
4. Begründe WARUM dieser Slot passt

**BEISPIEL:**
"Nach deinem Standup um zehn Uhr hast du bis vierzehn Uhr einen freien Block. Ich schlage vor: Nutze zehn Uhr dreißig bis zwölf Uhr dreißig für den Businessplan."

═══════════════════════════════════════════════════════════════════════════════
NEWS-AUSWAHL (STRIKTE QUELLEN-TREUE!)
═══════════════════════════════════════════════════════════════════════════════
**HEUTE IST: {date_short}**

**REGEL 1:** Nutze AUSSCHLIESSLICH die Informationen aus [NEWS - KURATIERTE QUELLEN] und [NEWS - DYNAMISCHE SUCHE].
**REGEL 2 (ANTI-HALLUZINATION):** Wenn dort steht "Keine News" oder wenn die Info leer ist: ERFINDE KEINE NEWS.
**REGEL 3:** "Leite Themen aus dem Kontext ab" ist HIER VERBOTEN. Du darfst keine News erfinden, nur weil der User "KI" im Kalender hat.

Wenn KEINE News-Quellen vorhanden sind:
-> Erwähne kurz, dass es heute ruhig ist in der Welt, und geh direkt zum Wetter über.

Maximal 3 Themen aus den GEGEBENEN Quellen.
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
   - Schließe diesen Teil mit dem REFLEXIONS-ZITAT (Zitat 1) ab.
3. Der Tagesplan (Termine + Todos in die Lücken integrieren).
   - Schließe mit dem INTENTIONS-ZITAT (Zitat 2) ab.
4. Recherche-Ergebnisse (falls vorhanden).
5. News (Mix aus Kuratiert & Dynamisch. Max 2-3 Themen. Nur Relevantes!).
6. Wetter & Abschluss (Motivation).

**METADATA OUTPUT (REQUIRED AT THE VERY END):**
Please add the following JSON block at the very end of your response, separated by "---METADATA---".
---METADATA---
{{
  "quotes": [
     {{ "text": "Quote 1 Text...", "author": "Author 1" }}
  ],
  "final_agenda": [
     {{ "time": "09:00", "name": "Deep Work (AI Suggestion)", "type": "suggestion" }},
     {{ "time": "14:00", "name": "Meeting with Client", "type": "fixed" }}
  ]
}}
"""
    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def generate_briefing_content(target_user_id: str):
    """
    Orchestrates the creation of the morning briefing for a SPECIFIC user.
    """
    print(f"DEBUG: Starting briefing generation for user {target_user_id}...", flush=True)
    logger.info(f"Starting briefing generation for user {target_user_id}...")
    
    # Validation
    if not settings.GOOGLE_API_KEY:
        print("DEBUG: Missing Google API Key", flush=True)
        raise ValueError("Google Gemini API Key (GEMINI_API_KEY) is missing.")

    # Gemini client will be initialized later when needed
    print("DEBUG: API Key validated.", flush=True)
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    session = None
    try:
        session = next(get_session())
        
        # Get user settings
        statement = select(UserSettings).where(UserSettings.user_id == target_user_id)
        user_settings = session.exec(statement).first()
        
        if not user_settings:
            print(f"DEBUG: No settings found for user {target_user_id}. Creating defaults.", flush=True)
            user_settings = UserSettings(user_id=target_user_id)
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)

        # 1. Fetch Calendar
        print("DEBUG: Fetching Calendar...", flush=True)
        # TODO: Pass user tokens to calendar service
        calendar_events_list = get_calendar_events(target_user_id)
        calendar_text = format_events_text(calendar_events_list)
        print(f"DEBUG: Calendar Fetched ({len(calendar_events_list)} events).", flush=True)
        
        # 2. Fetch User Interests & News
        print("DEBUG: Querying Interests...", flush=True)
        from models import Interest
        statement = select(Interest).where(Interest.user_id == target_user_id)
        interests = session.exec(statement).all()
        topic_list = [i.topic for i in interests]
        print(f"DEBUG: Found custom topics: {topic_list}", flush=True)
        
        # 3. Fetch yesterday's diary (Last entry from DB for THIS USER)
        print("DEBUG: Fetching last diary entry...", flush=True)
        statement = select(Entry).where(Entry.user_id == target_user_id).order_by(Entry.id.desc())
        last_entry = session.exec(statement).first()
        
        diary_transcript = last_entry.transcript if last_entry else "No diary entry for last night."
        detected_language = last_entry.language if last_entry and last_entry.language else "de"  # Default to German
        print(f"DEBUG: Detected language: {detected_language}", flush=True)

        # Get user's name for personalized greeting
        user_name = user_settings.name if user_settings.name else ""
        
        # 3b. Fetch Pending Todos
        print("DEBUG: Fetching Pending Todos...", flush=True)
        from services.todo_service import get_pending_todos, get_pending_research
        todos = get_pending_todos(target_user_id, session)
        todo_list_text = "\n".join([f"- {t.task} (Due: {t.due_date.strftime('%Y-%m-%d') if t.due_date else 'Anytime'})" for t in todos])
        if not todo_list_text:
            todo_list_text = "No pending tasks."
        
        # Auto-complete Todos (Ephemeral Mode)
        # User requested no persistent storage. We mention them once, then mark as done.
        if todos:
            print(f"DEBUG: Marking {len(todos)} todos as completed (Ephemeral Mode).", flush=True)
            for t in todos:
                t.is_completed = True
                session.add(t)
            session.commit()
            
        # 3c. Perform Pending Research (JIT)
        print("DEBUG: Checking for Research Tasks...", flush=True)
        research_tasks = get_pending_research(target_user_id, session)
        research_results_text = ""
        
        if research_tasks:
            from services.research_service import perform_research_grounding
            print(f"DEBUG: Found {len(research_tasks)} research tasks. Executing...", flush=True)
            
            for task in research_tasks:
                print(f"DEBUG: Researching '{task.query}'...", flush=True)
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
        print("DEBUG: Checking Weather Settings...", flush=True)
        weather_text = ""
        if user_settings.weather_enabled:
            print(f"DEBUG: Fetching Weather for {user_settings.weather_city}...", flush=True)
            weather_text = get_weather_briefing(user_settings.weather_city)
            print(f"DEBUG: Weather Fetched ({len(weather_text)} chars).", flush=True)

        # ═══════════════════════════════════════════════════════════════
        # PREPARE V3 INPUTS
        # ═══════════════════════════════════════════════════════════════
        
        # 1. Fetch Split News
        print("DEBUG: Fetching Split News...", flush=True)
        news_curated, news_dynamic = fetch_all_news(user_settings, topic_list)
        print(f"DEBUG: News Fetched. Curated: {len(news_curated)} chars, Dynamic: {len(news_dynamic)} chars.", flush=True)

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
        
        # 4. Map User Settings to Categories
        user_news_categories = []
        if user_settings.news_politics: user_news_categories.append("general_de")
        if user_settings.news_tech: user_news_categories.append("tech")
        if user_settings.news_economy: user_news_categories.append("business")
        
        # 5. GENERATE PROMPT V3
        prompt = generate_morning_briefing_prompt(
            diary_transcript=diary_transcript,
            todo_list_text=todo_list_text,
            calendar_text=calendar_text,
            weather_text=weather_text,
            news_curated=news_curated,
            news_dynamic=news_dynamic,
            briefing_yesterday=briefing_yesterday,
            briefing_day_before=briefing_day_before,
            research_results_text=research_results_text,
            user_name=user_name,
            user_news_categories=user_news_categories,
            used_quote_ids=used_quote_ids,
            language=user_settings.language
        )
        
        print("DEBUG: Generating Content with Gemini (v3.0 Prompt)...", flush=True)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        print("DEBUG: Gemini Response Received.", flush=True)
        raw_text = response.text
        
        # 6. Extract Metadata (Quotes) & Clean Script
        script = raw_text
        try:
            if "---METADATA---" in raw_text:
                parts = raw_text.split("---METADATA---")
                script = parts[0].strip() # The audio script
                metadata_str = parts[1].strip()
                
                # Parse JSON
                metadata_str = metadata_str.replace("```json", "").replace("```", "").strip()
                metadata = json.loads(metadata_str)
                
                # Save Used Quotes
                if "quotes" in metadata:
                    for q in metadata["quotes"]:
                        q_text = q.get("text", "")
                        q_author = q.get("author", "Unknown")
                        qid = generate_quote_id(q_text, q_author)
                        
                        # Store in DB
                        print(f"DEBUG: Tracking Quote: {qid} ({q_author})", flush=True)
                        new_used_quote = UsedQuote(
                            user_id=target_user_id,
                            quote_id=qid,
                            quote_text_snippet=q_text  # Store full text for frontend display
                        )
                        session.add(new_used_quote)
                    session.commit()

                # Extract Final Agenda (AI Suggestions + Fixed)
                if "final_agenda" in metadata and isinstance(metadata["final_agenda"], list):
                    ai_agenda = metadata["final_agenda"]
                    print(f"DEBUG: Found AI Suggested Agenda with {len(ai_agenda)} items.", flush=True)
                    
                    # Normalize to internal format
                    # Internal Format expected by Frontend/ImageService: { 'start': 'HH:MM' or ISO, 'name': '...', 'calendar': '...' }
                    normalized_agenda = []
                    for event in ai_agenda:
                        start_time = event.get("time", "")
                        # Ensure we handle purely time strings "10:00" vs ISO timestamps
                        # If it's just a time, append today's date for consistency if needed, 
                        # OR just keep it as is since frontend/image service handles "T" split check.
                        # Let's keep it simple: Ensure 'start' key exists.
                        
                        normalized_agenda.append({
                            "start": start_time, # ImageService expects 'start'
                            "name": event.get("name", "Event"),
                            "calendar": "AI Suggestion" if event.get("type") == "suggestion" else "Calendar",
                            "type": event.get("type", "fixed")
                        })
                    
                    # OVERRIDE the raw calendar events with this AI-enhanced version
                    if normalized_agenda:
                         calendar_events_list = normalized_agenda
                         print("DEBUG: Replaced raw calendar with AI Agenda.", flush=True)

            else:
                logger.warning("No Metadata block found in LLM response.")
        except Exception as e:
            logger.error(f"Failed to parse Quote Metadata: {e}")
            script = raw_text.split("---METADATA---")[0].strip() 
        
        # 7. Generate Audio
        print("DEBUG: Generating Audio (TTS)...", flush=True)
        audio_filename = f"briefing_{target_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        audio_path_abs = os.path.join(settings.AUDIO_DIR, audio_filename)
        
        user_voice = user_settings.voice_id if user_settings else None
        generate_speech(script, audio_path_abs, language=detected_language, voice_override=user_voice)
        print(f"DEBUG: Audio saved to {audio_path_abs} (lang: {detected_language}, voice: {user_voice})", flush=True)
        
        # 8. Upload to Supabase Storage
        print("DEBUG: Uploading to Supabase...", flush=True)
        from services.storage_service import upload_file, delete_file
        
        storage_path = f"{target_user_id}/{audio_filename}"
        
        try:
            upload_file(audio_path_abs, storage_path)
            if os.path.exists(audio_path_abs):
                os.remove(audio_path_abs)
                print("DEBUG: Local file generated and removed after upload.", flush=True)
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
            status="generated"
        )
        session.add(briefing)
        session.commit()
        session.refresh(briefing)
        session.expunge(briefing) 
        
        logger.info(f"Briefing generated and stored: {storage_path}")
        print("DEBUG: Briefing saved to DB.", flush=True)
        
        # 10. Auto-Cleanup
        try:
            print("DEBUG: Running Auto-Cleanup...", flush=True)
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
            print(f"DEBUG: Cleanup finished. Removed {len(old_briefings)} old briefings.", flush=True)
            
        except Exception as e:
            logger.error(f"Auto-cleanup failed: {e}")
        
        print("DEBUG: Done.", flush=True)
        return briefing
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        print(f"DEBUG: ERROR GENERATING BRIEFING: {e}", flush=True)
        if session:
            session.rollback()
        raise e
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    generate_briefing_content()
