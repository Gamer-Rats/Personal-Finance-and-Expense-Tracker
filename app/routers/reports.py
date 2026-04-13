from fastapi import Request
from fastapi.responses import HTMLResponse
from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.finance import FinanceRepository
from . import router, api_router, templates


@router.get("/reports", response_class=HTMLResponse)
def reports_view(request: Request, user: AuthDep, db: SessionDep):
    repo = FinanceRepository(db)

    expense_result = repo.list_expenses(user.id, page=1, limit=1000)
    budget_result = repo.list_budgets(user.id, page=1, limit=1000)

    expense_rows = expense_result[0]
    budget_rows = budget_result[0]

    expenses = []
    category_totals = {}
    monthly_totals = {}

    for expense in expense_rows:
        category_name = expense.category.name if expense.category else "Uncategorized"

        expenses.append({
            "category": category_name,
            "amount": float(expense.amount),
            "expense_date": expense.expense_date,
        })

        if category_name not in category_totals:
            category_totals[category_name] = 0
        category_totals[category_name] += float(expense.amount)

        month_key = expense.expense_date.strftime("%b %Y")
        if month_key not in monthly_totals:
            monthly_totals[month_key] = 0
        monthly_totals[month_key] += float(expense.amount)

    budgets = []
    for budget in budget_rows:
        category_name = budget.category.name if budget.category else "Uncategorized"
        actual = category_totals.get(category_name, 0)
        limit_amount = float(budget.limit_amount)

        if limit_amount > 0:
            percent = (actual / limit_amount) * 100
        else:
            percent = 0

        if percent <= 80:
            tone = "safe"
        elif percent <= 100:
            tone = "warning"
        else:
            tone = "danger"

        budgets.append({
            "category": category_name,
            "limit_amount": limit_amount,
            "actual": actual,
            "percent": percent,
            "tone": tone,
        })

    monthly_spending_trend = []
    for month, total in monthly_totals.items():
        monthly_spending_trend.append({
            "month": month,
            "total": total,
        })

    top_categories = []
    for category_name, total in category_totals.items():
        top_categories.append({
            "name": category_name,
            "total": total,
        })

    top_categories.sort(key=lambda x: x["total"], reverse=True)
    top_categories = top_categories[:3]

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": user,
            "expenses": expenses,
            "budgets": budgets,
            "monthly_spending_trend": monthly_spending_trend,
            "top_categories": top_categories,
        },
    )


@api_router.get("/expense-stats")
def expense_stats(user: AuthDep, db: SessionDep):
    repo = FinanceRepository(db)
    return repo.expense_breakdown(user.id)


@api_router.get("/subscription-stats")
def subscription_stats(user: AuthDep, db: SessionDep):
    repo = FinanceRepository(db)
    return repo.subscription_breakdown(user.id)
