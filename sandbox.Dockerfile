FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY sandbox/requirements.txt .
RUN pip install -r requirements.txt

# Copy the agent harness
COPY sandbox/main.py .

# Run the harness
CMD ["python", "main.py"]
