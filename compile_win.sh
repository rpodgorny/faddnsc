#!/bin/sh
set -e -x

rm -rf target

cargo build --target x86_64-pc-windows-gnu --release --locked
#cp -av target_nw/x86_64-pc-windows-gnu/release/atxrouter.exe target/x86_64-pc-windows-gnu/release/atxrouter_nw.exe
