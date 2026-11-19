FROM python:3.11-slim

WORKDIR /app
# Keep dependency installation before application code so Python-only edits reuse this layer.
COPY requirements.txt ./
# --no-cache-dir disables pip downloads cache, not Docker layer caching.
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
