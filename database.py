from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from pydantic import BaseModel
from sqlalchemy.sql import func
from datetime import datetime, timedelta

import pyodbc  # Import pyodbc instead of pymssql

# Define your credentials and connection details
username = 'dev'
password = 'Amongus69'
server = 'boooking-transaction-db.database.windows.net'
database = 'booking_transactionDB'
driver = 'ODBC Driver 17 for SQL Server'

# Create the connection string
DATABASE_URL = f'mssql+pymssql://{username}:{password}@{server}:1433/{database}'

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Modelss
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer)
    customer_id = Column(Integer)
    seats = Column(String)
    amount = Column(Integer)
    is_paid = Column(Boolean)
    is_used = Column(Boolean)
    datetime = Column(DateTime, default=func.now())

    def check_expired(self):
        # Check if the booking request is older than 2 days and not paid
        return (datetime.utcnow() - self.datetime) > timedelta(days=2) and not self.is_paid

# Pydantic models for input data (request bodies)
class BookingCreate(BaseModel):
    show_id: int
    customer_id: int
    seats: str
    amount: int

class BookingUpdate(BaseModel):
    is_paid: bool
    is_used: bool

# Pydantic models for output data (response bodies)
class BookingResponse(BaseModel):
    id: int
    show_id: int
    customer_id: int
    seats: str
    amount: int
    is_paid: bool
    is_used: bool
    datetime: datetime

# Create the database tables
Base.metadata.create_all(bind=engine)
