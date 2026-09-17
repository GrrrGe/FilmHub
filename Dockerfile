FROM python:3.11-slim
# faiss-cpu needs OpenMP at runtime; slim images don't ship it.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py app.py ./
COPY rag/ ./rag/
COPY storage/ ./storage/
COPY manager_agent/ ./manager_agent/
COPY tools/ ./tools/
COPY callbacks/ ./callbacks/
COPY data/imdb_cleaned.csv ./data/imdb_cleaned.csv
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
