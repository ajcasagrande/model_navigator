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
# pytype: disable=import-error

import tempfile
from pathlib import Path

import numpy
import onnx
import torch
from polygraphy.backend.trt import Profile

from model_navigator.__version__ import __version__
from model_navigator.framework_api._nav_package_format_version import NAV_PACKAGE_FORMAT_VERSION
from model_navigator.framework_api.commands.correctness import Correctness
from model_navigator.framework_api.commands.data_dump.samples import (
    DumpInputModelData,
    DumpOutputModelData,
    samples_to_npz,
)
from model_navigator.framework_api.commands.export.pyt import ExportPYT2ONNX, ExportPYT2TorchScript
from model_navigator.framework_api.common import TensorMetadata
from model_navigator.framework_api.package_descriptor import PackageDescriptor
from model_navigator.framework_api.status import ModelStatus, NavigatorStatus
from model_navigator.framework_api.utils import Framework, JitType
from model_navigator.model import Format
from model_navigator.tensor import TensorSpec

# pytype: enable=import-error

VALUE_IN_TENSOR = 9.0
OPSET = 11


dataloader = [torch.full((1, 1), VALUE_IN_TENSOR) for _ in range(10)]


class MyModule(torch.nn.Module):
    def forward(self, x):
        return x + 10


model = MyModule()


def _extract_dumped_samples(filepath: Path):
    dumped_samples = []
    for sample_path in filepath.iterdir():
        sample = {}
        with numpy.load(sample_path.as_posix()) as data:
            for k, v in data.items():
                sample[k] = v
        dumped_samples.append(sample)
    return dumped_samples


def test_pyt_dump_model_input():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        package_dir = workdir / f"{model_name}.nav.workspace"
        model_input_dir = package_dir / "model_input"

        input_data = next(iter(dataloader))
        numpy_data = input_data.cpu().numpy()

        dump_cmd = DumpInputModelData()
        samples = [{"input__1": numpy_data}]

        dump_cmd(
            framework=Framework.PYT,
            workdir=workdir,
            model_name=model_name,
            dataloader=dataloader,
            profiling_sample=samples[0],
            conversion_samples=samples,
            correctness_samples=samples,
            input_metadata={"input__1": TensorSpec("input__1", numpy_data.shape, numpy_data.dtype)},
            output_metadata={"output__1": TensorSpec("output__1", numpy_data.shape, numpy_data.dtype)},
            sample_count=1,
            batch_dim=None,
        )

        for filepath in model_input_dir.iterdir():
            dumped_samples = _extract_dumped_samples(filepath)
            for dumped, reference in zip(dumped_samples, samples):
                for name in reference:
                    assert numpy.allclose(dumped[name], reference[name])


def test_pyt_dump_model_output():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        package_dir = workdir / f"{model_name}.nav.workspace"
        model_dir = package_dir / "torchscript-script"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_input_dir = package_dir / "model_input"
        model_input_dir.mkdir(parents=True, exist_ok=True)
        model_output_dir = package_dir / "model_output"

        input_data = next(iter(dataloader))
        numpy_data = input_data.cpu().numpy()
        model_output = model(*input_data)
        outputs = [{"output__1": model_output}]

        dump_cmd = DumpOutputModelData()
        samples = [{"input__1": numpy_data}]

        dump_cmd(
            framework=Framework.PYT,
            workdir=workdir,
            model=model,
            model_name=model_name,
            dataloader=dataloader,
            profiling_sample=samples[0],
            conversion_samples=samples,
            correctness_samples=samples,
            input_metadata={"input__1": TensorSpec("input__1", numpy_data.shape, numpy_data.dtype)},
            output_metadata={"output__1": TensorSpec("output__1", numpy_data.shape, numpy_data.dtype)},
            sample_count=1,
            target_device="cpu",
            batch_dim=None,
        )

        for filepath in model_output_dir.iterdir():
            dumped_samples = _extract_dumped_samples(filepath)
            for dumped, reference in zip(dumped_samples, outputs):
                for name in reference:
                    assert numpy.allclose(dumped[name], reference[name])


def test_pyt_correctness():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        package_dir = workdir / f"{model_name}.nav.workspace"
        model_dir = package_dir / "torchscript-script"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "model.pt"

        script_module = torch.jit.script(model)
        torch.jit.save(script_module, model_path.as_posix())

        input_data = next(iter(dataloader))
        numpy_input = input_data.numpy()
        numpy_output = model(input_data).detach().cpu().numpy()
        batch_dim = None

        samples_to_npz([{"input__1": numpy_input}], package_dir / "model_input" / "correctness", batch_dim=batch_dim)
        samples_to_npz([{"output__1": numpy_output}], package_dir / "model_output" / "correctness", batch_dim=batch_dim)

        input_metadata = TensorMetadata({"input__1": TensorSpec("input__1", numpy_input.shape, numpy_input.dtype)})
        output_metadata = TensorMetadata({"output__1": TensorSpec("output__1", numpy_output.shape, numpy_output.dtype)})
        nav_status = NavigatorStatus(
            format_version=NAV_PACKAGE_FORMAT_VERSION,
            model_navigator_version=__version__,
            uuid="1",
            git_info={},
            environment={},
            export_config={
                "model_name": model_name,
                "target_device": "cpu",
            },
            model_status=[
                ModelStatus(
                    format=Format.TORCHSCRIPT,
                    path=Path("torchscript-script/model.pt"),
                    runtime_results=[],
                    torch_jit=JitType.SCRIPT,
                )
            ],
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            trt_profile=Profile(),
        )
        pkg_desc = PackageDescriptor(nav_status, workdir)
        pkg_desc.save_status_file()

        correctness_cmd = Correctness(
            name="test correctness",
            target_format=Format.TORCHSCRIPT,
            target_jit_type=JitType.SCRIPT,
        )

        correctness_cmd(
            workdir=workdir,
            model_name=model_name,
            rtol=0.0,
            atol=0.0,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            target_device="cpu",
            batch_dim=batch_dim,
        )


def test_pyt_export_torchscript():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        package_dir = workdir / f"{model_name}.nav.workspace"

        export_cmd = ExportPYT2TorchScript(target_jit_type=JitType.SCRIPT)
        input_data = next(iter(dataloader))
        numpy_data = input_data.cpu().numpy()
        samples_to_npz([{"input__1": numpy_data}], package_dir / "model_input" / "profiling", None)

        exported_model_path = package_dir / export_cmd(
            model=model,
            model_name=model_name,
            workdir=workdir,
            input_metadata={"input__1": TensorSpec("input__1", numpy_data.shape, numpy_data.dtype)},
            target_device="cpu",
        )

        torch.jit.load(exported_model_path.as_posix())


def test_pyt_export_onnx():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        package_dir = workdir / f"{model_name}.nav.workspace"

        device = "cuda" if torch.cuda.is_available() else "cpu"

        dataloader_ = (torch.full((3, 5), VALUE_IN_TENSOR, device=device) for _ in range(10))
        model_ = torch.nn.Linear(5, 7).to(device).eval()

        input_data = next(iter(dataloader_))
        sample = {"input": input_data.detach().cpu().numpy()}
        samples_to_npz([sample], package_dir / "model_input" / "profiling", None)

        export_cmd = ExportPYT2ONNX()
        exported_model_path = package_dir / export_cmd(
            model=model_,
            model_name=model_name,
            workdir=workdir,
            opset=OPSET,
            dynamic_axes={"input": {0: "batch"}},
            input_metadata=TensorMetadata({"input": TensorSpec("input", (-1, 5), numpy.dtype("float32"))}),
            output_metadata=TensorMetadata({"output": TensorSpec("output", (-1, 7), numpy.dtype("float32"))}),
            target_device=device,
        )

        onnx.checker.check_model(exported_model_path.as_posix())
