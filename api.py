from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from database import booking_to_bookingresponse,Booking, SessionLocal, BookingCreate, BookingResponse
from helper import generate_qr_code, generate_ticket_pdf
from typing import List
import requests
from fastapi import FastAPI, HTTPException, Depends
import threading
import itertools
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#mutex for the resource
resource_lock = threading.Lock()

#transaction id generator
#list for transaction ids
inward_transaction_ids = []

def get_idempotency_key(string):
    response = requests.post('https://backend-idempotency-provider.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/generate-key/', json={'description': string})
    data = response.json()
    idempotency_key = data['key']
    return idempotency_key

def check_idempotency_key(idempotency_key):
    if idempotency_key in inward_transaction_ids:
        return True #the request has already been processed
    else:
        return False #the request has not been processed yet
    
def contact_user_container(customer_id,idempotency_key,message):
    url = "https://backend-message-board.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/messages/"
    payloaddict={"message":{"header":message["message"]["header"],"body":message["message"]["body"]},"transaction_id": idempotency_key,"recipient": customer_id}
    payload = json.dumps(payloaddict)
    headers = {}
    requests.request("POST", url, headers=headers, data=payload)
    
# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


    
# Create a new booking
@app.post("/bookings/new", response_model=BookingResponse)
def create_booking(request: BookingCreate, db: Session = Depends(get_db)):
 
    transID=request.transaction_id
    with resource_lock:
        if check_idempotency_key(transID):
            raise HTTPException(status_code=400, detail="Transaction already received")
        # add it only after checking if it is already in the list
        inward_transaction_ids.append(transID)

    # get all the request infos
    show_id = request.show_id
    customer_id = request.customer_id
    seats = request.seats
    amount = request.amount


    
    # enter mutex
    with resource_lock:
        # check if a seat is already booked
        seatlist = [] #for all already booked seats
        db_bookings = db.query(Booking).filter(Booking.show_id == show_id).all()
        for booking in db_bookings:
            seatlist.append(booking.seats)


        seatlist = list(itertools.chain.from_iterable(seatlist))
        
        if any(seat in seatlist for seat in seats):
            raise HTTPException(status_code=400, detail="Seat already booked")
        db_booking = Booking(show_id=show_id, customer_id=customer_id, seats=seats, amount=amount, is_paid=False, is_used=False)
        db.add(db_booking)
        db.commit()
        
        # exit 

    ##start the eventual concistency
        for seat in seats:
            key=get_idempotency_key(f"marking seat {seat} as booked in show{show_id}")
            
            url = f'https://dsssi-backend-lookup.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/sitzplatzReservieren?sitzplan={show_id}&sitz={seat}&besetzt=true&transID={key}'

            payload = {}
            headers = {}

            requests.request("POST", url, headers=headers, data=payload)
    
        #inform user seats are blocked and he has to pay
        idempotency_key=get_idempotency_key(f"booking contacting the user {db_booking.customer_id}container because of show "+str(db_booking.show_id))
        payload_dict = {
        "message": {
            "header": "Your Booking has been Recieved",
            "body": "Thank you for your Order please pay now."
        }
        }
        contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)

    

    
    return booking_to_bookingresponse(db_booking)

# Cancel a booking and process a refund if paid
@app.delete("/bookings/{booking_id}/{transaction_id}", response_model=BookingResponse)
def cancel_booking(booking_id: int, transaction_id: str,db: Session = Depends(get_db)):
    with resource_lock:
        if check_idempotency_key(transaction_id):
            raise HTTPException(status_code=400, detail="Transaction already recieved")
        #add it only after checking if it is already in the list
        inward_transaction_ids.append(transaction_id)


    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if db_booking.is_paid:
        # Process refund logic here (you can implement this as needed)
        # request to user container to give the man his balance back
        db_booking.is_paid = False
        # Generate a new idempotency key for the outbound transaction
        idempotency_key=get_idempotency_key(f"booking contacting the user {db_booking.customer_id}container because of show "+str(db_booking.show_id))
        payload_dict = {
        "message": {
            "header": "Your Booking has been Cancelled",
            "body": f'we will refund you {db_booking.amount}$.'
        }
        }
        contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)
    else:

    # Generate a new idempotency key for the outbound transaction
        idempotency_key=get_idempotency_key(f"booking contacting the user {db_booking.customer_id}container because of show "+str(db_booking.show_id))
        payload_dict = {
        "message": {
            "header": "Your Booking has been Cancelled",
            "body": "We are sorry."
        }
        }
        contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)
    
    db.delete(db_booking)
    db.commit()



    #start eventual consistency
    seats=db_booking.seats
    show_id=db_booking.show_id
    for seat in seats:
        key=get_idempotency_key(f"marking seat {seat} as notbooked in show{show_id}")

        url = f'https://dsssi-backend-lookup.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/sitzplatzReservieren?sitzplan={show_id}&sitz={seat}&besetzt=false&transID={key}'

        payload = {}
        headers = {}

        requests.request("POST", url, headers=headers, data=payload)


        return booking_to_bookingresponse(db_booking)

# Pay for a booking
@app.put("/bookings/{booking_id}/pay")
def pay_booking(booking_id: int, db: Session = Depends(get_db)):
    
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.is_paid:
        raise HTTPException(status_code=200, detail="Booking already paid")

    db_booking.is_paid = True
    db.commit()
    db.refresh(db_booking)
    # Generate a new idempotency key for the outbound transaction
    idempotency_key=get_idempotency_key(f"booking contacting the user {db_booking.customer_id}container because of show "+str(db_booking.show_id))
    payload_dict = {
    "message": {
        "header": "Your Booking has been Paid",
        "body": "Thank you for your payment."
    }
    }
    contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)

    # Generate a QR code for the booking
    key=get_idempotency_key('booking validating the booking'+str(db_booking.id))
    # Generate a QR code for the booking


    validateURL=f'https://dsssi-backend-booking.greenplant-9a54dc56.germanywestcentral.azurecontainerapps.io/bookings/{db_booking.id}/validate/{key}'
    QRc=generate_qr_code(validateURL)
    
    pdf_file_path=generate_ticket_pdf(db_booking.seats, db_booking.amount, QRc )
    
    # Send the PDF file as a response with appropriate headers
    response = FileResponse(pdf_file_path, headers={"Content-Disposition": "attachment; filename=booking_ticket.pdf"})

    
    return response

# Validate a booking/ticket as used
@app.put("/bookings/{booking_id}/validate/{transaction_id}", response_model=BookingResponse)
def validate_booking(booking_id: int,transaction_id: str, db: Session = Depends(get_db)):
    with resource_lock:
        if check_idempotency_key(transaction_id):
            raise HTTPException(status_code=400, detail="Transaction already recieved")
        #add it only after checking if it is already in the list
        inward_transaction_ids.append(transaction_id)


    db_booking = db.query(Booking).filter(Booking.id == booking_id)
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if not db_booking.is_paid:
        raise HTTPException(status_code=400, detail="Booking not paid")
    
    if db_booking.is_used:
        raise HTTPException(status_code=400, detail="Booking already validated")
    
    db_booking.is_used = True
    db.commit()
    db.refresh(db_booking)

    #inform user seats are blocked and he has to pay
    idempotency_key=get_idempotency_key(f"booking contacting the user {db_booking.customer_id}container because of show "+str(db_booking.show_id))
    payload_dict = {
    "message": {
        "header": "Thank you for your Visit",
        "body": "We hope you enjoyed the show."
    }
    }
    contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)


    return booking_to_bookingresponse(db_booking)

#inform all users with a booking for a specific show that the show is cancelled and notifys them that they will get a refund
@app.put("/shows/{show_id}/cancel/{transaction_id}", response_model=BookingResponse)
def cancel_show(show_id: int,transaction_id: str, db: Session = Depends(get_db)):
    with resource_lock:
        if check_idempotency_key(transaction_id):
            raise HTTPException(status_code=400, detail="Transaction already recieved")
        #add it only after checking if it is already in the list
        inward_transaction_ids.append(transaction_id)
    


    db_booking = db.query(Booking).filter(Booking.show_id == show_id).all()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    #generate a new idempotency key for outbound transaction
    customer_ids = []
    for booking in db_booking:
        if booking.is_paid:
            customer_ids.append([booking.customer_id,booking.amount])
            booking.is_paid = False
        customer_ids.append([booking.customer_id,0])
    
    for customer_id in customer_ids:
        idempotency_key=get_idempotency_key(f"booking contacting the user {customer_id[0]}container because of show "+str(show_id))
        payload_dict = {
        "message": {
            "header": "The Show you booked has been cancelled",
            "body": "We hope you can understant that. You will get a refund of "+str(customer_id[1])+"$."
        }
        }
        contact_user_container(db_booking.customer_id,idempotency_key,payload_dict)
    db.commit()
    return len(customer_ids) +"users affected and notified"



# Get a booking by ID
@app.get("/bookings/{booking_id}/", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return booking_to_bookingresponse(db_booking)

#GET a booking by transaction id
@app.get("/bookings/all", response_model=List[BookingResponse])
def get_all_bookings(db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).all()
    return [booking_to_bookingresponse(db_booking) for db_booking in db_bookings]

#GET a booking by user id
@app.get("/bookings/user/{user_id}/", response_model=List[BookingResponse])
def get_booking_by_user(user_id: int, db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).filter(Booking.customer_id == user_id).all()
    
    if db_bookings is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return [booking_to_bookingresponse(db_booking) for db_booking in db_bookings]

#GET a booking by show id
@app.get("/bookings/show/{show_id}/", response_model=List[BookingResponse])
def get_bookings_for_show(show_id: int, db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).filter(Booking.show_id == show_id).all()
    
    if db_bookings is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return [booking_to_bookingresponse(db_booking) for db_booking in db_bookings]

#GET Booking ID per User Per show
@app.get("/bookings/show/{show_id}/user/{user_id}/", response_model=List[BookingResponse])
def get_booking_for_show_and_user(show_id: int, user_id: int, db: Session = Depends(get_db)):
    db_bookings = db.query(Booking).filter(Booking.show_id == show_id).filter(Booking.customer_id == user_id).all()
    
    if db_bookings is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return [booking_to_bookingresponse(db_booking) for db_booking in db_bookings]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    