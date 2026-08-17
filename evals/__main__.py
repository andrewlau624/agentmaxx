"""CLI: python3 -m evals CONTROL_GLOB TREATMENT_GLOB

Run from the repository root. Point each glob at the transcript file(s)
for one arm of an A/B run.
"""

import argparse
import glob
import json
from pathlib import Path

from evals.compare import compare_arms


def _resolve(pattern: str) -> list[Path]:
    return [Path(match) for match in sorted(glob.glob(pattern))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", help="glob matching control transcripts")
    parser.add_argument("treatment", help="glob matching treatment transcripts")

    args = parser.parse_args()

    control = _resolve(args.control)
    treatment = _resolve(args.treatment)

    if not control:
        parser.error(f"no files matched control glob: {args.control}")

    if not treatment:
        parser.error(f"no files matched treatment glob: {args.treatment}")

    print(json.dumps(compare_arms(control, treatment), indent=2))


if __name__ == "__main__":
    main()
