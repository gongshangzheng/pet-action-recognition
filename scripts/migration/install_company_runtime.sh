#!/usr/bin/env bash
# Install dependencies only. Never invokes a model, a dataset, or a train/test loop.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="$ROOT/.runtime"
CACHE="$RUNTIME/cache"
WHEELS="$CACHE/wheels"
REPORT="$ROOT/results/deployment/company_runtime_20260930"
mkdir -p "$CACHE/bootstrap" "$WHEELS" "$RUNTIME/tmp" "$REPORT"
export TMPDIR="$RUNTIME/tmp" PIP_CACHE_DIR="$CACHE/pip"
export PIP_INDEX_URL="${COMPANY_PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_DEFAULT_TIMEOUT=180
export PYTHONNOUSERSITE=1
unset PIP_EXTRA_INDEX_URL
trap 'code=$?; printf "INSTALL_EXIT=%s\n" "$code"; exit "$code"' EXIT
printf 'INSTALL_START %s\n' "$(date -u +%FT%TZ)"

INSTALLER=Miniconda3-py310_23.3.1-0-Linux-x86_64.sh
# SHA256 published by https://repo.anaconda.com/miniconda/.
INSTALLER_SHA=aef279d6baea7f67940f16aad17ebe5f6aac97487c7c03466ff01f4819e5a651
if [[ ! -x "$RUNTIME/conda/bin/python" ]]; then
    printf 'STAGE bootstrap_download\n'
    if ! printf '%s  %s\n' "$INSTALLER_SHA" "$CACHE/bootstrap/$INSTALLER" | sha256sum -c --status; then
        curl -fL --retry 8 --retry-delay 5 --connect-timeout 30 \
            --speed-limit 1024 --speed-time 180 -C - \
            -o "$CACHE/bootstrap/$INSTALLER" \
            "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/$INSTALLER"
    fi
    printf '%s  %s\n' "$INSTALLER_SHA" "$CACHE/bootstrap/$INSTALLER" | sha256sum -c -
    bash "$CACHE/bootstrap/$INSTALLER" -b -p "$RUNTIME/conda"
fi
if [[ ! -x "$RUNTIME/pet/bin/python" ]]; then
    "$RUNTIME/conda/bin/python" -m venv "$RUNTIME/pet"
fi
PY="$RUNTIME/pet/bin/python"
export PATH="$RUNTIME/pet/bin:$PATH"
"$PY" --version
printf 'STAGE pip_bootstrap\n'
"$PY" -m pip install --retries 12 'pip==25.2' 'setuptools==69.5.1' 'wheel==0.43.0'

printf 'STAGE dependency_download\n'
"$PY" -m pip download --retries 12 --resume-retries 20 --only-binary=:all: \
    -r "$ROOT/configs/company_runtime_requirements.txt" -d "$WHEELS" \
    'pip==25.2'

MMCV_WHEEL=mmcv-2.1.0-cp310-cp310-manylinux1_x86_64.whl
if [[ ! -f "$WHEELS/$MMCV_WHEEL" ]]; then
    printf 'STAGE mmcv_download\n'
    curl -fL --retry 8 --retry-delay 5 --connect-timeout 30 \
        --speed-limit 1024 --speed-time 180 -C - \
        -o "$WHEELS/$MMCV_WHEEL.part" \
        "https://download.openmmlab.com/mmcv/dist/cu121/torch2.1.0/$MMCV_WHEEL"
    mv "$WHEELS/$MMCV_WHEEL.part" "$WHEELS/$MMCV_WHEEL"
fi
printf 'STAGE offline_dependency_install\n'
"$PY" -m pip install --no-index --find-links "$WHEELS" \
    -r "$ROOT/configs/company_runtime_requirements.txt" "$WHEELS/$MMCV_WHEEL"

printf 'STAGE local_mmaction_install\n'
"$PY" -m pip install --no-index --no-deps --no-build-isolation -e "$ROOT/models/mmaction2"
# AVA visualization uses MoviePy 1.x; MViT training uses PytorchVideoWrapper.
"$PY" -m pip wheel --retries 12 --no-build-isolation --wheel-dir "$WHEELS" \
    --constraint "$ROOT/configs/company_runtime_requirements.txt" \
    'moviepy==1.0.3' 'pytorchvideo==0.1.5' 'lmdb==1.5.1'
"$PY" -m pip install --no-index --find-links "$WHEELS" \
    'moviepy==1.0.3' 'pytorchvideo==0.1.5' 'lmdb==1.5.1'

"$PY" -m pip freeze > "$REPORT/pip-freeze.txt"
"$PY" -m pip list --format=json > "$REPORT/packages.json"
# The audit records pip check verbatim and recognizes only Decord's known
# cp36 internal wheel-tag error after its native-library import succeeds.
find "$WHEELS" -maxdepth 1 -type f -name '*.whl' -print0 | sort -z | xargs -0 sha256sum > "$REPORT/wheels.sha256"
printf 'STAGE dependency_only_audit\n'
"$PY" "$ROOT/scripts/checks/audit_company_runtime.py" --root "$ROOT" --out "$REPORT"
printf 'INSTALL_DEPENDENCIES_DONE %s\n' "$(date -u +%FT%TZ)"
