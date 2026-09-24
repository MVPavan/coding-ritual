"""Check the real JSON route without contacting any upstream engine."""

import json
from urllib.error import HTTPError
from urllib.request import urlopen


def main() -> None:
    try:
        with urlopen("http://127.0.0.1:8080/search?format=json", timeout=3):
            raise RuntimeError("missing-query request unexpectedly succeeded")
    except HTTPError as error:
        if error.code != 400 or json.load(error) != {"error": "No query"}:
            raise RuntimeError("JSON search route is unavailable or misconfigured") from error


if __name__ == "__main__":
    main()
