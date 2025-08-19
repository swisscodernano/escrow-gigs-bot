#!/bin/bash
# This script compiles all .po files to .mo files.

# Ensure the script is run from the project root
if [ ! -f "pyproject.toml" ]; then
    echo "Please run this script from the project root directory."
    exit 1
fi

# Compile translations
pybabel compile -d app/i18n
