# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the required dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port on which the Flask app will run
EXPOSE 8000

# Set the environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the Flask application
CMD ["flask", "run", "--port=8000", "--host=0.0.0.0"]
