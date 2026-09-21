import os
import stat
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.utils.files import remove_tree


def _read_only_tree(root: Path) -> Path:
    tree = root / "tree"
    (tree / "objects").mkdir(parents=True)
    file = tree / "objects" / "pack"
    file.write_text("x")
    # Like git: read-only object files
    os.chmod(file, stat.S_IREAD)
    if sys.platform != "win32":
        # On posix a file can only not be removed if its directory is read-only
        os.chmod(tree / "objects", stat.S_IREAD | stat.S_IEXEC)
    return tree


@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="root can remove read-only files")
def test_remove_read_only_tree(tmp_path: Path) -> None:
    tree = _read_only_tree(tmp_path)
    remove_tree(tree)
    assert not tree.exists()


def test_remove_missing_tree(tmp_path: Path) -> None:
    remove_tree(tmp_path / "missing")


def test_remove_tree_error(tmp_path: Path, mocker: MockerFixture) -> None:
    (tmp_path / "tree").mkdir()
    mocker.patch("prepare_assignment.utils.files.shutil.rmtree", side_effect=PermissionError("locked"))
    with pytest.raises(PermissionError):
        remove_tree(tmp_path / "tree")


def test_remove_tree_ignore_errors(tmp_path: Path, mocker: MockerFixture) -> None:
    (tmp_path / "tree").mkdir()
    mocker.patch("prepare_assignment.utils.files.shutil.rmtree", side_effect=PermissionError("locked"))
    remove_tree(tmp_path / "tree", ignore_errors=True)
