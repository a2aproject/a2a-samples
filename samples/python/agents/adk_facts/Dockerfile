FROM python:3.13-slim

EXPOSE 8080
WORKDIR /app

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["uvicorn", "agent:a2a_app --host 0.0.0.0 --port $PORT"]
