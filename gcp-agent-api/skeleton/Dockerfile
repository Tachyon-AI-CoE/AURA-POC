# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install any needed packages specified in pyproject.toml
RUN uv pip install --system --no-cache --requirement pyproject.toml

# Copy the rest of your application code into the container
COPY . .

# Expose the port your application listens on 
EXPOSE 8080

# Command to run the application with Uvicorn
CMD ["uvicorn", "--app-dir", "./src" , "main_fastapi:app", "--host", "0.0.0.0", "--port", "8080"]