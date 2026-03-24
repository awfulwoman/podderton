import yaml
import os
import re

DEFAULT_CONFIG = {
    "path": "/podcasts",
    "subscribe": {"feeds": [], "interval": "30m"},
    "generate": {"type": "separate", "interval": "5m"},
}

def _parse_interval(value):
    """Convert interval string like '30m', '1h', '60s', '2h30m' to integer seconds."""
    if isinstance(value, int):
        return value
    value = str(value).strip()
    if re.fullmatch(r'\d+', value):
        return int(value)
    total = 0
    for match in re.finditer(r'(\d+)([hms])', value):
        num, unit = int(match.group(1)), match.group(2)
        if unit == 'h':
            total += num * 3600
        elif unit == 'm':
            total += num * 60
        elif unit == 's':
            total += num
    return total

def subscribe_interval(configuration):
    """Return subscribe interval in seconds. YAML > env var > default."""
    val = (configuration or {}).get("subscribe", {}).get("interval")
    if val:
        return _parse_interval(val)
    env = os.environ.get("PODDERTON_SUBSCRIBE_INTERVAL")
    if env:
        return _parse_interval(env)
    return 1800

def generate_interval(configuration):
    """Return generate interval in seconds. YAML > env var > default."""
    val = (configuration or {}).get("generate", {}).get("interval")
    if val:
        return _parse_interval(val)
    env = os.environ.get("PODDERTON_GENERATE_INTERVAL")
    if env:
        return _parse_interval(env)
    return 300

def file(file_path):
    """Read a YAML file and return its contents. Create default if missing."""
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
        return DEFAULT_CONFIG.copy()

    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def basepath(configuration):
    """Get the base path from the configuration."""
    path = configuration.get("path") if configuration else None

    if not path:
        path = "/podcasts"

    base_path = os.path.expanduser(path)
    return base_path

def subscriptions_path(configuration):
    """Get the path for subscribed feed data."""
    return os.path.join(basepath(configuration), "subscriptions")

def feeds_path(configuration):
    """Get the path for generated feed XML files."""
    return os.path.join(basepath(configuration), "feeds")
