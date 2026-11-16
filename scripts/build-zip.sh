#!/usr/bin/env bash
# Builds build/Hoard-<version>.zip for "Install plugin from ZIP" in Decky's developer mode.
# Decky names the plugin's folder, and so its settings and log folders, after the zip's
# top-level folder, which is why that folder is always Hoard/.
set -euo pipefail

cd "$(dirname "$0")/.."

version=$(node -p 'require("./package.json").version')
stage=build/zip
out="build/Hoard-$version.zip"

pnpm build

rm -rf "$stage" "$out"
mkdir -p "$stage/Hoard/dist"
cp dist/index.js "$stage/Hoard/dist/"
cp main.py scanner.py plugin.json package.json LICENSE "$stage/Hoard/"
(cd "$stage" && zip -qrX "../${out#build/}" Hoard)

echo "$out"
