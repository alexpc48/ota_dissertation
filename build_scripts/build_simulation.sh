#!/bin/bash
# This script is used to build the simulation environment for the project

# Set environment variables
root_dir="$(cd "$(dirname "$0")/.." && pwd)"
build_scripts_dir="$root_dir/build_scripts"
helpers_dir="$root_dir/helpers"

# Clean tree of old build files
cd "$root_dir"
echo "Cleaning up old build files ..."
rm -rf build/ install_location/
rm -f client.exe.spec server.exe.spec client.exe server.exe
rm -f server_ota_updates.db client_linux_ota_updates.db client_windows_ota_updates.db

# Create the update installation path
if [ ! -d "$root_dir/install_location" ]; then
    echo "Creating update installation path..."
    mkdir -p "$root_dir/install_location"
fi

# Setup new databases and populae the tables
echo "Setting up new databases ..."
python "$helpers_dir/setup_db.py"

# Build executables
echo "Building executables ..."
pyinstaller --onefile --name client.exe --distpath "$root_dir" client.py
pyinstaller --onefile --name server.exe --distpath "$root_dir" server.py

# Return back to the build_scripts directory
echo "Build complete."
cd "$build_scripts_dir"


