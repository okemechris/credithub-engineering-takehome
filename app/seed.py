"""Seed synthetic loans + a few pending payment events.

Run once before starting the app:  python -m app.seed
"""

from .db import Base, SessionLocal, engine
from .models import Loan, LoanStatus, PaymentEvent, PaymentStatus


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(PaymentEvent).delete()
    db.query(Loan).delete()

    loans = [
        Loan(id=1, borrower_name="Adaeze Okafor", principal=100000, total_repayable=112000, total_paid=0, status=LoanStatus.active),
        Loan(id=2, borrower_name="Bola Adeyemi", principal=50000, total_repayable=56000, total_paid=28000, status=LoanStatus.active),
        Loan(id=3, borrower_name="Chidi Nwosu", principal=200000, total_repayable=224000, total_paid=224000, status=LoanStatus.paid_off),
        Loan(id=4, borrower_name="Fatima Bello", principal=75000, total_repayable=84000, total_paid=0, status=LoanStatus.cancelled),
        Loan(id=5, borrower_name="Emeka Obi", principal=300000, total_repayable=339000, total_paid=100000, status=LoanStatus.written_off),
        # Non-round amount — an exact-payoff event is a good money-handling check.
        Loan(id=6, borrower_name="Ngozi Eze", principal=33333, total_repayable=37333.33, total_paid=0, status=LoanStatus.active),
    ]
    db.add_all(loans)

    # Pending payments waiting to be reconciled. A couple are "interesting".
    events = [
        PaymentEvent(external_ref="PSK-9001", loan_id=1, amount=20000, channel="paystack"),   # normal partial
        PaymentEvent(external_ref="PSK-9002", loan_id=6, amount=37333.33, channel="paystack"), # exact payoff (float)
        PaymentEvent(external_ref="PSK-9003", loan_id=4, amount=5000, channel="gsi"),          # loan is cancelled
        PaymentEvent(external_ref="PSK-9001", loan_id=1, amount=20000, channel="paystack"),    # DUPLICATE of the first (redelivery)
        PaymentEvent(external_ref="PSK-9004", loan_id=2, amount=999999, channel="cbs"),        # overpayment
    ]
    db.add_all(events)
    db.commit()
    print(f"seeded {len(loans)} loans and {len(events)} pending payment events")
    db.close()


if __name__ == "__main__":
    seed()
