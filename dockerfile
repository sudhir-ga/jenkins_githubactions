# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the Python script and requirements.txt (if needed)
COPY jenkins_to_github_docker_secrets.py /app/
COPY requirements.txt /app/  # If you have external dependencies

# Install Python dependencies (if applicable)
RUN pip install --no-cache-dir -r requirements.txt

# Run the Python script by default when the container starts
ENTRYPOINT ["python", "jenkins_to_github_docker_secrets.py"]
