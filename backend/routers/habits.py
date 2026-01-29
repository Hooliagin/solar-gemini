from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Habit
from auth import get_current_user
from gotrue.types import User

router = APIRouter(prefix="/habits", tags=["habits"])

@router.get("/", response_model=list[Habit])
def get_habits(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    habits = session.exec(select(Habit).where(Habit.user_id == current_user.id).where(Habit.is_active == True)).all()
    return habits

@router.post("/", response_model=Habit)
def create_habit(habit: Habit, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # Override user_id from token to ensure security
    habit.user_id = current_user.id
    
    # Validation
    if habit.duration_minutes < 5:
        habit.duration_minutes = 30
        
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit

@router.delete("/{habit_id}")
def delete_habit(habit_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    habit = session.get(Habit, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
        
    if habit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    session.delete(habit)
    session.commit()
    return {"ok": True}
