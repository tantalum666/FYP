# /// script
# requires-python = ">=3.11"
# dependencies = ["python-stdnum==2.2"]
# ///
"""Reproduce the checksum result using only Stripe's public Link CLI 1.6.0 README."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.request import urlopen

from stdnum import luhn

SOURCE = "https://raw.githubusercontent.com/stripe/link-cli/06d97214935160aa26c848f090ac0d27eaeb5842/README.md"
SHA256 = "89ee1914f6211ab92823635d7231b9a64defe191e18e4849e1ce1eb1161bdfea"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, help="Read the pinned README offline")
    args = parser.parse_args()
    if args.readme:
        document = args.readme.read_bytes()
    else:
        with urlopen(SOURCE, timeout=15) as response:
            document = response.read()
    if hashlib.sha256(document).hexdigest() != SHA256:
        parser.error("README does not match the pinned release")
    rows = [
        line
        for line in document.decode().splitlines()
        if line.startswith("**Test mode:**") and "testmode SpendRequest" in line
    ]
    examples = re.findall(r"test card `([0-9]{12,19})`", "\n".join(rows))
    if len(examples) != 1:
        parser.error("Expected one example in the tagged test-mode paragraph")
    print(
        json.dumps(
            {
                "link_cli_release": "1.6.0",
                "verified_readme_sha256": SHA256,
                "public_example_length": len(examples[0]),
                "luhn_valid": luhn.is_valid(examples[0]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
