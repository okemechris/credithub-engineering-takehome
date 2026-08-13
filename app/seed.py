"""Seed synthetic loans in a range of states.

Run once before starting the app:  python -m app.seed
"""

from .db import Base, SessionLocal, engine
from .models import Loan, LoanStatus


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Loan).delete()
    loans = [
        Loan(borrower_name="Adaeze Okafor", principal=100000, total_repayable=112000, total_paid=0, status=LoanStatus.active),
        Loan(borrower_name="Bola Adeyemi", principal=50000, total_repayable=56000, total_paid=28000, status=LoanStatus.active),
        Loan(borrower_name="Chidi Nwosu", principal=200000, total_repayable=224000, total_paid=224000, status=LoanStatus.paid_off),
        Loan(borrower_name="Fatima Bello", principal=75000, total_repayable=84000, total_paid=0, status=LoanStatus.cancelled),
        Loan(borrower_name="Emeka Obi", principal=300000, total_repayable=339000, total_paid=100000, status=LoanStatus.written_off),
        # Non-round amounts — a repayment that "should" close this loan exactly
        # is a good place to check your money handling.
        Loan(borrower_name="Ngozi Eze", principal=33333, total_repayable=37333.33, total_paid=0, status=LoanStatus.active),
    ]
    db.add_all(loans)
    db.commit()
    print(f"seeded {len(loans)} loans")
    db.close()


if __name__ == "__main__":
    seed()
