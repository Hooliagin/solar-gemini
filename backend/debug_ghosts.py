
from database import get_session
from models import UserTodo, ResearchTask, Habit, UserSettings
from sqlmodel import select
import sys

def check_ghosts():
    session = next(get_session())
    
    # Get all users
    users = session.exec(select(UserSettings)).all()
    
    print(f"Found {len(users)} users.")
    
    for user in users:
        print(f"\n--- User: {user.name} ({user.user_id}) ---")
        
        # 1. Todos
        todos = session.exec(select(UserTodo).where(UserTodo.user_id == user.user_id, UserTodo.is_completed == False)).all()
        print(f"PENDING TODOS ({len(todos)}):")
        for t in todos:
            print(f" - [ID: {t.id}] {t.task} (Created: {t.created_at})")
            
        # 2. Research
        research = session.exec(select(ResearchTask).where(ResearchTask.user_id == user.user_id, ResearchTask.status == "pending")).all()
        print(f"PENDING RESEARCH ({len(research)}):")
        for r in research:
            print(f" - [ID: {r.id}] {r.query} (Created: {r.created_at})")
            
        # 3. Habits
        habits = session.exec(select(Habit).where(Habit.user_id == user.user_id)).all()
        print(f"HABITS ({len(habits)}):")
        for h in habits:
            print(f" - [ID: {h.id}] {h.name}")

if __name__ == "__main__":
    try:
        check_ghosts()
    except Exception as e:
        print(f"Error: {e}")
