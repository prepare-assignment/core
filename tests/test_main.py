import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture

from prepare_assignment.core.cli import main
from prepare_assignment.data.constants import LOG_LEVEL_TRACE

test_project_dir = os.path.join(Path(__file__).parent.absolute())


def test_main(monkeypatch: pytest.MonkeyPatch, caplog: LogCaptureFixture):
    monkeypatch.chdir(test_project_dir)
    args = ["prepare_assignment", "-f", "testproject/prepare.yml", "-vvvvv", "-dddd"]
    with patch.object(sys, 'argv', args):
            main()
    assert os.path.isdir("out")
    with open('out.txt', 'rbU') as handle:
        count = sum(1 for _ in handle)
    assert count == 7
