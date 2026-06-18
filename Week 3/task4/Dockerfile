# Use Python 3.11 lightweight slim runtime image
FROM python:3.11-slim

# Prevent Python from writing .pyc compiles and optimize streaming logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working container directory
WORKDIR /app

# Copy dependency definition file
COPY requirements.txt .

# Install necessary Python packages
RUN pip install --no-cache-dir -r requirements.txt

COPY .env.example .

# Copy all local project source files into the container
COPY . .

# Expose Streamlit dashboard port
EXPOSE 8501

# Streamlit-specific flags for headless execution inside container environment
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
