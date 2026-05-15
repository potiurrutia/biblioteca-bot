FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && \
    curl -sLO https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    apt-get install -y unzip && \
    unzip -q rclone-current-linux-amd64.zip && \
    mv rclone-*-linux-amd64/rclone /usr/local/bin/ && \
    rm -rf rclone-current-linux-amd64.zip rclone-*-linux-amd64 && \
    apt-get remove -y curl unzip && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py start.sh libros.json ./
RUN chmod +x start.sh

CMD ["./start.sh"]
