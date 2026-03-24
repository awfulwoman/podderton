FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/

# Default config and podcast paths (mapped via volumes)
ENV PODDERTON_CONFIG=/config/feeds.yaml
ENV PODDERTON_PATH=/podcasts

EXPOSE 9988

CMD ["python", "src/__main__.py", "/config/feeds.yaml"]
