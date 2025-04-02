import yaml

def read_yaml(file_path):
    """Read a YAML file and return its contents."""
    # Use PyYAML or another library to read the YAML file
    # For example, you could use PyYAML's load function
    with open(file_path, "r") as file:
        return yaml.safe_load(file)
    

if __name__ == "__main__":
    main()