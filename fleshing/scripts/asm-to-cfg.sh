#!/usr/bin/env bash

filename=$(basename $2 .asm)
directory=$(dirname $2)
full_name="$directory/$filename"
spirv-as $2 -o "$full_name.spv" --target-env spv1.3 --preserve-numeric-ids
spirv-cfg "$full_name.spv" -o "$full_name.dot"
if [ $1 == "pdf" ]; then
  dot -Tpdf "$full_name.dot" -o "$full_name.pdf"
else
  dot -Tpng "$full_name.dot" -o "$full_name.png"
fi 

