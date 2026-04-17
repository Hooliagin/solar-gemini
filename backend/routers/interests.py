from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Interest
from typing import List
from auth import get_current_user_id

router = APIRouter(prefix="/interests", tags=["interests"])

MAX_INTERESTS = 5

@router.post("/", response_model=Interest)
def create_interest(
    interest: Interest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    # Enforce user_id from token
    interest.user_id = user_id

    existing_count = len(session.exec(select(Interest).where(Interest.user_id == user_id)).all())
    if existing_count >= MAX_INTERESTS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximal {MAX_INTERESTS} Interessen erlaubt. Bitte entferne zuerst ein bestehendes Thema."
        )

    session.add(interest)
    session.commit()
    session.refresh(interest)
    return interest

@router.get("/", response_model=List[Interest])
def read_interests(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    # Filter by user_id
    interests = session.exec(select(Interest).where(Interest.user_id == user_id)).all()
    return interests

@router.delete("/{interest_id}")
def delete_interest(
    interest_id: int, 
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id)
):
    interest = session.get(Interest, interest_id)
    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")
        
    # Check ownership
    if interest.user_id != user_id:
         raise HTTPException(status_code=403, detail="Not authorized to delete this interest")
         
    session.delete(interest)
    session.commit()
    return {"ok": True}
