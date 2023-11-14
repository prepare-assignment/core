import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from prepare_assignment.cli.main import app

test_project_dir = os.path.join(Path(__file__).parent.absolute())


def test_main(monkeypatch: pytest.MonkeyPatch, caplog: LogCaptureFixture, mocker: MockerFixture):
    git_mode = os.environ.get("PREPARE_TEST_GIT_MODE", "ssh")
    args = ["prepare_assignment", "run", "-f", "testproject/prepare.yml", "-vvvvv", "-dddd", "--git", git_mode]
    monkeypatch.chdir(test_project_dir)

    with tempfile.TemporaryDirectory() as tmpdir:         
        mocker.patch("prepare_assignment.core.preparer.cache_path", tmpdir)
        with patch.object(sys, 'argv', args):
            with pytest.raises(SystemExit):
                app()
    assert os.path.isdir("out")
    with open('out.txt', 'r') as handle:
        text = handle.read()
    assert "AssessmentResult.java" in text
