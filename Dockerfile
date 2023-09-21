# Use the official Python image as a base image
FROM python:3.8

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python application into the container
COPY . .

# Expose port 5000 for Flask app
EXPOSE 8000

# Define the command to run your Flask app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

