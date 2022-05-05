#!/usr/bin/env bash

filename=$(basename $1 .asm)
directory=$(dirname $1)
full_name="$directory/$filename"
spirv-as $1 -o "$full_name.spv" --target-env spv1.3
spirv-cfg "$full_name.spv" -o "$full_name.dot"
dot -Tpdf "$full_name.dot" -o "$full_name.pdf"
