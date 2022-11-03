<!--
Copyright (c) 2021-2022, NVIDIA CORPORATION. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Triton Model Configurator

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Overview](#overview)
- [The `triton-config-model` Command](#the-triton-config-model-command)
- [CLI and YAML Config Options](#cli-and-yaml-config-options)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

The model configurator command allows generating Triton configuration for passed model and given arguments.

Read more about Triton [model configuration](https://github.com/triton-inference-server/server/blob/master/docs/model_configuration.md)
and [framework-specific optimizations](https://github.com/triton-inference-server/server/blob/master/docs/optimization.md#framework-specific-optimization)
to understand the process of configuring models for Triton deployment.

## The `triton-config-model` Command

Using CLI arguments:

```shell
$ model-navigator triton-config-model --model-name add_sub \
    --model-path model_navigator/examples/quick-start/model.pt \
    --model-repository {path/to/triton/model/repository} \
    --inputs INPUT__0:-1,16:float32 INPUT__1:-1,16:float32 \
    --outputs OUTPUT__0:-1,16:float32 OUTPUT__1:-1,16:float32
```

Using YAML file:

```yaml
model_name: add_sub
model_path: model_navigator/examples/quick-start/model.pt
model_repository: { path/to/triton/model/repository }
inputs:
  INPUT__0:
    name: INPUT__0
    shape: [-1, 16]
    dtype: float32
  INPUT__1:
    name: INPUT__1
    shape: [-1, 16]
    dtype: float32
outputs:
  OUTPUT__0:
    name: OUTPUT__0
    shape: [-1, 16]
    dtype: float32
  OUTPUT__1:
    name: OUTPUT__1
    shape: [-1, 16]
    dtype: float32
```

Running command using YAML configuration:

```shell
$ model-navigator triton-config-model --config-path model_navigator.yaml
```

## CLI and YAML Config Options

[comment]: <> (START_CONFIG_LIST)
```yaml
# Name of the model.
model_name: str

# Path to the model file.
model_path: path

# Path to the Triton Model Repository.
model_repository: path

# Path to the configuration file containing default parameter values to use.
# For more information about configuration files, refer to:
# https://github.com/triton-inference-server/model_navigator/blob/main/docs/run.md
[ config_path: path ]

# Path to the output workspace directory.
[ workspace_path: path | default: navigator_workspace ]

# Path to the output package.
[ output_package: path ]

# Clean workspace directory before command execution.
[ override_workspace: boolean ]

# NVIDIA framework and Triton container version to use. For details refer to
# https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html and
# https://docs.nvidia.com/deeplearning/triton-inference-server/release-notes/index.html for details).
[ container_version: str | default: 22.10 ]

# Custom framework docker image to use. If not provided
# nvcr.io/nvidia/<framework>:<container_version>-<framework_and_python_version> will be used
[ framework_docker_image: str ]

# Custom Triton Inference Server docker image to use.
# If not provided nvcr.io/nvidia/tritonserver:<container_version>-py3 will be used
[ triton_docker_image: str ]

# List of GPU UUIDs or Device IDs to be used for the conversion and/or profiling.
# All values have to be provided in the same format.
# Use 'all' to profile all the GPUs visible by CUDA.
[ gpus: str | default: ['all'] ]

# Provide verbose logs.
[ verbose: boolean ]

# Seed to use for random number generation.
[ random_seed: integer ]

# Format of the model. Should be provided in case it is not possible to obtain format from model filename.
[ model_format: choice(torchscript, tf-savedmodel, tf-trt, torch-trt, onnx, trt) ]

# Version of model used by the Triton Inference Server.
[ model_version: str | default: 1 ]

# Request model load on the Triton Server and ensure it is loaded.
[ load_model: boolean ]

# Timeout in seconds to wait until the model loads.
[ load_model_timeout_s: integer | default: 100 ]

# Triton Server Model Control Mode.
[ model_control_mode: choice(explicit, poll) | default: explicit ]

# Signature of the model inputs.
[ inputs: list[str] ]

# Signature of the model outputs.
[ outputs: list[str] ]

# Select Backend Accelerator used to serve the model.
[ backend_accelerator: choice(none, amp, trt, openvino) ]

# Target model precision for TensorRT acceleration.
[ tensorrt_precision: choice(int8, fp16, fp32) ]

# Enable CUDA capture graph feature on the TensorRT backend.
[ tensorrt_capture_cuda_graph: boolean ]

# Maximum batch size allowed for inference.
[ max_batch_size: integer | default: 128 ]

# Triton batching used for model. Supported:
# disabled: model does not support batching,
# static: Default Scheduler is used, batch has to be formed on client side,
# dynamic: Dynamic Batcher is used, batch is formed on Triton Inference Server side.
[ batching: choice(disabled, static, dynamic) | default: static ]

# Batch sizes that the dynamic batching should attempt to create.
# In case --max-queue-delay-us is set and this parameter is not, default value will be --max-batch-size.
[ preferred_batch_sizes: list[integer] ]

# Max delay time that the dynamic batching will wait to form a batch.
[ max_queue_delay_us: integer ]

# Mapping of device kind to model instances count on a single device. Available devices: [cpu|gpu].
# Format: --engine-count-per-device <kind>=<count>
[ engine_count_per_device: list[str] ]

# Triton Inference Server Custom Backend parameters map.
# Format: --triton-backend-parameters <name1>=<value1> .. <nameN>=<valueN>
[ triton_backend_parameters: list[str] ]

# Inference server URL in format protocol://host[:port]
[ server_url: str | default: grpc://localhost:8001 ]

# The maximum GPU memory in bytes the model can use temporarily during execution for TensorRT acceleration.
[ tensorrt_max_workspace_size: integer | default: 4294967296 ]

```
[comment]: <> (END_CONFIG_LIST)
