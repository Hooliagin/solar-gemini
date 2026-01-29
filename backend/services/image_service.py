from PIL import Image, ImageDraw, ImageFont
import textwrap
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants for "Luxury" Design
BG_COLOR = "#F5F5F0" # Warm Grey / Off-White background
TEXT_COLOR = "#1A1A1A" # Charcoal
ACCENT_COLOR = "#D4AF37" # Gold
FONT_PATH_TITLE = "arial.ttf" # Fallback
FONT_PATH_BODY = "arial.ttf"

def generate_agenda_image(events: list[dict], date_text: str) -> str:
    """
    Generates a vertical timeline image of the day's agenda.
    Returns the path to the saved temporary image file.
    """
    if not events:
        return None

    # Config
    width = 800
    header_height = 200
    event_height = 100
    padding = 50
    
    # Calculate dynamic height
    total_height = header_height + (len(events) * event_height) + padding
    
    # Create Image
    img = Image.new('RGB', (width, total_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Load Fonts (Try to find a system font or fallback)
    try:
        # Linux/Render common paths or Windows
        # Ideally we would bundle a font, but for now use default or simple detection
        title_font = ImageFont.truetype("DejaVuSerif-Bold.ttf", 60)
        date_font = ImageFont.truetype("DejaVuSans.ttf", 30)
        time_font = ImageFont.truetype("DejaVuSerif.ttf", 30)
        event_font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except IOError:
         try:
            # Windows fallback
            title_font = ImageFont.truetype("timesbd.ttf", 60)
            date_font = ImageFont.truetype("arial.ttf", 30)
            time_font = ImageFont.truetype("times.ttf", 30)
            event_font = ImageFont.truetype("arial.ttf", 28)
         except IOError:
            # Ultimate Fallback
            title_font = ImageFont.load_default()
            date_font = ImageFont.load_default()
            time_font = ImageFont.load_default()
            event_font = ImageFont.load_default()

    # Draw Header
    draw.text((padding, 60), "Daily Agenda", font=title_font, fill=TEXT_COLOR)
    draw.text((padding, 130), date_text, font=date_font, fill=ACCENT_COLOR)
    
    # Draw Divider
    draw.line([(padding, 180), (width - padding, 180)], fill="#E0E0E0", width=2)
    
    # Draw Events
    current_y = header_height
    line_x = padding + 120 # X position for the vertical timeline line
    
    # Draw Vertical Line
    draw.line([(line_x, header_height), (line_x, total_height - padding)], fill=ACCENT_COLOR, width=2)
    
    for event in events:
        start_time = event['start']
        name = event['name']
        
        # Format Time
        time_str = "All Day"
        start_t = ""
        end_t = ""
        
        # Parse Start
        if 'T' in start_time:
             start_t = start_time.split('T')[1][:5]
        elif ':' in start_time:
             start_t = start_time[:5]
             
        # Parse End (if available)
        end_time = event.get('end', '')
        if end_time:
            if 'T' in end_time:
                end_t = end_time.split('T')[1][:5]
            elif ':' in end_time:
                end_t = end_time[:5]

        if start_t:
            if end_t:
                # Multi-line time for range
                # Draw start, then end below
                draw.text((padding, current_y - 10), start_t, font=time_font, fill=TEXT_COLOR)
                draw.text((padding + 5, current_y + 20), f"-{end_t}", font=time_font, fill=TEXT_COLOR)
                is_multiline_time = True
            else:
                draw.text((padding, current_y), start_t, font=time_font, fill=TEXT_COLOR)
        else:
             draw.text((padding, current_y), "All Day", font=time_font, fill=TEXT_COLOR)
        
        # Draw Dot
        dot_r = 6
        is_fixed = event.get('type') == 'fixed'
        
        if is_fixed:
            # Solid Gold Dot for fixed events
            draw.ellipse([(line_x - dot_r, current_y + 15 - dot_r), (line_x + dot_r, current_y + 15 + dot_r)], fill=ACCENT_COLOR, outline=ACCENT_COLOR)
        else:
            # Hollow Dot for suggestions
            draw.ellipse([(line_x - dot_r, current_y + 15 - dot_r), (line_x + dot_r, current_y + 15 + dot_r)], fill=BG_COLOR, outline=ACCENT_COLOR, width=2)
        
        # Draw Event Name (Right)
        text_x = line_x + 40
        
        # Truncate if too long
        if len(name) > 40:
            name = name[:37] + "..."
            
        draw.text((text_x, current_y), name, font=event_font, fill=TEXT_COLOR)
        
        current_y += event_height

    # Save
    filename = f"agenda_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    filepath = os.path.join("tmp", filename)
    os.makedirs("tmp", exist_ok=True)
    img.save(filepath)
    
    logger.info(f"Generated agenda image: {filepath}")
    return filepath
