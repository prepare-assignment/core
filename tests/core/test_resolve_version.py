from typing import Optional

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.preparer import __resolve_version

URL = "https://github.com/prepare-assignment/remove.git"

# Realistic fake tag output from git ls-remote --tags
TAGS_MULTIVERSION = (
    "abc1230000000000000000000000000000000001\trefs/tags/v1.0.0\n"
    "abc1230000000000000000000000000000000002\trefs/tags/v1.1.0\n"
    "abc1230000000000000000000000000000000003\trefs/tags/v1.1.2\n"
    "abc1230000000000000000000000000000000004\trefs/tags/v2.0.0\n"
    "abc1230000000000000000000000000000000005\trefs/tags/v2.1.0"
)

TAGS_WITH_ANNOTATED = (
    "abc1230000000000000000000000000000000001\trefs/tags/v1.0.0\n"
    "abc1230000000000000000000000000000000002\trefs/tags/v1.0.0^{}\n"
    "abc1230000000000000000000000000000000003\trefs/tags/v1.1.0\n"
    "abc1230000000000000000000000000000000004\trefs/tags/v1.1.0^{}"
)

TAGS_WITH_NONSEMVER = (
    "abc1230000000000000000000000000000000001\trefs/tags/v1.0.0\n"
    "abc1230000000000000000000000000000000002\trefs/tags/nightly\n"
    "abc1230000000000000000000000000000000003\trefs/tags/v2.0.0\n"
    "abc1230000000000000000000000000000000004\trefs/tags/beta-test"
)

TAGS_EMPTY = ""

TAGS_BRANCHES_ONLY = (
    "abc1230000000000000000000000000000000001\trefs/heads/main\n"
    "abc1230000000000000000000000000000000002\trefs/heads/develop"
)


def mock_ls_remote(mocker: MockerFixture, return_value: str) -> None:
    # Git uses __getattr__ for command dispatch, so patch the class at the module level
    # and configure the instance's ls_remote to return the desired string.
    mock_git_cls = mocker.patch("prepare_assignment.core.preparer.Git")
    mock_git_cls.return_value.ls_remote.return_value = return_value


# ── No network call needed ───────────────────────────────────────────────────

def test_main_returns_main() -> None:
    result = __resolve_version(URL, "main")
    assert result == "main"


def test_commit_hash_passthrough() -> None:
    commit = "abc1230000000000000000000000000000000001"
    result = __resolve_version(URL, commit)
    assert result == commit


# ── "latest" resolution ──────────────────────────────────────────────────────

def test_latest_returns_highest_semver(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    assert __resolve_version(URL, "latest") == "v2.1.0"


def test_latest_no_tags_returns_none(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_EMPTY)
    assert __resolve_version(URL, "latest") is None


def test_latest_only_branches_returns_none(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_BRANCHES_ONLY)
    assert __resolve_version(URL, "latest") is None


def test_latest_skips_nonsemver_tags(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_WITH_NONSEMVER)
    assert __resolve_version(URL, "latest") == "v2.0.0"


def test_latest_filters_annotated_tag_entries(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_WITH_ANNOTATED)
    # ^{} entries must be ignored; highest valid tag is v1.1.0
    assert __resolve_version(URL, "latest") == "v1.1.0"


# ── Exact version ────────────────────────────────────────────────────────────

def test_exact_tag_exists(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    assert __resolve_version(URL, "v1.1.0") == "v1.1.0"


def test_exact_tag_not_found_falls_back_to_prefix(mocker: MockerFixture) -> None:
    # "v1.0.0" is not a tag, but "v1.0.0.1" would be a prefix match.
    tags = (
        "abc1230000000000000000000000000000000001\trefs/tags/v1.0.0.1\n"
        "abc1230000000000000000000000000000000002\trefs/tags/v1.0.0.2"
    )
    mock_ls_remote(mocker, tags)
    assert __resolve_version(URL, "v1.0.0") == "v1.0.0.2"


# ── Prefix resolution ────────────────────────────────────────────────────────

def test_prefix_v1_returns_highest_in_v1(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    # v1.0.0, v1.1.0, v1.1.2 all match; v2.x must not be included
    assert __resolve_version(URL, "v1") == "v1.1.2"


def test_prefix_v2_returns_highest_in_v2(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    assert __resolve_version(URL, "v2") == "v2.1.0"


def test_prefix_skips_nonsemver_matches(mocker: MockerFixture) -> None:
    tags = (
        "abc1230000000000000000000000000000000001\trefs/tags/v1.0.0\n"
        "abc1230000000000000000000000000000000002\trefs/tags/v1.invalid\n"
        "abc1230000000000000000000000000000000003\trefs/tags/v1.1.0"
    )
    mock_ls_remote(mocker, tags)
    assert __resolve_version(URL, "v1") == "v1.1.0"


def test_prefix_no_matches_returns_version_as_fallback(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    # "v3" has no matching tags
    assert __resolve_version(URL, "v3") == "v3"


# ── Fallback ─────────────────────────────────────────────────────────────────

def test_unknown_version_returns_as_is(mocker: MockerFixture) -> None:
    mock_ls_remote(mocker, TAGS_MULTIVERSION)
    assert __resolve_version(URL, "develop") == "develop"
