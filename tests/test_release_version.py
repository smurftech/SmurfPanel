from pathlib import Path

import pytest

from scripts.check_release_version import project_version, validate_release_tag


def test_project_version_reads_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "2.3.4"\n', encoding="utf-8")

    assert project_version(pyproject) == "2.3.4"


def test_release_tag_must_match_project_version() -> None:
    validate_release_tag("v0.1.0", "0.1.0")

    with pytest.raises(ValueError, match="does not match"):
        validate_release_tag("v0.1.1", "0.1.0")


@pytest.mark.parametrize("tag", ["0.1.0", "v1.2", "v01.2.3", "release-1.2.3"])
def test_release_tag_requires_strict_semver(tag: str) -> None:
    with pytest.raises(ValueError, match="vMAJOR.MINOR.PATCH"):
        validate_release_tag(tag, "0.1.0")
