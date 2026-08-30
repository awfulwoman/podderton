FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 podderton \
    && useradd --uid 1000 --gid podderton --home-dir /app --shell /usr/sbin/nologin podderton

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default config and podcast paths (mapped via volumes)
ENV PODDERTON_CONFIG=/config/feeds.yaml
ENV PODDERTON_PATH=/podcasts
ENV PYTHONUNBUFFERED=1

EXPOSE 9988

WORKDIR /app/src
# The entrypoint fixes volume ownership then drops to the unprivileged
# "podderton" user; the app process never runs as root.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-c", "print('Usage: specify run_subscriber.py or run_generator.py as command')"]
