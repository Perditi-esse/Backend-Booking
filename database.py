from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from pydantic import BaseModel
from sqlalchemy.sql import func
from datetime import datetime, timedelta

DATABASE_URL = "sqlite:///./BookingService.db"  # You can change this to your preferred database URL

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
    seats = Column(String)
    amount = Column(Integer)
    qr_code_image = Column(String)
    is_paid = Column(Boolean)
    is_validated = Column(Boolean)
    is_ticket_used = Column(Boolean)
    datetime = Column(DateTime, default=func.now())


class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer)
    customer_id = Column(Integer)
    seats = Column(String)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def check_expired(self):
        # Check if the booking request is older than 2 days and not paid
        return (datetime.utcnow() - self.created_at) > timedelta(days=2) and not self.is_paid


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_request_id = Column(Integer)
    status = Column(String)
    payment_details = Column(String)

    booking_request = relationship("BookingRequest", back_populates="payment")


# Pydantic models for input data (request bodies)
class BookingRequestCreate(BaseModel):
    show_id: int
    customer_id: int
    seats: List[int]


class BookingResponseCreate(BaseModel):
    booking_request_id: int
    show_name: str
    seats: List[int]
    amount: int
    qr_code_image: str
    is_paid: bool
    is_validated: bool
    is_ticket_used: bool


class PaymentRequest(BaseModel):
    booking_request_id: int
    status: str
    payment_details: dict


# Pydantic models for output data (response bodies)
class BookingRequestResponse(BaseModel):
    id: int
    show_id: int
    customer_id: int


class BookingResponseResponse(BaseModel):
    id: int
    booking_request_id: int
    show_name: str
    seats: List[int]
    amount: int
    qr_code_image: str
    is_paid: bool
    is_validated: bool
    is_ticket_used: bool
    datetime: str


class PaymentResponse(BaseModel):
    id: int
    booking_request_id: int
    status: str
    payment_details: dict


# Create the database tables
Base.metadata.create_all(bind=engine)