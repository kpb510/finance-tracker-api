from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import extract 
from datetime import date 
from app.database import Base, engine, get_db, SessionLocal
from app import models, schemas, security 
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import List, Optional 
from app.dependencies import get_current_user
from contextlib import asynccontextmanager

def seed_categories(db: Session):
    """Insert default categories if none exist yet."""
    if db.query(models.Category).first() is not None:
        return # already seeded
    
    defaults = ["Food", "Transport", "Bills", "Entertainment", "Shopping", "Health", "Other"]
    for name in defaults:
        db.add(models.Category(name=name))
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_categories(db)
    finally:
        db.close()
    yield # app runs here

app = FastAPI(title="Personal Finance Tracker API", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Invalid input", "errors": exc.errors()},
    )
    
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )
    
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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
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

@app.get("/transactions", response_model=List[schemas.TransactionOut])
def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Transaction).filter(models.Transaction.owner_id == current_user.id)
    
    if start_date is not None:
        query = query.filter(models.Transaction.date >= start_date)
    if end_date is not None:
        query = query.filter(models.Transaction.date <= end_date)
    if category_id is not None:
        query = query.filter(models.Transaction.category_id == category_id)
    
    return query.all()

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

@app.get("/summary/monthly", response_model=schemas.MonthlySummary)
def monthly_summary(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    transactions = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.owner_id == current_user.id,
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .all()
    )
    
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    
    return schemas.MonthlySummary(
        year=year,
        month=month,
        total_income=total_income,
        total_expense=total_expense,
        net=total_income - total_expense,
    )
    



def _calculate_spent(
    db: Session,
    current_user: models.User,
    month: int,
    year: int,
    category_id: Optional[int],
) -> float:
    query = db.query(models.Transaction).filter(
        models.Transaction.owner_id == current_user.id,
        models.Transaction.type == "expense",
        extract("year", models.Transaction.date) == year,
        extract("month", models.Transaction.date) == month,
    )
    if category_id is not None:
        query = query.filter(models.Transaction.category_id == category_id)
    
    return sum(t.amount for t in query.all())

@app.post("/budgets", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if budget.category_id is not None:
        category = db.query(models.Category).filter(models.Category.id == budget.category_id).first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category does not exist")
    
    new_budget = models.Budget(
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        category_id=budget.category_id,
        owner_id=current_user.id,
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    
    spent = _calculate_spent(db, current_user, new_budget.month, new_budget.year, new_budget.category_id)
    return schemas.BudgetOut(
        id=new_budget.id,
        amount=new_budget.amount,
        month=new_budget.month,
        year=new_budget.year,
        category_id=new_budget.category_id,
        spent=spent,
        remaining=new_budget.amount - spent,
    )

@app.get("/budgets", response_model=List[schemas.BudgetOut])
def list_budgets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    budgets = db.query(models.Budget).filter(models.Budget.owner_id == current_user.id).all()
    
    return [
        schemas.BudgetOut(
            id=b.id,
            amount=b.amount,
            month=b.month,
            year=b.year, 
            category_id=b.category_id,
            spent=_calculate_spent(db, current_user, b.month, b.year, b.category_id),
            remaining=b.amount - _calculate_spent(db, current_user, b.month, b.year, b.category_id),
        )
        for b in budgets
    ]