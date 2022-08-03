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

from typing import TYPE_CHECKING, List

from model_navigator.framework_api.commands.core import Command
from model_navigator.framework_api.commands.export.jax import ExportJAX2SavedModel
from model_navigator.framework_api.config import Config
from model_navigator.framework_api.pipelines.pipeline import Pipeline
from model_navigator.framework_api.utils import Framework

if TYPE_CHECKING:
    from model_navigator.framework_api.package_descriptor import PackageDescriptor


def jax_export_builder(config: Config, package_descriptor: "PackageDescriptor") -> Pipeline:
    commands: List[Command] = [ExportJAX2SavedModel()]
    return Pipeline(name="JAX Export", framework=Framework.JAX, commands=commands)
