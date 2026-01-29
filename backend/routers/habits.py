from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Habit
from datetime import datetime
from typing import List

router = APIRouter(prefix="/habits", tags=["habits"])

@router.get("/", response_model=List[Habit])
def get_habits(user_id: str = "test-user-id", session: Session = Depends(get_session)):
    # TODO: Auth
    habits = session.exec(select(Habit).where(Habit.user_id == user_id).where(Habit.is_active == True)).all()
    return habits

@router.post("/", response_model=Habit)
def create_habit(habit: Habit, session: Session = Depends(get_session)):
    # Override user_id for now until auth is fully piped
    # habit.user_id = ... (Using passed in body or default for now)
    
    # Validation
    if habit.duration_minutes < 5:
        habit.duration_minutes = 30
        
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit

@router.delete("/{habit_id}")
def delete_habit(habit_id: int, user_id: str = "test-user-id", session: Session = Depends(get_session)):
    habit = session.get(Habit, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
        
    if habit.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Soft delete or hard delete? Let's do soft delete for now, or just hard delete since it's simple
    session.delete(habit)
    session.commit()
    return {"ok": True}
