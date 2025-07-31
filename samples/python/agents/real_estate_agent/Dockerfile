# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file to the working directory
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Bundle app source
COPY . .

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Your app binds to port 3001, so expose that
EXPOSE 3001

# Define the command to run your app
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "[::]:3001", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]