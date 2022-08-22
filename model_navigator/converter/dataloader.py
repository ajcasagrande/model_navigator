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
import itertools
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import numpy as np

from model_navigator.converter import DatasetProfileConfig
from model_navigator.converter.utils import navigator_subprocess
from model_navigator.exceptions import ModelNavigatorException
from model_navigator.model import Format, Model, ModelConfig, ModelSignatureConfig
from model_navigator.tensor import TensorSpec
from model_navigator.utils.nav_package import NavPackage

LOGGER = logging.getLogger(__name__)


class Dataloader(ABC):
    @abstractmethod
    def __iter__(self) -> Iterator[Dict[str, np.ndarray]]:
        ...

    def __call__(self) -> Iterator[Dict[str, np.ndarray]]:
        yield from self.__iter__()

    @property
    @abstractmethod
    def opt_shapes(self) -> Dict[str, List[int]]:
        ...

    @property
    @abstractmethod
    def min_shapes(self) -> Dict[str, List[int]]:
        ...

    @property
    @abstractmethod
    def max_shapes(self) -> Dict[str, List[int]]:
        ...

    @property
    @abstractmethod
    def dtypes(self) -> Dict[str, List[np.dtype]]:
        ...


def _generate_random(dtype, shapes, value_range, rng) -> Iterable[Tuple]:
    if dtype.kind == "i":
        return rng.integers(value_range[0], value_range[1], size=shapes, dtype=dtype.type)
    elif dtype.kind == "f":
        return np.array(
            rng.standard_normal(size=shapes) * (value_range[1] - value_range[0]) + value_range[0],
            dtype=dtype.type,
        )
    else:
        raise ModelNavigatorException(f"Don't know how to generate random tensor for dtype={dtype}")


def extract_model_signature(model_config: ModelConfig):
    model = Model(model_config.model_name, model_config.model_path, explicit_format=model_config.model_format)

    # PyTorch and ONNX models are available with input model
    if model.has_signature():
        return model.signature

    # Obtain signature for TF-SavedModel only when the input model has correct format
    if model_config.model_format == Format.TF_SAVEDMODEL:
        # Run in a separate process to avoid problems with global resource management
        with navigator_subprocess() as navigator:
            module = navigator.module("model_navigator.converter.tf.utils")
            return module.get_tf_signature(model_config.model_path)


def _check_dynamic_dims(shape, inp):
    for x in shape:
        if x == -1:
            raise ModelNavigatorException(
                "Cannot construct default dataset profile: "
                f"too many dynamic axes in the model input {inp.name}: {list(inp.shape)}. "
                "Please provide a full dataset profile instead of max_batch_size."
            )


def _shapes_from_signature(model_signature, max_batch_size):
    min_shapes = {}
    for name, inp in model_signature.inputs.items():
        min_shape = list(inp.shape)
        min_shape[0] = 1
        _check_dynamic_dims(min_shape, inp)
        min_shapes[name] = min_shape

    max_shapes = {}
    for name, inp in model_signature.inputs.items():
        max_shape = list(inp.shape)
        max_shape[0] = max_batch_size
        _check_dynamic_dims(max_shape, inp)
        max_shapes[name] = max_shape
    return min_shapes, max_shapes


class RandomDataloader(Dataloader):
    """Generate synthetic data based on DatasetProfileConfig or model's input signature.

    Args:
        dataset_profile (DatasetProfileConfig): Specification of possible input sizes, types and values.
            This is the basic information that is needed for generating data.
            It is optional and if not provided, the information about inputs is taken from
            input signature is extracted either from `model_signature_config` or
            from the model described by `model_config` and from max_batch_size.
        model_signature_config: Optional. Specification of model inputs.
        model_config (ModelConfig): Optional. If neither `dataset_profile` nor `model_signature_config`
            is not provided, then this should at least contain the path to the model file.
        max_batch_size: Upper limit for generated batch sizes. If `dataset_profile` is provided,
            the value is ignored, unless `enforce_max_batch_size` is set to True.
        enforce_max_batch_size:
            Override batch size range specified in `dataset_profile` to (1, `max_batch_size`),
            if both those args are provided. This exists only to facilitate
            compatibility with previous Model Navigator releases and should be deprecated
            and removed in the future.
    """

    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        model_signature_config: Optional[ModelSignatureConfig] = None,
        dataset_profile_config: Optional[DatasetProfileConfig] = None,
        max_batch_size: Optional[int] = None,
        enforce_max_batch_size: bool = False,
        random_seed: int = 0,
    ):
        self.dataset_profile_config = dataset_profile_config or DatasetProfileConfig()
        self.model_signature_config = model_signature_config or ModelSignatureConfig()
        self.rng = np.random.default_rng(random_seed)
        if not self._dataset_profile_complete():
            LOGGER.debug("Dataset profile incomplete, reconstructing from model signature.")
            self._generate_default_profile(model_config, model_signature_config, max_batch_size)
        assert self.dataset_profile_config.max_shapes.keys() == self.dataset_profile_config.min_shapes.keys()
        if enforce_max_batch_size:
            assert max_batch_size is not None
            self._ensure_max_batch_size(max_batch_size)

    def _dataset_profile_complete(self):
        return None not in (
            self.dataset_profile_config.min_shapes,
            self.dataset_profile_config.max_shapes,
            self.dataset_profile_config.dtypes,
            self.dataset_profile_config.value_ranges,
        )

    def _ensure_max_batch_size(self, max_batch_size):
        if not max_batch_size:
            return
        for inp in self.dataset_profile_config.max_shapes:
            self.dataset_profile_config.max_shapes[inp] = (
                max_batch_size,
                *self.dataset_profile_config.max_shapes[inp][1:],
            )
            self.dataset_profile_config.opt_shapes[inp] = (
                min(self.dataset_profile_config.opt_shapes[inp][0], max_batch_size),
                *self.dataset_profile_config.opt_shapes[inp][1:],
            )
            self.dataset_profile_config.min_shapes[inp] = (1, *self.dataset_profile_config.min_shapes[inp][1:])

    def _generate_default_profile(self, model_config, model_signature, max_batch_size):
        if model_config is None and (model_signature is None or model_signature.is_missing()):
            raise ModelNavigatorException("Cannot reconstruct input signatures.")

        if model_signature is None or model_signature.is_missing():
            model_signature = extract_model_signature(model_config.model_path)

        if model_signature is None or model_signature.is_missing():
            raise ModelNavigatorException("Extracted input signatures is missing.")

        # dtypes are almost always missing, so do those first
        if self.dataset_profile_config.dtypes is None:
            dtypes = {}
            for name, inp in model_signature.inputs.items():
                dtypes[name] = inp.dtype
            self.dataset_profile_config.dtypes = dtypes
            LOGGER.debug("Generated default dataset profile. dtypes=%s.", dtypes)

        if self.dataset_profile_config.value_ranges is None:

            def _get_default_value_range(spec: TensorSpec):
                return {"i": (0, 1), "f": (0.0, 1.0)}[spec.dtype.kind]

            value_ranges = {name: _get_default_value_range(spec) for name, spec in model_signature.inputs.items()}
            self.dataset_profile_config.value_ranges = value_ranges
            LOGGER.debug(
                "Missing model input value ranges required during conversion. "
                "Use `value_ranges` config to define missing dataset profiles. "
                f"Used default values_ranges: {value_ranges}"
            )

        try:
            sig_min_shapes, sig_max_shapes = _shapes_from_signature(model_signature, max_batch_size)
        except ModelNavigatorException:
            # it is possible that min_shapes and max_shapes are already there
            if self._dataset_profile_complete():
                return
            raise

        if self.dataset_profile_config.min_shapes is None:
            self.dataset_profile_config.min_shapes = sig_min_shapes
            LOGGER.debug("Generated default dataset profile: min_shapes=%s.", sig_min_shapes)
        if self.dataset_profile_config.max_shapes is None:
            if not max_batch_size:
                raise ModelNavigatorException("Cannot construct default dataset profile: max_batch_size not provided")
            if max_batch_size < 0:
                raise ModelNavigatorException("Cannot construct default dataset profile: max_batch_size negative")

            self.dataset_profile_config.max_shapes = sig_max_shapes
            LOGGER.debug("Generated default dataset profile: max_shapes=%s.", sig_max_shapes)

    @property
    def min_shapes(self) -> Dict[str, Iterable[int]]:
        return self.dataset_profile_config.min_shapes

    @property
    def max_shapes(self) -> Dict[str, Iterable[int]]:
        return self.dataset_profile_config.max_shapes

    @property
    def opt_shapes(self) -> Dict[str, Iterable[int]]:
        if self.dataset_profile_config.opt_shapes is None:
            LOGGER.info("opt_shapes not provided, using opt_shapes=max_shapes")
            self.dataset_profile_config.opt_shapes = self.dataset_profile_config.max_shapes
        return self.dataset_profile_config.opt_shapes

    @property
    def dtypes(self) -> Dict[str, List[np.dtype]]:
        def _extract_type(dtype, name):
            if not self.model_signature_config or not self.model_signature_config.inputs:
                return dtype.type

            tensor_spec = self.model_signature_config.inputs.get(name)
            if not tensor_spec:
                LOGGER.debug(f"Input {name} not found in signature.")
                return dtype.type

            return tensor_spec.dtype.type

        return {k: _extract_type(t, k) for k, t in self.dataset_profile_config.dtypes.items()}

    def __iter__(self) -> Iterator[Dict[str, np.ndarray]]:
        def _extract_dtype(dtype, name):
            if not self.model_signature_config or not self.model_signature_config.inputs:
                return dtype

            tensor_spec = self.model_signature_config.inputs.get(name)
            if not tensor_spec:
                LOGGER.debug(f"Input {name} not found in signature.")
                return dtype

            return tensor_spec.dtype

        yield from (
            {
                name: _generate_random(
                    _extract_dtype(dtype, name),
                    shapes[name],
                    self.dataset_profile_config.value_ranges[name],
                    rng=self.rng,
                )
                for name, dtype in self.dataset_profile_config.dtypes.items()
            }
            for shapes in (self.dataset_profile_config.min_shapes, self.dataset_profile_config.max_shapes)
        )


class NavPackageDataloader(Dataloader):
    """Dataloader for reading inputs dumped in .nav packages
    It generates batches of size 1 and max_batch_size.
    """

    def __init__(
        self,
        package: NavPackage,
        dataset: str,
        max_batch_size: int = 0,
        model_signature_config: Optional[ModelSignatureConfig] = None,
    ):
        LOGGER.debug("Creating dataloader from package %s", package.path)
        if max_batch_size == 0:
            raise ModelNavigatorException("Please provide the --max-batch-size option")
        if max_batch_size < 0:
            raise ModelNavigatorException(f"Provided max_batch_size={max_batch_size} is negative")

        self.package = package
        self.dataset = dataset
        self.max_batch_size = max_batch_size
        self.model_signature_config = model_signature_config
        self.size_index = None
        if dataset not in package.datasets:
            raise ModelNavigatorException(f"Dataset {dataset} not found in {package}")
        self._index_by_shape()

    def __iter__(self) -> Iterator[Dict[str, np.ndarray]]:
        """Make batches from samples of the same size.
        Produces batches of sizes 1 and max_batch_size,
        repeatedly reusing samples from the package if needed to make a full batch."""
        for batch_size in {1, self.max_batch_size}:
            for inputs, files in self.size_index.items():
                count = len(files)
                samples = []
                for i, file in enumerate(itertools.cycle(files)):
                    if i > 0 and i % batch_size == 0:
                        yield self._stack_batch(inputs, samples)
                        if i >= count:
                            break
                        samples = []
                    with self.package.open(file) as fobj:
                        samples.append(dict(np.load(fobj)))

    @property
    @lru_cache
    def min_shapes(self) -> Dict[str, List[int]]:
        shape = {}
        for sample in self:
            for inp, val in sample.items():
                if not shape.get(inp):
                    shape[inp] = list(val.shape)
                assert len(shape[inp]) == len(val.shape)
                for i, (s1, s2) in enumerate(zip(shape[inp], val.shape)):
                    shape[inp][i] = min(s1, s2)
        return shape

    @property
    @lru_cache
    def max_shapes(self) -> Dict[str, List[int]]:
        shape = {}
        for sample in self:
            for inp, val in sample.items():
                if not shape.get(inp):
                    shape[inp] = list(val.shape)
                assert len(shape[inp]) == len(val.shape)
                for i, (s1, s2) in enumerate(zip(shape[inp], val.shape)):
                    shape[inp][i] = max(s1, s2)
        return shape

    @property
    def opt_shapes(self) -> Dict[str, List[int]]:
        return self.max_shapes

    @property
    def dtypes(self) -> Dict[str, List[np.dtype]]:
        dtypes = {}
        for sample in self:
            for inp, val in sample.items():
                dtypes[inp] = self._extract_dtype(val, inp)

            break

        return dtypes

    def _index_by_shape(self):
        """Group samples by shapes, so that batches can be made when iterating"""
        self.size_index = defaultdict(list)
        for file in self.package.datasets[self.dataset]:
            with self.package.open(file) as fobj:
                sample = dict(np.load(fobj))
                key = frozenset((k, v.shape) for k, v in sample.items())
                self.size_index[key].append(file)

    def _format_sample(self, sample, name):
        if not self.model_signature_config or not self.model_signature_config.inputs:
            LOGGER.debug("No signature. No cast.")
            return sample[name]

        input_sample = sample[name]
        tensor_spec = self.model_signature_config.inputs.get(name)
        if not tensor_spec:
            LOGGER.debug(f"Input {name} not found in signature")
            return input_sample

        if tensor_spec.dtype != input_sample.dtype:
            LOGGER.debug(f"Casting input {name} to {tensor_spec.dtype}")
            input_sample = input_sample.astype(tensor_spec.dtype)

        return input_sample

    def _stack_batch(self, inputs, samples):
        batch = {}
        for name, _ in inputs:
            batch[name] = np.stack(self._format_sample(s, name) for s in samples)
        return batch

    def _extract_dtype(self, val, name):
        if not self.model_signature_config or not self.model_signature_config.inputs:
            return val.dtype.type

        tensor_spec = self.model_signature_config.inputs.get(name)
        if not tensor_spec:
            LOGGER.debug(f"Input {name} not found in signature.")
            return val.dtype.type

        return tensor_spec.dtype.type
