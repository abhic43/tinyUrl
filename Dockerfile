# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables
ENV DATABASE_URL=${DATABASE_URL}
ENV SHORT_CODE_LENGTH=${SHORT_CODE_LENGTH}
ENV BASE_URL=${BASE_URL}

# Run the application
CMD ["uvicorn", "url_shortener:app", "--host", "0.0.0.0", "--port", "8000"]