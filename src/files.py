import os
import json

def write_json(data, file_path):
    """Write JSON data to a file. Returns True on success."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    return True

def write_bytes(data, file_path):
    """Write raw bytes to a file. Returns True on success."""
    with open(file_path, 'wb') as file:
        file.write(data)
    return True

def write_dir(directory):
    """Create a directory if it doesn't exist."""
    if os.path.exists(directory):
        return True
    os.makedirs(directory, exist_ok=True)
    return True
