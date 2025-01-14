from pathlib import Path

_ROOT = Path(__file__).absolute().parent


def get_config(config: dict):
    # This loads things from the configurable dict
    if "email" in config["configurable"]:
        return config["configurable"]
    else:
        raise ValueError("No email configuration found configurable")
