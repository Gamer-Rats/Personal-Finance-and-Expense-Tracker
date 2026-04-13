import typer
from datetime import date
from app.database import create_db_and_tables, get_cli_session, drop_all
from app.models.user import User
from app.models.finance import ExpenseCategory, Expense, Subscription, Budget
from app.utilities.security import encrypt_password


cli = typer.Typer(no_args_is_help=True)


@cli.callback()
def app():
    """Personal finance CLI commands."""
    pass


@cli.command()
def initialize():
    with get_cli_session() as db:
        drop_all()
        create_db_and_tables()

        bob = User(
            username="bob",
            email="bob@mail.com",
            password=encrypt_password("bobpass"),
            role="regular_user",
            monthly_income=8500.00,
        )
        admin = User(
            username="pam",
            email="pam@mail.com",
            password=encrypt_password("pampass"),
            role="admin",
            monthly_income=0.0,
        )
        db.add(bob)
        db.add(admin)
        db.commit()
        db.refresh(bob)

        groceries = ExpenseCategory(user_id=bob.id, name="Groceries")
        transport = ExpenseCategory(user_id=bob.id, name="Transport")
        entertainment = ExpenseCategory(user_id=bob.id, name="Entertainment")
        db.add(groceries)
        db.add(transport)
        db.add(entertainment)
        db.commit()
        db.refresh(groceries)
        db.refresh(transport)
        db.refresh(entertainment)

        db.add(Expense(user_id=bob.id, category_id=groceries.id, title="Supermarket", amount=425.50, expense_date=date.today(), notes="Weekly groceries"))
        db.add(Expense(user_id=bob.id, category_id=transport.id, title="Fuel", amount=300.00, expense_date=date.today(), notes="Car fuel"))
        db.add(Expense(user_id=bob.id, category_id=entertainment.id, title="Movie", amount=90.00, expense_date=date.today(), notes="Weekend outing"))
        db.add(Subscription(user_id=bob.id, category_id=entertainment.id, name="Netflix", amount=15.99, billing_cycle="monthly", next_payment_date=date.today(), active=True))
        db.add(Subscription(user_id=bob.id, category_id=entertainment.id, name="Spotify", amount=9.99, billing_cycle="monthly", next_payment_date=date.today(), active=True))
        db.add(Budget(user_id=bob.id, category_id=groceries.id, month=date.today().strftime("%Y-%m"), limit_amount=1500.00))
        db.add(Budget(user_id=bob.id, category_id=transport.id, month=date.today().strftime("%Y-%m"), limit_amount=1200.00))
        db.commit()

        print("Database initialized with demo finance data")


if __name__ == "__main__":
    cli()
