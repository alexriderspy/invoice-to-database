#!/bin/bash
name="$1"; shift
out="media/terminal/$name.log"
{ echo "sreemanti@MacBook-Pro invoice-pipeline % $*"; "$@" 2>&1; } | tee "$out"
