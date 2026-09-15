from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db, SessionLocal
from app import models, schemas, security 

from fastapi.security import OAuth2PasswordRequestForm

from typing import List
from app.dependencies import get_current_user

def seed_categories(db: Session):
    """Insert default categories if none exist yet."""
    if db.query(models.Category).first() is not None:
        return # already seeded
    
    defaults = ["Food", "Transport", "Bills", "Entertainment", "Shopping", "Health", "Other"]
    for name in defaults:
        db.add(models.Category(name=name))
    db.commit()

Base.metadata.create_all(bind=engine)

# Seed categories once at startup, using a throwaway session
_db = SessionLocal()
try:
    seed_categories(_db)
finally:
    _db.close()

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

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

def _get_owned_transaction_or_404(
    transaction_id: int,
    db: Session,
    current_user: models.User
) -> models.Transaction:
    
    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id,
            models.Transaction.owner_id == current_user.id,
        )
        .first()
    )
    
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction

@app.post(
    "/transactions",
    response_model=schemas.TransactionOut,
    status_code=status.HTTP_201_CREATED
)
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    if transaction.category_id is not None:
        category = db.query(models.Category).filter(models.Category.id == transaction.category_id).first()
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category does not exist"
            )
    
    new_transaction = models.Transaction(
        **transaction.model_dump(),
        owner_id=current_user.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction

@app.get("/transactions/{transaction_id}", response_model=List[schemas.TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.owner_id == current_user.id)
        .all()
    )

@app.get(
    "/transactions/{transaction_id}",
    response_model=schemas.TransactionOut
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_owned_transaction_or_404(transaction_id, db, current_user)

@app.put(
    "/transactions/{transaction_id}",
    response_model=schemas.TransactionOut
)
def update_transaction(
    transaction_id: int, 
    updates: schemas.TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    transaction = _get_owned_transaction_or_404(transaction_id, db, current_user)
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction

@app.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_transaction(
    transaction_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    transaction = _get_owned_transaction_or_404(transaction_id, db, current_user)
    db.delete(transaction)
    db.commit()
    
@app.get(
    "/categories",
    response_model=List[schemas.CategoryOut]
)
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Category).all()

@app.post(
    "/categories",
    response_model=schemas.CategoryOut,
    status_code=status.HTTP_201_CREATED
)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.Category).filter(models.Category.name == category.name).first()
    if existing: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists"
        )
    new_category = models.Category(name=category.name)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category