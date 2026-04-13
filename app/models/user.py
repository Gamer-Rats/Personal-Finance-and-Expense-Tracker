from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from pydantic import EmailStr

if TYPE_CHECKING:
    from app.models.finance import ExpenseCategory, Expense, Subscription, Budget

class UserBase(SQLModel,):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str
    role:str = ""
    monthly_income: float = 0.0

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    categories: list["ExpenseCategory"] = Relationship(back_populates="user")
    expenses: list["Expense"] = Relationship(back_populates="user")
    subscriptions: list["Subscription"] = Relationship(back_populates="user")
    budgets: list["Budget"] = Relationship(back_populates="user")
