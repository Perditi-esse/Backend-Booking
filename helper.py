import qrcode
from io import BytesIO
from fpdf import FPDF

class Helper:
    @staticmethod
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
        img_buffer = BytesIO()
        qr_img.save(img_buffer, format="PNG")
        return img_buffer.getvalue()

    # Define the TicketPDF class here

    @staticmethod
    def generate_ticket_pdf(seats, amount, qr_code_image, date_time):
        pdf = Helper.TicketPDF()
        pdf.add_page()
        pdf.chapter_title("Ticket Details:")
        pdf.chapter_body(f"Seats: {seats}")
        pdf.chapter_body(f"Amount: {amount}")
        pdf.chapter_body(f"Date and Time: {date_time}")

        try:
            pdf.image(qr_code_image, x=10, y=pdf.get_y(), w=40)
        except Exception as e:
            print(f"Error adding image: {e}")

        pdf_file_path = 'ticket.pdf'
        pdf.output(pdf_file_path)
        return pdf_file_path
