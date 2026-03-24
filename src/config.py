import yaml
import os

DEFAULT_CONFIG = {
    "path": "/podcasts",
    "subscribe": {"feeds": []},
    "generate": {"type": "separate"},
}

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
