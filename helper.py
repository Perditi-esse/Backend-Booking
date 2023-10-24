import qrcode
from fpdf import FPDF
import os

# Function to generate a QR code as an image
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=100,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    return qr_img

# Function to generate a PDF ticket with the QR code
def generate_ticket_pdf(seats, amount, qr_code_image):
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

    qr_code_path = 'qr_code.png'
    qr_code_image.save(qr_code_path)

    pdf.image(qr_code_path, x=10, y=pdf.get_y(), w=40)
    
    pdf_file_path = 'ticket.pdf'
    pdf.output(pdf_file_path)
    os.remove(qr_code_path)
    return pdf_file_path

