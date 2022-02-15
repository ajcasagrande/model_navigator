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
import sys

from click import Context

from model_navigator.log import LOGGER
from model_navigator.results import State, Status


def is_cli_command(ctx: Context) -> bool:
    """
    Check if command is run from CLI

    Args:
        ctx: Click context object

    Returns:
        True if run as CLI command, False otherwise
    """
    return ctx.parent.info_name == "model-navigator"


def exit_cli_command(status: Status) -> None:
    """
    Exit from CLI command with system exit code

    Args:
        status: Command status
    """
    result_status = 1 if status.state == State.FAILED else 0
    if result_status != 0:
        LOGGER.error(status.message)
    sys.exit(result_status)
