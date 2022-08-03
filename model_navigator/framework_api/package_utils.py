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

from packaging import version

try:
    import jax.experimental  # pytype: disable=import-error # noqa: F401

    _JAX_AVILABLE = True
except ModuleNotFoundError:
    _JAX_AVILABLE = False

try:
    import torch  # pytype: disable=import-error # noqa: F401

    _TORCH_AVAILABLE = True
except ModuleNotFoundError:
    _TORCH_AVAILABLE = False

try:
    import tensorflow  # pytype: disable=import-error

    _TF_VERSION = tensorflow.__version__

    if version.parse(_TF_VERSION) < version.parse("2.0.0"):
        _TF_AVAILABLE = False
    else:
        _TF_AVAILABLE = True
except (ModuleNotFoundError, AttributeError):
    _TF_AVAILABLE = False

try:
    import datasets  # pytype: disable=import-error # noqa: F401
    import transformers  # pytype: disable=import-error # noqa: F401

    _HF_AVAILABLE = True
except ModuleNotFoundError:
    _HF_AVAILABLE = False


def is_torch_available() -> bool:
    return _TORCH_AVAILABLE


def is_tf_available() -> bool:
    return _TF_AVAILABLE


def is_hf_available() -> bool:
    return _HF_AVAILABLE


def is_jax_available() -> bool:
    return _JAX_AVILABLE
