# Use a slim, official Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy only requirements first (better Docker layer caching -
# dependencies won't reinstall unless requirements.txt changes)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code
COPY . .

# FastAPI/uvicorn will listen on this port
EXPOSE 8000

# Run the app. main.py lives in the app/ folder, so we
# point uvicorn at "app.main:app" (dotted module path).
# Adjust the variable name if your FastAPI instance isn't called "app".
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]