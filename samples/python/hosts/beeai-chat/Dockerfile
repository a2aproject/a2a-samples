FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install .
COPY . ./

CMD ["python", "__main__.py"]
