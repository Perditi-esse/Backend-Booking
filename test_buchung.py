import pytest
from fastapi.testclient import TestClient
from api import app  # Adjust the import statement based on your project structure

client = TestClient(app)

# Test case for the scenario where we try to cancel a booking that doesn't exist
def test_cancel_booking_that_does_not_exist():
    response = client.delete(f"/bookings/99999/nonexistenttransaction123")
    assert response.status_code == 404
    assert response.json() == {"detail": "Booking not found"}

# Test case for the scenario where we try to pay for a booking that doesn't exist
def test_pay_booking_that_does_not_exist():
    response = client.put(f"/bookings/99999/pay/nonexistenttransaction1234")
    assert response.status_code == 404
    assert response.json() == {"detail": "Booking not found"}

# Test case for the scenario where we try to validate a booking that doesn't exist
def test_validate_booking_that_does_not_exist():
    response = client.put(f"/bookings/99999/validate/nonexistenttransaction12345")
    assert response.status_code == 404
    assert response.json() == {"detail": "Booking not found"}

# Test case for the scenario where we try to validate a booking that is not paid
def test_validate_booking_that_is_not_paid():
    response=client.post("/bookings/new", json={"transaction_id":"sdsd","show_id": -1, "customer_id": 1, "seats": "A1", "amount": 100})
    print(response.json())
    booking_id_not_paid = response.json()["id"]
    response = client.put(f"/bookings/{booking_id_not_paid}/validate/nonexistenttransaction123456")
    assert response.status_code == 400
    assert response.json() == {"detail": "Booking not paid"}

if __name__ == "__main__":
    test_validate_booking_that_is_not_paid()
    pytest.main()