from langsmith import Client
import re
import argparse
import json

def format_assertion_error(error_string):
    """
    Parses an assertion error string to extract expected and actual values and 
    formats them into a user-friendly message.

    Args:
        error_string: A string containing an assertion error message
          in the format of an AssertionError with diff details.

    Returns:
        A formatted string message like:
        "This email was supposed to be categorized as `email` but the AI thought it should categorize it as `no`",
        or None if it can't parse the error string
    """
    match = re.search(r"assert '(.*?)' == '(.*?)'", error_string)
    if match:
        actual, expected = match.groups()
        return f"This email was supposed to be categorized as `{expected}` but the AI thought it should categorize it as `{actual}`"
    else:
      return None # handle case where error format isn't as expected

def main(experiment_name: str):
    client = Client()
    
    experiment_runs = [r for r in client.list_runs(project_name=experiment_name, is_root=True)]
    errored_runs = [r for r in experiment_runs if r.error]

    errored_pairs = [(r.inputs, r.error) for r in errored_runs]

    formatted_errors = []
    for inputs, error in errored_pairs:
        formatted_error = format_assertion_error(error)
        if formatted_error:
            formatted_errors.append({**inputs, "formatted_error": formatted_error})

    # Load existing errors if file exists
    try:
        with open("few_shot_emails.json", "r") as f:
            existing_errors = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_errors = []

    # Add new errors, avoiding duplicates
    existing_errors.extend([error for error in formatted_errors if error not in existing_errors])

    # Write back all errors
    with open("few_shot_emails.json", "w") as f:
        json.dump(existing_errors, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="The name of the experiment to run.",
    )
    args = parser.parse_args()
    main(experiment_name=args.experiment_name)