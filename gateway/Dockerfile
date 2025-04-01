
FROM python:3.11-slim

WORKDIR /app
COPY ./gateway ./gateway
COPY ./shared ./shared
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "5000"]
