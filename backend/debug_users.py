from sqlmodel import Session, select
from database import engine
from models import UserSettings, Briefing, Entry

def debug_users():
    with Session(engine) as session:
        users = session.exec(select(UserSettings)).all()
        print(f"Found {len(users)} users in UserSettings:")
        print("-" * 60)
        print(f"{'User ID':<40} | {'Name':<10} | {'Telegram ID':<15} | {'Briefings'}")
        print("-" * 60)
        
        for user in users:
            briefing_count = session.exec(select(Briefing).where(Briefing.user_id == user.user_id)).all()
            print(f"{user.user_id:<40} | {str(user.name):<10} | {str(user.telegram_chat_id):<15} | {len(briefing_count)}")

debug_users()
