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

# Optimize for Triton Inference Server

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Synopsis](#synopsis)
- [Description](#description)
- [Examples](#examples)
  - [Using a package](#using-a-package)
  - [Using CLI arguments to override default package settings](#using-cli-arguments-to-override-default-package-settings)
  - [Using a YAML file](#using-a-yaml-file)
- [Advanced usage](#advanced-usage)
  - [Example using a TorchScript file](#example-using-a-torchscript-file)
  - [Example using a TensorFlow SavedModel](#example-using-a-tensorflow-savedmodel)
- [CLI and YAML Config Options](#cli-and-yaml-config-options)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

The Triton Model Navigator supports a single command to run through the process and step-by-step execution going through each stage.

The `model-navigator optimize` command replaces the old default behavior where all the steps are being performed one by one. Review the other commands to learn more about the process:
- [Model Conversion](advanced/conversion.md)
- [Triton Model Configurator](advanced/triton_model_configurator.md)
- [Profiling](advanced/profiling.md)
- [Analysis](advanced/analysis.md)
- [Helm Chart Generator](advanced/helm_charts.md)

## Synopsis

```shell
$ model-navigator optimize [<options>] [-o _outpackage_] [ _package_ ]
```

## Description

The `model-navigator optimize` command performs step-by-step execution of model optimization and profiling.
The `optimize` operations start the model conversion to optimized formats like the TensorRT plan, verify
the conversion correctness, evaluate optimized model versions on Triton, and profile them using
the Triton Model Analyzer. In the final stage, the `optimize` command analyzes the obtained results
based on provided constraints and objectives, and prepares the Helm Charts deployment for
top N configurations on the Triton Inference Server.

The preferred way to use `model-navigator optimize` is to supply a Navigator package.
For advanced users, it is also possible to use raw TorchScript/SavedModel models as inputs.
The output of the procedure is a `triton.nav` package.

## Examples

### Using a package

```shell
$ model-navigator optimize model_navigator/examples/quick-start/model.nav
```

### Using CLI arguments to override default package settings

```shell
$ model-navigator optimize --tensorrt_max_workspace_size 8589934592 \
    --config-search-max-concurrency 256 \
    --max-latency-ms 50 \
    --verbose \
	model_navigator/examples/quick-start/model.nav
```

### Using a YAML file

```yaml
inputs:
  INPUT__0:
    name: INPUT__0
    shape:
    - -1
    - 16
    dtype: float32
  INPUT__1:
    name: INPUT__1
    shape:
    - -1
    - 16
    dtype: float32
outputs:
  OUTPUT__0:
    name: OUTPUT__0
    shape:
    - -1
    - 16
    dtype: float32
  OUTPUT__1:
    name: OUTPUT__1
    shape:
    - -1
    - 16
    dtype: float32
max_concurrency: 256
max_latency_ms: 50
verbose: true
```

Running the Triton Model Navigator optimize command:

```shell
$ model-navigator optimize --config-path model_navigator.yaml model_navigator/examples/quick-start/model.nav
```


## Advanced usage

Model Navigator can also take raw TorchScript/SavedModel models as inputs, however this
requires specifying numerous additional options, depending on desired input and output model formats.

### Example using a TorchScript file

Since TorchScript files do not contain signatures of inputs (i.e. their sizes and datatypes),
those have to be supplied as options.

```shell
$ model-navigator optimize --model-name add_sub \
    --model-path model_navigator/examples/quick-start/model.pt \
    --inputs input0:-1,16:float32 input1:-1,16:float32 \
    --outputs OUTPUT__0:-1,16:float32 OUTPUT__1:-1,16:float32 \
    --config-search-max-concurrency 256 \
    --max-latency-ms 50
```

The input names are the same as argument names to the forward function.
Output names should follow the convention described in the [Triton Inference Server documentation](https://github.com/triton-inference-server/server/blob/89b7f8b30bf84d20f96825a6c476e7f71eca6dd6/docs/model_configuration.md#inputs-and-outputs).

### Example using a TensorFlow SavedModel

```shell
$ model-navigator optimize --model-name add-sub \
    --model-path model_navigator/examples/quick-start/model.pt
```

## CLI and YAML Config Options

The Triton Model Navigator can be configured with a [YAML](https://yaml.org/) file or via the command-line interface (CLI).
Every flag supported by the CLI is supported in the configuration file.

The placeholders below are used throughout the configuration:

* `text`: a regular string value
* `integer`: a regular integer value
* `boolean`: a regular boolean value (in the CLI it is the form of a boolean flag)
* `choice(<choices>)`: a string which value should equal to one from the listed
* `path`: a string value pointing to the path
* `list[<type>]`: list of values separated by a string where type is defined as arg

A list of all the configuration options supported by both the CLI and YAML config file are shown below.
Brackets indicate that a parameter is optional. For non-list and non-object parameters, the value is set to the specified default.

The CLI flags corresponding to each of the following options are obtained by converting the `snake_case` options
to `--kebab-case`. For example, `model_name` in the YAML would be `--model-name` in the CLI.

[comment]: <> (START_CONFIG_LIST)
```yaml
# Name of the model.
model_name: str

# Path to the model file.
model_path: path

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

# Signature of the model inputs.
[ inputs: list[str] ]

# Signature of the model outputs.
[ outputs: list[str] ]

# Target format to generate.
[ target_formats: list[str] | default: ['tf-trt', 'tf-savedmodel', 'onnx', 'trt', 'torchscript', 'torch-trt'] ]

# Generate an ONNX graph that uses only ops available in a given opset.
[ onnx_opsets: list[integer] | default: [14] ]

# Configure TensorRT builder for precision layer selection.
[ tensorrt_precisions: list[choice(int8, fp16, fp32, tf32)] | default: ['fp16', 'fp32'] ]

# Select how target precision should be applied during conversion:
# 'hierarchy': enable possible precisions for values passed in target precisions int8 enable tf32, fp16 and int8
# 'single': each precision passed in target precisions is applied separately
# 'mixed': combine both strategies
[ tensorrt_precisions_mode: choice(hierarchy, single, mixed) | default: hierarchy ]

# Enable explicit precision for TensorRT builder when model already contain quantized layers.
[ tensorrt_explicit_precision: boolean ]

# Enable optimizations for sparse weights in TensorRT.
[ tensorrt_sparse_weights: boolean ]

# The maximum GPU memory in bytes the model can use temporarily during execution for TensorRT acceleration.
[ tensorrt_max_workspace_size: integer | default: 4294967296 ]

# Absolute tolerance parameter for output comparison.
# To specify per-output tolerances, use the format: --atol [<out_name>=]<atol>.
# Example: --atol 1e-5 out0=1e-4 out1=1e-3
[ atol: list[str] | default: ['1e-05'] ]

# Relative tolerance parameter for output comparison.
# To specify per-output tolerances, use the format: --rtol [<out_name>=]<rtol>.
# Example: --rtol 1e-5 out0=1e-4 out1=1e-3
[ rtol: list[str] | default: ['1e-05'] ]

# Map of features names and minimum shapes visible in the dataset.
# Format: --min-shapes <input0>=D0,D1,..,DN .. <inputN>=D0,D1,..,DN
[ min_shapes: list[str] ]

# Map of features names and optimal shapes visible in the dataset.
# Used during the definition of the TensorRT optimization profile.
# Format: --opt-shapes <input0>=D0,D1,..,DN .. <inputN>=D0,D1,..,DN
[ opt_shapes: list[str] ]

# Map of features names and maximal shapes visible in the dataset.
# Format: --max-shapes <input0>=D0,D1,..,DN .. <inputN>=D0,D1,..,DN
[ max_shapes: list[str] ]

# Map of features names and range of values visible in the dataset.
# Format: --value-ranges <input0>=<lower_bound>,<upper_bound> ..
# <inputN>=<lower_bound>,<upper_bound> <default_lower_bound>,<default_upper_bound>
[ value_ranges: list[str] ]

# Map of features names and numpy dtypes visible in the dataset.
# Format: --dtypes <input0>=<dtype> <input1>=<dtype> <default_dtype>
[ dtypes: list[str] ]

# Triton Inference Server Custom Backend parameters map.
# Format: --triton-backend-parameters <name1>=<value1> .. <nameN>=<valueN>
[ triton_backend_parameters: list[str] ]

# Mapping of device kind to model instances count on a single device. Available devices: [cpu|gpu].
# Format: --engine-count-per-device <kind>=<count>
[ engine_count_per_device: list[str] ]

# The method used  to launch the Triton Server.
# 'local' assume tritonserver binary is available locally.
# 'docker' pulls and launches a triton docker container with the specified version.
[ triton_launch_mode: choice(local, docker) | default: local ]

# Path to the Triton Server binary when the local mode is enabled.
[ triton_server_path: str | default: tritonserver ]

# Model max batch size used for automatic config search in profiling.
[ config_search_max_batch_size: integer | default: 128 ]

# Max client side request concurrency used for automatic config search in profiling.
[ config_search_max_concurrency: integer | default: 1024 ]

# Max number of model instances count used for automatic config search in profiling.
[ config_search_max_instance_count: integer | default: 5 ]

# List of client side request concurrency used for manual config search in profiling.
# Forces manual config search.
# Format: --config-search-concurrency 1 2 4 ...
[ config_search_concurrency: list[integer] ]

# List of client side request batch size used for manual config search in profiling.
# Forces manual config search.
# Format: --config-search-batch-sizes 1 2 4 ...
[ config_search_batch_sizes: list[integer] ]

# List of model instance count used for manual config search in profiling.
# Forces manual config search.
# Format: --config-search-instance-counts <DeviceKind>=<count>,<count> <DeviceKind>=<count> ...
[ config_search_instance_counts: list[str] ]

# List of model max batch sizes used for manual config search in profiling. Forces manual config search.
# Format: --config-search-max-batch-sizes 1 2 4 ...
[ config_search_max_batch_sizes: list[integer] ]

# List of preferred batch sizes used for manual config search in profiling.
# Forces manual config search.
# Format: --config-search-preferred-batch-sizes 4,8,16 8,16 16 ...
[ config_search_preferred_batch_sizes: list[str] ]

# List of custom backend parameters used for manual config search in profiling.
# Forces manual config search.
# Format: --config-search-backend-parameters <param_name1>=<value1>,<value2> <param_name2>=<value3> ...
[ config_search_backend_parameters: list[str] ]

# Enable early exit on profiling when configuration not bring performance improvement.
# When automatic config search is used, the early exit is enabled by default.
[ config_search_early_exit_enable: boolean ]

# Number of top final configurations selected from the analysis.
[ top_n_configs: integer | default: 3 ]

# The Model Navigator uses the objectives described here to find the best configuration for the model.
[ objectives: list[str] | default: ['perf_throughput=10'] ]

# Maximum latency in ms that the analyzed models should match.
[ max_latency_ms: integer ]

# Minimal throughput that the analyzed models should match.
[ min_throughput: integer ]

# Maximal GPU memory usage in MB that analyzed model should match.
[ max_gpu_usage_mb: integer ]

# Perf Analyzer measurement timeout in seconds.
[ perf_analyzer_timeout: integer | default: 600 ]

# Path to perf_analyzer binary.
[ perf_analyzer_path: str | default: perf_analyzer ]

# Perf Analyzer measurement mode. Available: count_windows, time_windows.
[ perf_measurement_mode: str | default: count_windows ]

# Perf Analyzer count windows number of samples to used for stabilization.
[ perf_measurement_request_count: integer | default: 50 ]

# Perf Analyzer time windows time in [ms] used for stabilization.
[ perf_measurement_interval: integer | default: 5000 ]

# Define usage of shared memory to pass tensors:
# none - no shared memory used
# system - use RAM memory.
# cuda - use GPU memory.
[ perf_measurement_shared_memory: str | default: none ]

# Define size of shared memory for model outputs.
[ perf_measurement_output_shared_memory_size: integer | default: 102400 ]

# The method by which to launch conversion. 'local' assume conversion will be run locally. 'docker' build conversion
# Docker and perform operations inside it.
[ launch_mode: choice(local, docker) | default: docker ]

# Override conversion container if it already exists.
[ override_conversion_container: boolean ]

```
[comment]: <> (END_CONFIG_LIST)
