FROM python:3.10-slim

WORKDIR /app

# Install Java 21
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy JAR files from your repo root (matching your filenames)
COPY apktool_3.0.2.jar /app/apktool.jar
COPY uber-apk-signer-1.2.1.jar /app/uber-apk-signer.jar

# Copy bot code
COPY bot.py .

# Run the bot
CMD ["python", "bot.py"]