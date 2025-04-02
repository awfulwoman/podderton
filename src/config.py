import yaml
import os

def file(file_path):
    """Read a YAML file and return its contents."""
    # Use PyYAML or another library to read the YAML file
    # For example, you could use PyYAML's load function
    with open(file_path, "r") as file:
        return yaml.safe_load(file)
    
def basepath(configuration):
    """Get the base path from the configuration."""
    
    if not configuration["path"]:
        raise Exception("No valid path defined for storing downloaded assets.")

    base_path = configuration["path"]
    base_path = os.path.expanduser(base_path)

    return base_path