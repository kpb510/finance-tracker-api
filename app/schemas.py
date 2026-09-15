from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import date
from typing import Optional 
from enum import Enum

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class UserOut(BaseModel):
    """What we send back - notice there is no password field at all."""
    id: int
    email: EmailStr
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class TransactionBase(BaseModel):
    amount: float = Field(gt=0)
    description: Optional[str] = None
    date: date
    type: TransactionType
    category_id: Optional[int] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date] = None
    type: Optional[str] = None # "income" or "expense"
    category_id: Optional[int] = None
    
class TransactionOut(TransactionBase):
    id: int
    owner_id: int
    
    model_config = ConfigDict(from_attributes=True)

class CategoryCreate(BaseModel):
    name: str
    
class CategoryOut(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)

class MonthlySummary(BaseModel):
    year: int
    month: int
    total_income: float
    total_expense: float 
    net: float 

class BudgetCreate(BaseModel):
    amount: float = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    category_id: Optional[int] = None
    
class BudgetOut(BaseModel):
    id: int
    amount: float
    month: int
    year: int
    category_id: Optional[int] = None 
    spent: float
    remaining: float
    
    model_config = ConfigDict(from_attributes=True)   