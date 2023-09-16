import os
from datetime import datetime, timedelta
from io import BytesIO
import qrcode
from flask import Flask, jsonify, request, send_file, url_for
from fpdf import FPDF
from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker



class Helper:
    def generate_qr_code(url):
        # Create a QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create an image from the QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save the image to a BytesIO object
        img_buffer = BytesIO()
        qr_img.save(img_buffer, format="PNG")

        # Return the QR code image as bytes
        return img_buffer.getvalue()



    class TicketPDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "Ticket", 0, 1, "C")

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Generated on {datetime.now()}", 0, 0, "C")

        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, title, 0, 1)

        def chapter_body(self, body):
            self.set_font("Arial", "", 12)
            self.multi_cell(0, 10, body)
            self.ln()

    def generate_ticket_pdf(seats, amount, qr_code_image, date_time):
        pdf = Helper.TicketPDF()
        pdf.add_page()
        pdf.chapter_title("Ticket Details:")
        pdf.chapter_body(f"Seats: {seats}")
        pdf.chapter_body(f"Amount: {amount}")
        pdf.chapter_body(f"Date and Time: {date_time}")

        try:
            # Try to add the image with error handling
            pdf.image(qr_code_image, x=10, y=pdf.get_y(), w=40)
        except Exception as e:
            print(f"Error adding image: {e}")

        pdf.output("ticket.pdf")


# SQLAlchemy setup
engine = create_engine('sqlite:///booking_service.sqlite')
Base = declarative_base()

# Define the SQLAlchemy models
class BookingRequest(Base):
    __tablename__ = 'booking_requests'

    id = Column(Integer, primary_key=True)
    
    # Foreign key to the 'shows' table
    #show_id = Column(Integer, ForeignKey('shows.id')) later
    show_id = Column(Integer)
    # Foreign key to the 'customers' table
    #customer_id = Column(Integer, ForeignKey('customers.id'))later
    customer_id = Column(Integer)

    seats = Column(JSON)

    # Relationships
    show = relationship('Show')
    customer = relationship('Customer')

class BookingResponse(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    
    # Foreign key to the 'booking_requests' table
    booking_request_id = Column(Integer, ForeignKey('booking_requests.id'))
    
    show_name = Column(String)  # Include the show name

    # Relationships
    booking_request = relationship('BookingRequest')
    seats = Column(JSON)
    amount = Column(Integer)
    qr_code_image = Column(String)
    is_paid = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    is_ticket_used = Column(Boolean, default=False)
    datetime = Column(DateTime, default=datetime.utcnow)

class PaymentResponse(Base):
    __tablename__ = 'payment_responses'
    id = Column(Integer, primary_key=True)
    
    # Foreign key to the 'booking_requests' table
    booking_request_id = Column(Integer, ForeignKey('booking_requests.id'))
    
    status = Column(String)
    payment_details = Column(JSON)

    # Relationship
    booking_request = relationship('BookingRequest')

def get_session():
    # Create a session to interact with the database
    Session = sessionmaker(bind=engine)
    session = Session()
    return session
#end of Database



#comment
app = Flask(__name__)
session = get_session()
# Endpoint for creating a new booking
@app.route('/booking', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        booking_request = BookingRequest(**data)
        session.add(booking_request)
        
        session.commit()


        booking_id = booking_request.id

        validate_url = url_for('validate_ticket', bookingId=booking_id, _external=True)#validate heist entwerten
        qr= Helper.generate_qr_code(validate_url)##something needs to be done
        # Save the QR code as an image file (you can customize the filename)
        qr.save('qr_codes/{}.png'.format(booking_id))

        # Or return the QR code image as a response
        img_buffer = BytesIO()
        qr.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return send_file(img_buffer, mimetype='image/png')

    except IntegrityError:
        session.rollback()
        return jsonify({"error": "Bad request"}), 400
    except Exception as e:
        session.rollback()
        return jsonify({"error": "Internal server error"}), 500

# Endpoint for getting booking details by ID
@app.route('/bookings/<int:bookingId>', methods=['GET'])
def get_booking(bookingId):
    booking_response = session.query(BookingResponse).filter_by(bookingId=bookingId).first()
    if booking_response:
        return jsonify({"data": booking_response}), 200
    else:
        return jsonify({"error": "Booking not found"}), 404

# Endpoint for canceling a booking by ID
@app.route('/bookings/<int:bookingId>/cancel', methods=['DELETE'])
def cancel_booking(bookingId):
    booking_response = session.query(BookingResponse).filter_by(bookingId=bookingId).first()
    if booking_response:
        session.delete(booking_response)
        session.commit()
        return '', 204
    else:
        return jsonify({"error": "Booking not found"}), 404

# Endpoint for initiating payment for a booking
@app.route('/bookings/<int:bookingId>/pay', methods=['POST'])
def initiate_payment(bookingId):
    try:
        data = request.get_json()
        payment_response = PaymentResponse(**data)
        session.add(payment_response)
        session.commit()
        return jsonify({"message": "Payment initiated successfully"}), 200
    except IntegrityError:
        session.rollback()
        return jsonify({"error": "Bad request"}), 400
    except Exception as e:
        session.rollback()
        return jsonify({"error": "Internal server error"}), 500
    
# Endpoint for validating a booking by ID
@app.route('/bookings/validate/<int:bookingId>', methods=['POST'])
def validate_ticket(bookingId):
    try:
        booking_response = session.query(BookingResponse).filter_by(bookingId=bookingId).first()
        if not booking_response:
            return jsonify({"error": "Booking does not exist"}), 404

        if booking_response.is_validated:
            return jsonify({"error": "Booking has already been validated"}), 400

        if not booking_response.is_paid:
            return jsonify({"error": "Booking is not paid"}), 400
        
         # Get the current UTC time
        current_utc_time = datetime.utcnow()

        # Calculate the time difference
        time_difference = abs(current_utc_time - booking_response.datetime)

        # Check if the time difference is more than 1 hour (3600 seconds)
        if time_difference > timedelta(hours=1):
            return jsonify({"error": "Wrong time, more than 1 hour off from the ticket"}), 400


        # Perform validation logic here
        # For example, mark the booking as validated
        booking_response.is_ticket_used = True
        session.commit()

        return jsonify({"message": "Booking validated successfully"}), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/helloworld')
def helloworld():
    return("Helloworld form backend booking")


if __name__ == '__main__':
    Base.metadata.create_all(engine)
    app.run(host='0.0.0.0', port=80)
