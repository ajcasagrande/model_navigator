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
from typing import Generator

from model_navigator.converter import ConversionConfig
from model_navigator.converter.config import TargetFormatConfigSetIterator, TensorRTPrecisionMode
from model_navigator.exceptions import ModelNavigatorException


class TensorRTConfigSetIterator(TargetFormatConfigSetIterator):
    def __iter__(self):
        for onnx_opset in self._conversion_set_config.onnx_opsets:
            for tensorrt_precision, tensorrt_precision_mode in self._precision_modes():
                yield ConversionConfig(
                    target_format=self._target_format,
                    onnx_opset=onnx_opset,
                    tensorrt_precision=tensorrt_precision,
                    tensorrt_precision_mode=tensorrt_precision_mode,
                    tensorrt_explicit_precision=self._conversion_set_config.tensorrt_explicit_precision,
                    tensorrt_sparse_weights=self._conversion_set_config.tensorrt_sparse_weights,
                    tensorrt_strict_types=self._conversion_set_config.tensorrt_strict_types,
                )

    def _precision_modes(self) -> Generator:
        """
        Generate all possible precision modes based on provided strategy
        """
        tensorrt_precisions = self._conversion_set_config.tensorrt_precisions
        tensorrt_precisions_mode = self._conversion_set_config.tensorrt_precisions_mode

        if tensorrt_precisions_mode == TensorRTPrecisionMode.HIERARCHY:
            for tensorrt_precision in tensorrt_precisions:
                yield tensorrt_precision, tensorrt_precisions_mode
        elif tensorrt_precisions_mode == TensorRTPrecisionMode.SINGLE:
            for tensorrt_precision in tensorrt_precisions:
                yield tensorrt_precision, tensorrt_precisions_mode
        elif tensorrt_precisions_mode == TensorRTPrecisionMode.MIXED:
            for precision_mode in [TensorRTPrecisionMode.HIERARCHY, TensorRTPrecisionMode.SINGLE]:
                for tensorrt_precision in tensorrt_precisions:
                    yield tensorrt_precision, precision_mode
        else:
            raise ModelNavigatorException(f"Unsupported TensorRT target precision mode: {tensorrt_precisions_mode}")
