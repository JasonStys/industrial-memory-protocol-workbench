#!/usr/bin/env bash
# @file validate.sh
# @brief Runs the portable configure, build, test, demo, index, and repository-policy checks.
# @details Important command locations are indexed in docs/generated/symbol-index.md.

set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_directory="${repository_root}/build/validate"

cmake -S "${repository_root}" -B "${build_directory}" -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build "${build_directory}" --parallel
ctest --test-dir "${build_directory}" --output-on-failure
"${build_directory}/imlp-cli" demo
python3 "${repository_root}/scripts/generate_symbol_index.py" --check
python3 "${repository_root}/scripts/check_repository.py"

