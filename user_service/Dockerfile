
FROM python:3.11-slim

WORKDIR /app
COPY ./user_service ./user_service
COPY ./shared ./shared
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "uvicorn", "user_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
