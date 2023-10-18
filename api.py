from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from database import Booking, SessionLocal, BookingCreate, BookingUpdate, BookingResponse
from helper import generate_qr_code, generate_ticket_pdf

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to construct a dictionary response from a Booking instance
def booking_to_dict(booking):
    return {
        "id": booking.id,
        "show_id": booking.show_id,
        "customer_id": booking.customer_id,
        "seats": booking.seats,
        "amount": booking.amount,
        "is_paid": booking.is_paid,
        "is_used": booking.is_used,
        "datetime": booking.datetime,
    }

# Create a new booking
@app.post("/bookings/")
def create_booking(
        show_id: int, 
        customer_id: int, 
        seats: str, 
        amount: int, 
        db: Session = Depends(get_db)
    ):
    db_booking = Booking(
        show_id=show_id,
        customer_id=customer_id,
        seats=seats,
        amount=amount,
        is_paid=False,
        is_used=False
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    return booking_to_dict(db_booking)

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
    return booking_to_dict(db_booking)

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
    QRc=generate_qr_code(validateURL)
    pdf_file_path=generate_ticket_pdf(db_booking.seats, db_booking.amount, QRc, db_booking.datetime)

    # Send the PDF file as a response with appropriate headers
    response = FileResponse(pdf_file_path, headers={"Content-Disposition": "attachment; filename=booking_ticket.pdf"})
    return response

# Validate a booking/ticket as used
@app.put("/bookings/{booking_id}/validate/", response_model=BookingResponse)
def validate_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.is_used:
        raise HTTPException(status_code=400, detail="Booking already validated")
    if not db_booking.is_paid:
        raise HTTPException(status_code=400, detail="Booking not paid")
    
    db_booking.is_used = True
    db.commit()
    db.refresh(db_booking)
    return booking_to_dict(db_booking)

#inform all users with a booking for a specific show that the show is cancelled and notifys them that they will get a refund
@app.put("/shows/{show_id}/cancel/", response_model=BookingResponse)
def cancel_show(show_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.show_id == show_id).all()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    customer_ids = []
    for booking in db_booking:
        if booking.is_paid:
            customer_ids.append([booking.customer_id,booking.amount])
            # Process refund logic here (you can implement this as needed)
            # Assuming refund processed successfully, update the booking status
            booking.is_paid = False
        customer_ids.append([booking.customer_id,0])
    
    #logic to send to usercontainer
    #requests.post('https://dsssi-backend-user.greenplant-9a54dc56.germanywestcentral.azurecontainer.io/users/notify/', json=customer_ids)

    db.commit()
    return len(customer_ids) +"users affected and notified"



# Get a booking by ID
@app.get("/bookings/{booking_id}/", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return booking_to_dict(db_booking)

# Get all bookings
@app.get("/bookings/all", response_model=list[BookingResponse])
def get_all_bookings(db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).all()
    return [booking_to_dict(db_booking) for db_booking in db_bookings]

#get bookings by user id
@app.get("/bookings/user/{user_id}/", response_model=list[BookingResponse])
def get_booking_by_user(user_id: int, db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).filter(Booking.customer_id == user_id).all()
    
    if db_bookings is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return [booking_to_dict(db_booking) for db_booking in db_bookings]

# Get all bookings for a show
@app.get("/bookings/show/{show_id}/", response_model=list[BookingResponse])
def get_bookings_for_show(show_id: int, db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).filter(Booking.show_id == show_id).all()
    
    if db_bookings is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return [booking_to_dict(db_booking) for db_booking in db_bookings]


@app.get("/hello")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
