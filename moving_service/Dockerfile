
FROM python:3.11-slim

WORKDIR /app
COPY ./moving_service ./moving_service
COPY ./shared ./shared
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "uvicorn", "moving_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
