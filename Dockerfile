FROM python:3.10-slim

WORKDIR /app

# Install Java 21 (available in current Debian repos)
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download APK tools — USING VERIFIED, WORKING URLs
RUN wget -O /app/apktool.jar https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/apktool.jar
RUN wget -O /app/uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.2.1/uber-apk-signer-1.2.1.jar

# Copy bot code
COPY bot.py .

# Run the bot
CMD ["python", "bot.py"]