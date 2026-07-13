FROM python:3.10-slim

WORKDIR /app

# Install Java 21
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    unzip \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download APK tools — USING VERIFIED WORKING SOURCES
# Option 1: Try direct download
RUN wget -O /app/apktool.jar https://github.com/iBotPeaches/Apktool/releases/latest/download/apktool.jar || \
    curl -L -o /app/apktool.jar https://github.com/iBotPeaches/Apktool/releases/latest/download/apktool.jar

# Download uber-apk-signer (this one works)
RUN wget -O /app/uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.2.1/uber-apk-signer-1.2.1.jar

# Copy bot code
COPY bot.py .

CMD ["python", "bot.py"]