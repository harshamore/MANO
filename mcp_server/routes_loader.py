import os, yaml

def load_routes():
    # Load from config/ed_routes.yaml
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "ed_routes.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
