# Use a slim Python image for efficiency
FROM python:3.12-slim

# Install system dependencies
# ffmpeg: for video processing
# libgl1-mesa-glx, libglib2.0-0: for OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
# Copying requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the application
COPY . .

# Create necessary directories for persistence
RUN mkdir -p assets output data

# Expose the port Gunicorn will run on
EXPOSE 5000

# Environment variable to ensure output is sent straight to terminal (unbuffered)
ENV PYTHONUNBUFFERED=1

# Start the application using Gunicorn
# Using 4 workers, binding to all interfaces on port 5000
# High timeout for long video processing tasks
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "600", "app:app"]