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

from model_navigator.__version__ import __version__  # noqa: F401
from model_navigator.converter.config import TensorRTPrecision  # noqa: F401
from model_navigator.framework_api import commands, config, pipelines  # noqa: F401
from model_navigator.framework_api.constants import NAV_PACKAGE_FORMAT_VERSION  # noqa: F401
from model_navigator.framework_api.commands.performance import MeasurementMode, ProfilerConfig  # noqa: F401
from model_navigator.framework_api.logger import LOGGER  # noqa: F401
from model_navigator.framework_api.package_descriptor import profile, save  # noqa: F401
from model_navigator.framework_api.package_utils import is_jax_available, is_tf_available, is_torch_available
from model_navigator.framework_api.utils import Framework, JitType, RuntimeProvider, Status  # noqa: F401
from model_navigator.model import Format  # noqa: F401
from model_navigator.tensor import TensorSpec  # noqa: F401

if is_torch_available():
    from model_navigator.framework_api import torch  # noqa: F401

if is_tf_available():
    from model_navigator.framework_api import tensorflow  # noqa: F401

if is_tf_available() and is_jax_available():
    from model_navigator.framework_api import jax  # noqa: F401

from model_navigator.framework_api import contrib  # noqa: F401 pylint: disable=wrong-import-position
from model_navigator.framework_api import onnx  # noqa: F401
from model_navigator.framework_api.load import load  # noqa: F401
