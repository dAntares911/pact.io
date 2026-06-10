FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    ruby \
    ruby-dev \
    build-essential \
    && gem install pact-mock_service --no-document \
    && gem install pact_broker-client --no-document \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
