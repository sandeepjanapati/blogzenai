# Use the official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application using uvicorn
# The host must be 0.0.0.0 to be accessible from outside the container
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]