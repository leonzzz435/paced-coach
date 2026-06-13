#!/usr/bin/env bash
set -euo pipefail

PIXI_VERSION="0.65.0"
PIXI_RELEASE="v${PIXI_VERSION}"
PIXI_BASE_URL="https://github.com/prefix-dev/pixi/releases/download/${PIXI_RELEASE}"
INSTALL_DIR="${1:-$HOME/.pixi/bin}"

mkdir -p "${INSTALL_DIR}"

case "$(uname -m)" in
  x86_64|amd64)
    PIXI_ARCHIVE="pixi-x86_64-unknown-linux-musl.tar.gz"
    PIXI_ARCHIVE_SHA256="216adf73a7ba92547d38a4768c2c7cdad8cabb90af466b00c9ef69db89dc8649"
    ;;
  aarch64|arm64)
    PIXI_ARCHIVE="pixi-aarch64-unknown-linux-musl.tar.gz"
    PIXI_ARCHIVE_SHA256="c77be0963888a2da84dc79f331bfef7feee9945aff2b2e6ae555e72c4172258f"
    ;;
  *)
    echo "Unsupported architecture for Pixi install: $(uname -m)" >&2
    exit 1
    ;;
esac

tmp_archive="$(mktemp)"
trap 'rm -f "${tmp_archive}"' EXIT

curl -fsSL "${PIXI_BASE_URL}/${PIXI_ARCHIVE}" -o "${tmp_archive}"
echo "${PIXI_ARCHIVE_SHA256}  ${tmp_archive}" | sha256sum -c -
tar -xzf "${tmp_archive}" -C "${INSTALL_DIR}"
chmod +x "${INSTALL_DIR}/pixi"
