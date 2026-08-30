from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAG_PATTERN = re.compile(
    r"^v(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
)


def project_version(pyproject_path: Path = ROOT / "pyproject.toml") -> str:
    with pyproject_path.open("rb") as project_file:
        project = tomllib.load(project_file)
    return str(project["project"]["version"])


def validate_release_tag(tag: str, version: str) -> None:
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(f"Release tag must use vMAJOR.MINOR.PATCH format: {tag}")
    if match.group("version") != version:
        raise ValueError(
            f"Release tag {tag} does not match pyproject.toml version v{version}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the SmurfPanel release tag")
    parser.add_argument("tag", help="release tag, for example v1.0.0")
    args = parser.parse_args()

    version = project_version()
    try:
        validate_release_tag(args.tag, version)
    except ValueError as error:
        parser.error(str(error))
    print(f"Release tag {args.tag} matches package version {version}.")


if __name__ == "__main__":
    main()
