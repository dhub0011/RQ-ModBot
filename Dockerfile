FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y openjdk-17-jre-headless unzip wget

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN wget -O /app/apktool.jar https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/apktool.jar
RUN wget -O /app/uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.2.1/uber-apk-signer-1.2.1.jar

COPY bot.py .

CMD ["python", "bot.py"]