from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import Booking, BookingRequest, Payment, SessionLocal, BookingRequestCreate, PaymentResponse
from datetime import datetime
from helper import Helper

app = FastAPI()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Method to create a booking request
@app.post("/create_booking/", response_model=BookingRequestCreate)
def create_booking(data: BookingRequestCreate, db: Session = Depends(get_db)):
    # Create a new booking request
    booking_request = BookingRequest(
        show_id=data.show_id,
        customer_id=data.customer_id,
        seats=','.join(map(str, data.seats))
    )
    
    db.add(booking_request)
    db.commit()
    db.refresh(booking_request)
    
    return booking_request

# Method to initiate payment for a booking and return the PDF
@app.post("/initiate_payment/{bookingId}", response_model=str)
def initiate_payment(bookingId: int, db: Session = Depends(get_db)):
    booking_request = db.query(BookingRequest).filter(BookingRequest.id == bookingId).first()
    if not booking_request:
        raise HTTPException(status_code=404, detail="Booking Request not found")
    
    # Create a payment record (UNVALIDATED BOOKING) and return a PDF with QR code
    payment = Payment(
        booking_request_id=bookingId,
        status="UNVALIDATED",
        payment_details={}
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Generate the QR code for validation and create a PDF
    qr_code_data = f"/validate_ticket/{bookingId}"
    qr_code_image = Helper.generate_qr_code(qr_code_data)
    
    date_time = datetime.utcnow()  # Replace with actual booking date and time
    
    pdf_file_path = Helper.generate_ticket_pdf(
        seats=booking_request.seats.split(','),
        amount=0,  # Replace with actual amount
        qr_code_image=qr_code_image,
        date_time=date_time
    )
    
    return pdf_file_path

# Method to validate a ticket for a booking
@app.post("/validate_ticket/{bookingId}")
def validate_ticket(bookingId: int, db: Session = Depends(get_db)):
    booking_request = db.query(BookingRequest).filter(BookingRequest.id == bookingId).first()
    if not booking_request:
        raise HTTPException(status_code=404, detail="Booking Request not found")
    
    payment = db.query(Payment).filter(Payment.booking_request_id == bookingId).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status != "UNVALIDATED":
        raise HTTPException(status_code=400, detail="Payment is already validated")
    
    # Implement any additional validation logic here
    
    # Mark the payment as validated
    payment.status = "VALIDATED"
    db.commit()
    
    # Mark the booking request as paid
    booking_request.is_paid = True
    db.commit()
    
    return {"message": "Ticket validated successfully"}

# Method for testing purposes
@app.get("/helloworld")
def helloworld():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)