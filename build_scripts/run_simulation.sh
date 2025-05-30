#!/bin/bash
# This script is used to run the simulation project

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
build_scripts_dir="$root_dir/build_scripts"

cd "$root_dir"
# gnome-terminal -- bash -c "./server.exe"
# gnome-terminal -- bash -c "./client.exe"

# Debug
gnome-terminal -- bash -c "./server.exe; exec bash"
gnome-terminal -- bash -c "./client.exe; exec bash"

cd "$build_scripts_dir"
