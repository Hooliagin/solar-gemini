from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Interest
from typing import List

router = APIRouter(prefix="/interests", tags=["interests"])

@router.post("/", response_model=Interest)
def create_interest(interest: Interest, session: Session = Depends(get_session)):
    session.add(interest)
    session.commit()
    session.refresh(interest)
    return interest

@router.get("/", response_model=List[Interest])
def read_interests(session: Session = Depends(get_session)):
    interests = session.exec(select(Interest)).all()
    return interests

@router.delete("/{interest_id}")
def delete_interest(interest_id: int, session: Session = Depends(get_session)):
    interest = session.get(Interest, interest_id)
    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")
    session.delete(interest)
    session.commit()
    return {"ok": True}
