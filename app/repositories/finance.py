from datetime import date
from sqlmodel import Session, select, func, or_
from app.models.finance import ExpenseCategory, Expense, Subscription, Budget
from app.models.user import User
from app.utilities.pagination import Pagination


class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_categories(self, user_id: int):
        return self.db.exec(
            select(ExpenseCategory)
            .where(ExpenseCategory.user_id == user_id)
            .order_by(ExpenseCategory.name)
        ).all()

    def get_or_create_category(self, user_id: int, category_name: str | None):
        if not category_name:
            return None
        category_name = category_name.strip()
        if not category_name:
            return None
        category = self.db.exec(
            select(ExpenseCategory).where(
                ExpenseCategory.user_id == user_id,
                ExpenseCategory.name == category_name,
            )
        ).one_or_none()
        if category:
            return category
        category = ExpenseCategory(user_id=user_id, name=category_name)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def list_expenses(
        self,
        user_id: int,
        q: str = "",
        category_name: str = "",
        min_amount: float | None = None,
        max_amount: float | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        limit: int = 10,
    ):
        offset = (page - 1) * limit
        db_qry = select(Expense).where(Expense.user_id == user_id)
        if q:
            db_qry = db_qry.where(
                or_(
                    Expense.title.ilike(f"%{q}%"),
                    Expense.notes.ilike(f"%{q}%"),
                    Expense.category.has(ExpenseCategory.name.ilike(f"%{q}%")),
                )
            )
        if category_name:
            db_qry = db_qry.where(Expense.category.has(ExpenseCategory.name.ilike(f"%{category_name}%")))
        if min_amount is not None:
            db_qry = db_qry.where(Expense.amount >= min_amount)
        if max_amount is not None:
            db_qry = db_qry.where(Expense.amount <= max_amount)
        if start_date is not None:
            db_qry = db_qry.where(Expense.expense_date >= start_date)
        if end_date is not None:
            db_qry = db_qry.where(Expense.expense_date <= end_date)
        count_qry = select(func.count()).select_from(db_qry.subquery())
        total_count = self.db.exec(count_qry).one()
        items = self.db.exec(
            db_qry.order_by(Expense.expense_date.desc(), Expense.id.desc()).offset(offset).limit(limit)
        ).all()
        pagination = Pagination(total_count=total_count, current_page=page, limit=limit)
        return items, pagination

    def list_subscriptions(
        self,
        user_id: int,
        q: str = "",
        category_name: str = "",
        min_amount: float | None = None,
        max_amount: float | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        active: str = "",
        page: int = 1,
        limit: int = 10,
    ):
        offset = (page - 1) * limit
        db_qry = select(Subscription).where(Subscription.user_id == user_id)
        if q:
            db_qry = db_qry.where(
                or_(
                    Subscription.name.ilike(f"%{q}%"),
                    Subscription.category.has(ExpenseCategory.name.ilike(f"%{q}%")),
                )
            )
        if category_name:
            db_qry = db_qry.where(Subscription.category.has(ExpenseCategory.name.ilike(f"%{category_name}%")))
        if min_amount is not None:
            db_qry = db_qry.where(Subscription.amount >= min_amount)
        if max_amount is not None:
            db_qry = db_qry.where(Subscription.amount <= max_amount)
        if start_date is not None:
            db_qry = db_qry.where(Subscription.next_payment_date >= start_date)
        if end_date is not None:
            db_qry = db_qry.where(Subscription.next_payment_date <= end_date)
        if active == "active":
            db_qry = db_qry.where(Subscription.active == True)
        elif active == "inactive":
            db_qry = db_qry.where(Subscription.active == False)
        count_qry = select(func.count()).select_from(db_qry.subquery())
        total_count = self.db.exec(count_qry).one()
        items = self.db.exec(
            db_qry.order_by(Subscription.next_payment_date.asc(), Subscription.id.desc()).offset(offset).limit(limit)
        ).all()
        pagination = Pagination(total_count=total_count, current_page=page, limit=limit)
        return items, pagination

    def list_budgets(
        self,
        user_id: int,
        month: str = "",
        category_name: str = "",
        min_amount: float | None = None,
        max_amount: float | None = None,
        page: int = 1,
        limit: int = 10,
    ):
        offset = (page - 1) * limit
        db_qry = select(Budget).where(Budget.user_id == user_id)
        if month:
            db_qry = db_qry.where(Budget.month == month)
        if category_name:
            db_qry = db_qry.where(Budget.category.has(ExpenseCategory.name.ilike(f"%{category_name}%")))
        if min_amount is not None:
            db_qry = db_qry.where(Budget.limit_amount >= min_amount)
        if max_amount is not None:
            db_qry = db_qry.where(Budget.limit_amount <= max_amount)
        count_qry = select(func.count()).select_from(db_qry.subquery())
        total_count = self.db.exec(count_qry).one()
        items = self.db.exec(db_qry.order_by(Budget.month.desc(), Budget.id.desc()).offset(offset).limit(limit)).all()
        pagination = Pagination(total_count=total_count, current_page=page, limit=limit)
        return items, pagination

    def get_expense(self, expense_id: int, user_id: int):
        return self.db.exec(select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)).one_or_none()

    def get_subscription(self, subscription_id: int, user_id: int):
        return self.db.exec(select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user_id)).one_or_none()

    def get_budget(self, budget_id: int, user_id: int):
        return self.db.exec(select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)).one_or_none()

    def create_expense(self, user_id: int, title: str, amount: float, expense_date: date, notes: str, category_name: str = ""):
        category = self.get_or_create_category(user_id, category_name)
        expense = Expense(
            user_id=user_id,
            category_id=category.id if category else None,
            title=title,
            amount=amount,
            expense_date=expense_date,
            notes=notes,
        )
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def update_expense(self, expense: Expense, title: str, amount: float, expense_date: date, notes: str, category_name: str = ""):
        category = self.get_or_create_category(expense.user_id, category_name)
        expense.title = title
        expense.amount = amount
        expense.expense_date = expense_date
        expense.notes = notes
        expense.category_id = category.id if category else None
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete_expense(self, expense: Expense):
        self.db.delete(expense)
        self.db.commit()

    def create_subscription(self, user_id: int, name: str, amount: float, billing_cycle: str, next_payment_date: date, active: bool, category_name: str = ""):
        category = self.get_or_create_category(user_id, category_name)
        subscription = Subscription(
            user_id=user_id,
            category_id=category.id if category else None,
            name=name,
            amount=amount,
            billing_cycle=billing_cycle,
            next_payment_date=next_payment_date,
            active=active,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def update_subscription(self, subscription: Subscription, name: str, amount: float, billing_cycle: str, next_payment_date: date, active: bool, category_name: str = ""):
        category = self.get_or_create_category(subscription.user_id, category_name)
        subscription.name = name
        subscription.amount = amount
        subscription.billing_cycle = billing_cycle
        subscription.next_payment_date = next_payment_date
        subscription.active = active
        subscription.category_id = category.id if category else None
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def delete_subscription(self, subscription: Subscription):
        self.db.delete(subscription)
        self.db.commit()

    def create_budget(self, user_id: int, month: str, limit_amount: float, category_name: str = ""):
        category = self.get_or_create_category(user_id, category_name)
        budget = Budget(
            user_id=user_id,
            category_id=category.id if category else None,
            month=month,
            limit_amount=limit_amount,
        )
        self.db.add(budget)
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def update_budget(self, budget: Budget, month: str, limit_amount: float, category_name: str = ""):
        category = self.get_or_create_category(budget.user_id, category_name)
        budget.month = month
        budget.limit_amount = limit_amount
        budget.category_id = category.id if category else None
        self.db.add(budget)
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def delete_budget(self, budget: Budget):
        self.db.delete(budget)
        self.db.commit()

    def get_dashboard_summary(self, user: User):
        today = date.today()
        current_month = today.strftime("%Y-%m")

        monthly_expenses = self.db.exec(
            select(Expense).where(
                Expense.user_id == user.id,
                Expense.expense_date >= date(today.year, today.month, 1),
            )
        ).all()
        monthly_expense_total = sum(item.amount for item in monthly_expenses)

        active_subscriptions = self.db.exec(
            select(Subscription).where(Subscription.user_id == user.id, Subscription.active == True)
        ).all()
        monthly_subscription_total = 0.0
        for item in active_subscriptions:
            if item.billing_cycle == "yearly":
                monthly_subscription_total += item.amount / 12
            else:
                monthly_subscription_total += item.amount

        budgets = self.db.exec(
            select(Budget).where(Budget.user_id == user.id, Budget.month == current_month)
        ).all()
        monthly_budget_total = sum(item.limit_amount for item in budgets)
        monthly_total_spending = monthly_expense_total + monthly_subscription_total
        burn_rate = (monthly_total_spending / user.monthly_income) if user.monthly_income > 0 else 0
        savings_remaining = user.monthly_income - monthly_total_spending
        savings_rate = (savings_remaining / user.monthly_income) if user.monthly_income > 0 else 0

        if user.monthly_income <= 0:
            burn_rate_status = "No income set"
            burn_rate_tone = "neutral"
        elif burn_rate < 0.5:
            burn_rate_status = "Excellent"
            burn_rate_tone = "good"
        elif burn_rate < 0.75:
            burn_rate_status = "Healthy"
            burn_rate_tone = "good"
        elif burn_rate <= 1:
            burn_rate_status = "Caution"
            burn_rate_tone = "warning"
        else:
            burn_rate_status = "Overspending"
            burn_rate_tone = "danger"

        recent_expenses = self.db.exec(
            select(Expense)
            .where(Expense.user_id == user.id)
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .limit(5)
        ).all()

        return {
            "current_month": current_month,
            "monthly_expense_total": monthly_expense_total,
            "monthly_subscription_total": monthly_subscription_total,
            "monthly_total_spending": monthly_total_spending,
            "monthly_budget_total": monthly_budget_total,
            "burn_rate": burn_rate,
            "savings_remaining": savings_remaining,
            "savings_rate": savings_rate,
            "burn_rate_status": burn_rate_status,
            "burn_rate_tone": burn_rate_tone,
            "recent_expenses": recent_expenses,
        }

    def expense_breakdown(self, user_id: int):
        expenses = self.db.exec(select(Expense).where(Expense.user_id == user_id)).all()
        result = {}
        for expense in expenses:
            key = expense.category.name if expense.category else "Uncategorized"
            result[key] = result.get(key, 0) + expense.amount
        return result

    def subscription_breakdown(self, user_id: int):
        subscriptions = self.db.exec(select(Subscription).where(Subscription.user_id == user_id, Subscription.active == True)).all()
        result = {}
        for item in subscriptions:
            result[item.name] = item.amount
        return result
