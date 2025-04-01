
FROM python:3.11-slim

WORKDIR /app
COPY ./repair_service ./repair_service
COPY ./shared ./shared
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "uvicorn", "repair_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
