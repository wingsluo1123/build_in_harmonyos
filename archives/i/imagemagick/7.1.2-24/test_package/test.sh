#!/usr/bin/env bash
set -euo pipefail

version_output="$(magick -version)"
printf '%s\n' "$version_output" | grep -F "ImageMagick 7.1.2-24"

pixel_output="$(magick -size 1x1 xc:red txt:-)"
printf '%s\n' "$pixel_output" | grep -F "red"
