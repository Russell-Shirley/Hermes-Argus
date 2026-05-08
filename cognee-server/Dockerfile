FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git for pip git+https installs)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY . .

EXPOSE 8000

# Use entrypoint to symlink Cognee data to persistent volume
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
