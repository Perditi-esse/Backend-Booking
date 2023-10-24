import qrcode
from fpdf import FPDF
import os

# Function to generate a QR code as an image
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    return qr_img

# Function to generate a PDF ticket with the QR code
def generate_ticket_pdf(seats, amount, qr_code_image, date_time):
    class TicketPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'Ticket', align='C', ln=True)

        def chapter_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, ln=True, align='L')

        def chapter_body(self, body):
            self.set_font('Arial', '', 12)
            self.multi_cell(0, 10, body)
            self.ln()

    pdf = TicketPDF()
    pdf.add_page()
    pdf.chapter_title("Ticket Details:")
    pdf.chapter_body(f"Seats: {seats}")
    pdf.chapter_body(f"Amount: {amount}")
    pdf.chapter_body(f"Date and Time: {date_time}")

    qr_code_path = 'qr_code.png'
    qr_code_image.save(qr_code_path)

    pdf.image(qr_code_path, x=10, y=pdf.get_y(), w=40)
    
    pdf_file_path = 'ticket.pdf'
    pdf.output(pdf_file_path)
    os.remove(qr_code_path)
    return pdf_file_path

# Example usage:
data = "Sample QR Code Data"
qr_code_image = generate_qr_code(data)
generate_ticket_pdf("A1, A2", "$50", qr_code_image, "2023-09-21 15:00")


#generate datasrtucture for the cinemahall and the seats
#matrix of seats
def SeatStringToVector(seats):
    seatVector = []
    for seat in seats.split(","):
        seatVector.append(seat)
        #seat will be called something like A2 or B3
        #turn to numeric value
        #dictionary
        dict={"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"G":6}
        seatVector.append(dict[seat[0]])
        seatVector.append(int(seat[1]))
    return seatVector

def SeatVectorToString(seatVector):
    #use dict
    dict={"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"G":6}
    seatString = ""
    for i in range(0,len(seatVector),3):
        seatString+=dict[seatVector[i+1]]+seatVector[i+2]+","
    return seatString[:-1]

def SeperateSeats(seats):
    seatList = []
    for seat in seats.split(","):
        seatList.append(seat)
    return seatList
def seatmatrix(seats):
    seatMatrix = [[0 for i in range(7)] for j in range(10)]
    for seat in seats:
        seatMatrix[seat[1]][seat[2]]=1
    return seatMatrix
def flatten_list(nested_list):
    """ Flattens a list of lists into a single list. """
    flat_list = []
    for element in nested_list:
        if isinstance(element, list):
            # If the element is a list, extend the result with a flattened version of this element
            flat_list.extend(flatten_list(element))
        else:
            # If the element is not a list, just append it to the result list
            flat_list.append(element)
    return flat_list