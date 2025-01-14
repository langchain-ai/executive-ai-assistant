from eaia.gmail import get_credentials
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assistant_id",
        type=str,
        default=None,
        help="assistant_id to set up for",
    )
    args = parser.parse_args()
    get_credentials(args.assistant_id)
