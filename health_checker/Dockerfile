# Use the official Python image from the Docker Hub
FROM python:3.9.19-alpine

# Set the working directory in the container
WORKDIR /app

# Install the dependencies
RUN pip install kubernetes psycopg2-binary

# Copy the requirements file into the container
COPY  . .

# Command to run the script
CMD ["python", "get_pods_status.py"]
