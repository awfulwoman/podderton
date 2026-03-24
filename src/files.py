import os
import json

def write_json(data, file_path):
    """Write JSON data to a file."""
    with open(file_path, 'w') as file:
        if json.dump(data, file, indent=4):
            return True
    return None

def write_image(image, file_path):
    """Write an image to a file."""
    with open(file_path, 'wb') as file:
        if file.write(image):
            return True
    return None

def write_dir(directory):
    """Create a directory if it doesn't exist."""
    if os.path.exists(directory):
        return True
    os.makedirs(directory, exist_ok=True)
    return True
    

    