from sqlalchemy import create_engine, Column, Integer, String,JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from pydantic import BaseModel
from sqlalchemy.sql import func
from datetime import datetime, timedelta

# define a locl database url
DATABASE_URL = "sqlite:///./BookingService.db"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer)
    customer_id = Column(Integer)
    seats = Column(JSON)
    amount = Column(Integer)
    is_paid = Column(Boolean)
    is_used = Column(Boolean)

    
# Pydantic models for input data (request bodies)
class BookingCreate(BaseModel):
    transaction_id: str
    show_id: int
    customer_id: int
    seats: List[int]  # Now it's a list of ints
    amount: int
# Pydantic models for output data (response bodies)
class BookingResponse(BaseModel):
    id: int
    show_id: int
    customer_id: int
    seats: List[int]  # Now it's a list of ints
    amount: int
    is_paid: bool
    is_used: bool

def booking_to_bookingresponse(booking: Booking):
    return BookingResponse(
        id=booking.id,
        show_id=booking.show_id,
        customer_id=booking.customer_id,
        seats=booking.seats,
        amount=booking.amount,
        is_paid=booking.is_paid,
        is_used=booking.is_used
    )

# Create the database tables
Base.metadata.create_all(bind=engine)
