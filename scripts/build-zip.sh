#!/usr/bin/env bash
# Builds build/Hoard.zip for "Install Plugin from ZIP File" in Decky's developer mode.
# Decky names the plugin's folder, and so its settings and log folders, after the zip's
# top-level folder, which is why that folder is always Hoard/. It also looks for the
# installed plugin to replace by the zip's file name, so the file is always Hoard.zip.
set -euo pipefail

cd "$(dirname "$0")/.."

stage=build/zip
out=build/Hoard.zip

pnpm build

rm -rf "$stage" "$out"
mkdir -p "$stage/Hoard/dist"
cp dist/index.js "$stage/Hoard/dist/"
cp main.py scanner.py plugin.json package.json LICENSE "$stage/Hoard/"
(cd "$stage" && zip -qrX "../${out#build/}" Hoard)

echo "$out"
