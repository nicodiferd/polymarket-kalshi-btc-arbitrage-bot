FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .

# Expose port
EXPOSE 8000

# Install deps at runtime and run (avoids build issues in LXC)
CMD pip install --no-cache-dir -r requirements.txt && python api.py
