#!/bin/bash
set -e
set -o pipefail

# This script formats Python (.py) and Jupyter Notebook (.ipynb) files.
# It's designed to be git-aware, ignoring files listed in .gitignore.
#
# NOTE: For Notebook formatting, you must have the required packages installed.
# Based on the provided snippet, these are:
# pip install "git+https://github.com/tensorflow/docs" ipython jupyter nbconvert nbqa nbformat

# --- Argument Parsing ---
# Initialize flags
FORMAT_ALL=false
RUFF_UNSAFE_FIXES_FLAG=""

# Process command-line arguments
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--all)
		FORMAT_ALL=true
		echo "Detected --all flag: Formatting all tracked Python and Notebook files."
		shift # Consume the argument
		;;
	--unsafe-fixes)
		RUFF_UNSAFE_FIXES_FLAG="--unsafe-fixes"
		echo "Detected --unsafe-fixes flag: Ruff will run with unsafe fixes."
		shift # Consume the argument
		;;
	*)
		# Handle unknown arguments or just ignore them
		echo "Warning: Unknown argument '$1'. Ignoring."
		shift # Consume the argument
		;;
	esac
done

# Sort Spelling Allowlist
SPELLING_ALLOW_FILE=".github/actions/spelling/allow.txt"
if [ -f "$SPELLING_ALLOW_FILE" ]; then
	echo "Sorting and de-duplicating $SPELLING_ALLOW_FILE"
	sort -u "$SPELLING_ALLOW_FILE" -o "$SPELLING_ALLOW_FILE"
fi

# --- File Discovery ---
CHANGED_PY_FILES=""
CHANGED_NB_FILES=""

if $FORMAT_ALL; then
	echo "Finding all tracked Python and Notebook files in the repository..."
	CHANGED_PY_FILES=$(git ls-files -- '*.py' ':!src/a2a/grpc/*')
	CHANGED_NB_FILES=$(git ls-files -- '*.ipynb')
else
	echo "Finding changed Python and Notebook files based on git diff..."
	TARGET_BRANCH="origin/${GITHUB_BASE_REF:-main}"
	git fetch origin "${GITHUB_BASE_REF:-main}" --depth=1

	MERGE_BASE=$(git merge-base HEAD "$TARGET_BRANCH")

	# Get python files changed in this PR, excluding grpc generated files.
	CHANGED_PY_FILES=$(git diff --name-only --diff-filter=ACMRTUXB "$MERGE_BASE" HEAD -- '*.py' ':!src/a2a/grpc/*')
	CHANGED_NB_FILES=$(git diff --name-only --diff-filter=ACMRTUXB "$MERGE_BASE" HEAD -- '*.ipynb')
fi

# Exit if no files of either type were found
if [ -z "$CHANGED_PY_FILES" ] && [ -z "$CHANGED_NB_FILES" ]; then
	echo "No changed or tracked Python or Notebook files to format."
	exit 0
fi

# --- Helper Function ---
# Runs a command on a list of files passed via stdin.
# $1: A string containing the list of files (space-separated).
# $2...: The command and its arguments to run.
run_formatter() {
	local files_to_format="$1"
	shift # Remove the file list from the arguments
	if [ -n "$files_to_format" ]; then
		echo "$files_to_format" | xargs -r "$@"
	fi
}

# --- Python File Formatting ---
if [ -n "$CHANGED_PY_FILES" ]; then
	echo "--- Formatting Python Files ---"
	echo "Files to be formatted:"
	echo "$CHANGED_PY_FILES"

	echo "Running autoflake..."
	run_formatter "$CHANGED_PY_FILES" autoflake -i -r --remove-all-unused-imports
	echo "Running ruff check (fix-only)..."
	run_formatter "$CHANGED_PY_FILES" ruff check --fix-only $RUFF_UNSAFE_FIXES_FLAG
	echo "Running ruff format..."
	run_formatter "$CHANGED_PY_FILES" ruff format
	echo "Python formatting complete."
else
	echo "No Python files to format."
fi

# --- Jupyter Notebook Formatting ---
if [ -n "$CHANGED_NB_FILES" ]; then
	echo "--- Formatting Jupyter Notebooks ---"
	echo "Notebooks to be formatted:"
	echo "$CHANGED_NB_FILES"

	echo "Updating notebook links..."
	python3 .github/workflows/update_notebook_links.py .

	echo "Running nbqa autoflake..."
	run_formatter "$CHANGED_NB_FILES" nbqa autoflake -i -r --remove-all-unused-imports
	echo "Running nbqa ruff --fix-only..."
	run_formatter "$CHANGED_NB_FILES" nbqa "ruff check --fix-only $RUFF_UNSAFE_FIXES_FLAG"
	echo "Running nbqa ruff format..."
	run_formatter "$CHANGED_NB_FILES" nbqa "ruff format"
	echo "Running tensorflow_docs nbfmt..."
	run_formatter "$CHANGED_NB_FILES" python3 -m tensorflow_docs.tools.nbfmt
	echo "Notebook formatting complete."
else
	echo "No Jupyter Notebooks to format."
fi

echo "All formatting tasks are complete."
