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

import time
from collections import OrderedDict
from pathlib import Path
from typing import Mapping

import torch  # pytype: disable=import-error
from polygraphy.backend.base import BaseRunner
from polygraphy.common import TensorMetadata

from model_navigator.framework_api.runners.base import INavigatorRunner
from model_navigator.framework_api.utils import Framework, validate_sample_output
from model_navigator.utils import tensorrt


class PytRunner(INavigatorRunner, BaseRunner):
    """
    Runs inference using PyTorch.
    """

    def __init__(
        self,
        model,
        input_metadata,
        output_names=None,
        target_device="cpu",
        name=None,
        forward_kw_names=None,
        trt_dtype_cast=False,
    ):
        """
        Args:
            model (Union[torch.nn.Module, str, pathlib.Path]):
                    A torch.nn.Module or model path.
            input_metadata (TensorMetadata): Mapping of input names to their data types and shapes.
            output_names (List[str]):
                    A list of output names of the model. This information is used by the
                    Comparator to determine which outputs to compare.


            name (str):
                    The human-readable name prefix to use for this runner.
                    A runner count and timestamp will be appended to this prefix.

            trt_dtype_cast (bool):
                Cast data type is required for Torch-TensorRT
        """
        super().__init__(name=name, prefix="pytorch-runner")
        self._model = model
        self.model = None
        self._target_device = target_device

        self.input_metadata = TensorMetadata()
        for name, spec in input_metadata.items():
            self.input_metadata.add(name, spec.dtype, spec.shape)
        self.output_names = output_names
        self._forward_kw_names = forward_kw_names
        self._trt_dtype_cast = trt_dtype_cast

    def activate_impl(self):
        if isinstance(self._model, (str, Path)):
            self.model = torch.jit.load(str(self._model), map_location=self._target_device).eval()
        else:
            self.model = self._model
            self.model.to(self._target_device).eval()

    def deactivate_impl(self):
        self.model = None

    def get_input_metadata_impl(self):
        return self.input_metadata

    def infer_impl(self, feed_dict):
        start = time.time()
        with torch.no_grad():
            inputs = [
                torch.from_numpy(self._cast_value(val, dtype)).to(self._target_device)
                for (val, (dtype, _)) in zip(feed_dict.values(), self.input_metadata.values())
            ]
            if self._forward_kw_names is None:
                outputs = self.model(*inputs)
            else:
                inputs_dict = dict(zip(self._forward_kw_names, inputs))
                outputs = self.model(**inputs_dict)

        validate_sample_output(outputs, Framework.PYT)
        if torch.is_tensor(outputs):
            outputs = (outputs,)
        if isinstance(outputs, Mapping):
            outputs = outputs.values()

        out_dict = OrderedDict()
        if self.output_names is None:
            self.output_names = [f"output__{i}" for i in range(len(outputs))]
        for name, output in zip(self.output_names, outputs):
            out_dict[name] = output.cpu().numpy()
        end = time.time()
        self.inference_time = end - start
        return out_dict

    def _cast_value(self, value, dtype):
        value = value.astype(dtype)
        value = tensorrt.cast_tensor(value)

        return value
