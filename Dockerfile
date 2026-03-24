FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/

# Default config and podcast paths (mapped via volumes)
ENV PODDERTON_CONFIG=/config/feeds.yaml
ENV PODDERTON_PATH=/podcasts
ENV PYTHONUNBUFFERED=1

EXPOSE 9988

WORKDIR /app/src
CMD ["python", "__main__.py", "/config/feeds.yaml"]
