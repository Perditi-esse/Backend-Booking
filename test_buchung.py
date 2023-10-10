import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Booking, BookingCreate
from api import create_booking, cancel_booking, pay_booking, validate_booking, get_db
from fastapi.exceptions import HTTPException

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///test.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture to set up a database session for testing
@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

def test_cancel_booking_that_does_not_exist(test_db):
    with pytest.raises(HTTPException) as e:
        cancel_booking(-1, db=test_db)
    assert e.value.status_code == 404
    assert e.value.detail == "Booking not found"

def test_pay_booking_that_does_not_exist(test_db):
    with pytest.raises(HTTPException) as e:
        pay_booking(-1, db=test_db)
    assert e.value.status_code == 404
    assert e.value.detail == "Booking not found"

def test_validate_booking_that_does_not_exist(test_db):
    with pytest.raises(HTTPException) as e:
        validate_booking(-1, db=test_db)
    assert e.value.status_code == 404
    assert e.value.detail == "Booking not found"

def test_validate_booking_that_is_not_paid(test_db):
    booking_data = BookingCreate(
        show_id=1,
        customer_id=1,
        seats="A1,A2",
        amount=100,
    )
    created_booking = create_booking(booking_data, db=test_db)
    with pytest.raises(HTTPException) as e:
        validate_booking(created_booking['id'], db=test_db)
    assert e.value.status_code == 400
    assert e.value.detail == "Booking not paid"

def test_full_lifecycle(test_db):
    booking_data = BookingCreate(
        show_id=1,
        customer_id=1,
        seats="A1,A2",
        amount=100,
    )
    created_booking = create_booking(booking_data, db=test_db)
    assert created_booking['show_id'] == booking_data.show_id
    assert created_booking['customer_id'] == booking_data.customer_id
    assert created_booking['seats'] == booking_data.seats
    assert created_booking['amount'] == booking_data.amount
    assert not created_booking['is_paid']
    assert not created_booking['is_used']
    pay_booking(created_booking['id'], db=test_db)
    assert test_db.query(Booking).filter(Booking.id == created_booking['id']).first().is_paid
    validate_booking(created_booking['id'], db=test_db)
    assert test_db.query(Booking).filter(Booking.id == created_booking['id']).first().is_used
    cancel_booking(created_booking['id'], db=test_db)

if __name__ == "__main__":
    pytest.main()
