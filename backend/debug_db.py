from database import get_session
from models import UserSettings
from sqlmodel import select

def inspect_users():
    session = next(get_session())
    try:
        users = session.exec(select(UserSettings)).all()
        print(f"Found {len(users)} users.")
        for user in users:
            print(f"User: {user.name}")
            print(f"  ID: {user.user_id}")
            print(f"  Telegram Enabled: {user.telegram_enabled}")
            print(f"  Chat ID: {user.telegram_chat_id}")
            print(f"  Reflection Time: '{user.reflection_time}'")
            print(f"  Reminder Enabled: {user.reflection_reminder_enabled}")
            print("-" * 20)
    finally:
        session.close()

if __name__ == "__main__":
    inspect_users()
