FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY dashboard ./dashboard

RUN pip install --no-cache-dir -e .

ENV DATABASE_URL=sqlite:////app/data/stochastiq.db

EXPOSE 8000 8501

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
