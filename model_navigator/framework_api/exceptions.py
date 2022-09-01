# Copyright (c) 2021-2022, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import contextlib
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Optional

import fire

from model_navigator.framework_api.logger import LOGGER


class ModelNavigatorExportAPIError(Exception):
    pass


class UserError(ModelNavigatorExportAPIError):
    pass


class ModelNavigatorBackwardCompatibilityError(ModelNavigatorExportAPIError):
    pass


class ExecutionContext(contextlib.AbstractContextManager):
    accepted_types = (int, float, bool, str)

    def __init__(self, scipt_path: Optional[Path] = None, cmd_path: Optional[Path] = None):
        super().__init__()
        self._scipt_path = Path(scipt_path) if scipt_path else scipt_path
        self._cmd_path = Path(cmd_path) if cmd_path else cmd_path
        self._cache = {}
        self._output = None

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None or exc_type == UserError:
            return

        raise UserError(exc_value)

    def execute_local_runtime_script(self, path, func, args):
        shutil.copy(path, self._scipt_path)
        run_cmd = self.execute_cmd(" ".join([sys.executable, self._scipt_path.as_posix()] + args), dry_run=True)
        try:
            fire.Fire(func, args)
        except Exception as e:
            raise UserError(f"Command to reproduce error:\n{run_cmd}") from e

    def execute_external_runtime_script(self, path, args):
        shutil.copy(path, self._scipt_path)
        cmd = [sys.executable, self._scipt_path.as_posix()] + args
        self.execute_cmd(cmd)

    def execute_cmd(self, cmd, dry_run=False):
        LOGGER.info(f"Command: {' '.join(cmd)}")

        if self._cmd_path is None:
            raise ValueError("cmd_path is required when using `execute_cmd` method.")

        with self._cmd_path.open("w") as f:
            f.write(" ".join(cmd))

        run_cmd = [os.environ.get("SHELL", "bash"), self._cmd_path.as_posix()]

        if dry_run:
            return run_cmd

        output = subprocess.run(run_cmd, capture_output=True)

        if len(output.stdout):
            LOGGER.info(f"Command stdout:\n\n{textwrap.indent(output.stdout.decode('utf-8'), '    ')}")
        if len(output.stderr):
            LOGGER.info(f"Command stderr:\n\n{textwrap.indent(output.stderr.decode('utf-8'), '    ')}")
        if output.returncode != 0:
            raise UserError(f"{output.stderr.decode('utf-8')}\nCommand to reproduce error:\n{' '.join(run_cmd)}")


class TensorTypeError(TypeError):
    pass
