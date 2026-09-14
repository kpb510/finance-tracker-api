from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # "relationship" is not a real column. It allows us to write
    # user.transactions in python and get a list back automatically.
    transactions = relationship("Transaction", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")
    
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # e.g. "Food", "Bills" etc.
    
    transactions = relationship("Transaction", back_populates="category")

class Transaction(Base): 
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True,
                index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    type = Column(String, nullable=False) # "income" or "expense"
    
    # Foreign key = "this column's value must match an id in another table"
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

class Budget(Base): 
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    month = Column(Integer, nullable=False) # 1-12
    year = Column(Integer, nullable=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    owner = relationship("User", back_populates="budgets")
    