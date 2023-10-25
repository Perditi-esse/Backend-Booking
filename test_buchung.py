from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from your_application import app, get_db  # replace 'your_application' with the actual name of your application file
import pytest

# Setup for the test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # or the path to your test database

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the dependency with a new database session
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Sample data for creating bookings
test_booking_data = {
    # Populate with the required fields to create a booking.
    # e.g., "transaction_id": "test_trans_001", "show_id": 123, ...
    #copilot please help here

    show_id: 1,
}

def test_booking_lifecycle():
    # Create booking
    create_response = client.post("/bookings/new", json=test_booking_data)
    assert create_response.status_code == 200
    booking_info = create_response.json()
    booking_id = booking_info["id"]

    # Pay for the booking
    payment_response = client.put(f"/bookings/{booking_id}/pay")
    assert payment_response.status_code == 200

    # Validate the booking
    transaction_id = "unique_transaction_002"  # ensure this is unique each test run
    validate_response = client.put(f"/bookings/{booking_id}/validate/{transaction_id}")
    assert validate_response.status_code == 200

    # Cancel the booking
    cancel_transaction_id = "unique_transaction_003"  # ensure this is unique each test run
    cancel_response = client.delete(f"/bookings/{booking_id}/{cancel_transaction_id}")
    assert cancel_response.status_code == 200

    # Attempt to retrieve the canceled booking (expecting failure or not found)
    get_response = client.get(f"/bookings/{booking_id}/")
    assert get_response.status_code == 404  # or appropriate code based on your implementation

@pytest.mark.parametrize("booking_id, expected_status", [(999, 404), (0, 404)])  # Non-existent booking IDs
def test_get_invalid_booking(booking_id, expected_status):
    response = client.get(f"/bookings/{booking_id}/")
    assert response.status_code == expected_status

# Additional tests for other scenarios and edge cases can be added below.
# ...

