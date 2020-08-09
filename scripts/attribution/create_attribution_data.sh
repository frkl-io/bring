#!/usr/bin/env bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

PROJECT_ROOT=${1}
if [[ -z "${PROJECT_ROOT}" ]]; then
  PROJECT_ROOT=${PWD}
fi

ATTRIBUTION_DATA_FILE=${2}
if [[ -z "${ATTRIBUTION_DATA_FILE}" ]]; then
  ATTRIBUTION_DATA_FILE="attribution.json"
fi

tmp_dir=$(mktemp -d -t ci-XXXXXXXXXX)
venv="${tmp_dir}/venv"

python3 -m venv "${venv}"

source "${venv}/bin/activate"

pip install pip-licenses
pip install --pre --extra-index-url https://pkgs.frkl.io/frkl/dev --extra-index-url https://pkgs.frkl.dev/pypi "${PROJECT_ROOT}[all]"

pip-licenses --from=mixed --with-authors --with-urls --with-description --with-license-file --format json --output-file "${ATTRIBUTION_DATA_FILE}"

rm -r "${tmp_dir}"
