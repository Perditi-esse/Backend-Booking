from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from sqlalchemy.orm import Session
from database import Booking, SessionLocal, BookingCreate, BookingUpdate, BookingResponse
from helper import Helper
app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a new booking
@app.post("/bookings/", response_model=BookingResponse)
def create_booking(booking_data: BookingCreate, db: Session = Depends(get_db)):
    db_booking = Booking(**booking_data.dict(), is_paid=False, is_used=False)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

# Cancel a booking and process a refund if paid
@app.delete("/bookings/{booking_id}/", response_model=BookingResponse)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.is_paid:
        # Process refund logic here (you can implement this as needed)
        # Assuming refund processed successfully, update the booking status
        db_booking.is_paid = False
    
    db.delete(db_booking)
    db.commit()
    return db_booking

# Pay for a booking
@app.put("/bookings/{booking_id}/pay/", response_model=BookingResponse)
def pay_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db_booking.is_paid = True
    db.commit()
    db.refresh(db_booking)
    validateURL="https://dsssi-backend-booking.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/bookings/"+str(booking_id)+"/validate/"
    QRc=Helper.generate_qr_code(validateURL)
    PDFFile=Helper.generate_ticket_pdf(db_booking.seats, db_booking.amount, QRc, db_booking.datetime)
    return UploadFile(PDFFile, attachment_filename='ticket.pdf')

# Validate a booking/ticket as used
@app.put("/bookings/{booking_id}/validate/", response_model=BookingResponse)
def validate_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.is_used:
        raise HTTPException(status_code=400, detail="Booking already validated")
    
    db_booking.is_used = True
    db.commit()
    db.refresh(db_booking)
    return db_booking

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)