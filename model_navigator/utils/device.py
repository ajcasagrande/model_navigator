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
import ctypes
import logging
import uuid
from ctypes import c_uint8
from typing import Optional, Sequence

from model_navigator.exceptions import ModelNavigatorException

LOGGER = logging.getLogger(__name__)
UUID_SIZE = 16
CUDA_SUCCESS = 0

try:
    cuda = ctypes.cdll.LoadLibrary("libcuda.so")
except OSError as e:
    LOGGER.warning(f"CUDA not available: {e}")
    cuda = None


def _check_ret(err):
    if err != CUDA_SUCCESS:
        err_str = ctypes.c_char_p()
        cuda.cuGetErrorString(err, ctypes.byref(err_str))
        raise ModelNavigatorException(f"CUDA error: {err_str.value}.")


def _get_device_count():
    count = ctypes.c_int()
    _check_ret(cuda.cuDeviceGetCount(ctypes.byref(count)))
    return count.value


def _get_all_gpus():
    if cuda is None:
        return []

    _check_ret(cuda.cuInit(0))
    device_count = _get_device_count()
    dev_uuid = bytearray(UUID_SIZE)
    devices = []
    for device in range(device_count):
        _check_ret(cuda.cuDeviceGetUuid((c_uint8 * UUID_SIZE).from_buffer(dev_uuid), device))
        devices.append(f"GPU-{str(uuid.UUID(bytes=bytes(dev_uuid)))}")
    return devices


def get_gpus(gpus: Optional[Sequence[str]] = None):
    """
    Creates a list of GPU UUIDs corresponding to the GPUs visible to Model Navigator.
    GPU UUIDs are returned as hex-encoded strings prefixed with "GPU-", e.g.:
      "GPU-11111111-1111-1111-1111-111111111111"
    """

    devices = _get_all_gpus()

    requested_gpus = gpus or ("all",)
    if len(requested_gpus) == 1 and requested_gpus[0] == "all":
        requested_gpus = range(len(devices))

    navigator_gpus = []
    for gpu in requested_gpus:
        try:
            device = int(gpu)
            navigator_gpus.append(devices[device])
        except (ValueError, IndexError):
            if gpu not in devices:
                raise ModelNavigatorException(f"GPU {gpu} was not found.")
            navigator_gpus.append(gpu)
    return navigator_gpus