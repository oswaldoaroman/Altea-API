import yaml

with open("config.yaml", "r") as archivo:
    config = yaml.safe_load(archivo)

OLLAMA_URL = config["ollama"]["api_url"]
OLLAMA_MODEL = config["ollama"]["model_name"]
