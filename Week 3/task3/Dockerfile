# Use a clean, lightweight Python base image
FROM python:3.11-slim

# Set environment variables to optimize Python runtime in Docker container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy dependency definition file
COPY requirements.txt .

# Install necessary pip packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all local project source files into the container working directory
COPY . .

# Expose Streamlit's default port 8501 to host machine
EXPOSE 8501

# Streamlit-specific flags for headless, unbuffered execution inside a container
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
