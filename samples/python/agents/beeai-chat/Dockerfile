FROM python:3.11-slim

EXPOSE 9999
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY . ./

CMD ["python", "__main__.py"]
