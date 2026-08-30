#!/bin/sh
# Start as root only long enough to make the mounted data directories
# writable by the unprivileged "podderton" user, then drop to it.
# If the container is already run as a non-root user (docker run --user ...),
# just exec the command and assume the volumes are already writable.
set -e

APP_USER=podderton

if [ "$(id -u)" = "0" ]; then
    for dir in /podcasts /subscriptions /feeds "$PODDERTON_PATH"; do
        [ -z "$dir" ] && continue
        [ "$dir" = "/" ] && continue
        [ -d "$dir" ] || continue
        if [ "$(stat -c '%U' "$dir" 2>/dev/null)" != "$APP_USER" ]; then
            chown -R "$APP_USER:$APP_USER" "$dir" 2>/dev/null || true
        fi
    done
    exec gosu "$APP_USER" "$@"
fi

exec "$@"
