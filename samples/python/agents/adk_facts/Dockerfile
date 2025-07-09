FROM python:3.13-slim

EXPOSE 8001
WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["adk", "api_server", "--a2a", "--port 8001", "remote_a2a"]
