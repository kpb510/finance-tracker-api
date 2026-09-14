from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models, schemas, security 

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance Tracker API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if the email is already registered
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    new_user = models.User(
        email=user.email,
        hashed_password=security.hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
