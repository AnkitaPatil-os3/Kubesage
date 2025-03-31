# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy only the necessary files from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose FastAPI port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]