from eaia.gmail import get_credentials
import argparse

argparse.ArgumentParser()
parser = argparse.ArgumentParser()
parser.add_argument(
    "name",
    type=str,
    default=None,
    help="name to get credentials for",
)
args = parser.parse_args()

get_credentials(args.name, interactive=True)
