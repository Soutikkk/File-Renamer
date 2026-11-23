
import os
import json

from flask import Flask, render_template, request, jsonify


app = Flask(__name__)

HISTORY_FILE = "rename_history.json"
INVALID_CHARACTERS = '<>:"/\\|?*'


# ==================================================
# HISTORY MANAGEMENT
# ==================================================

def load_history():
    """Read previously saved rename operations."""

    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        return []


def save_history(history):
    """Write rename history to the JSON file."""

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


def add_to_history(operations):
    """Add a successful rename batch to history."""

    history = load_history()
    history.append(operations)

    save_history(history)


# ==================================================
# FILENAME UTILITIES
# ==================================================

def sanitize_filename(filename):
    """Remove characters not allowed in Windows filenames."""

    return "".join(
        char for char in filename
        if char not in INVALID_CHARACTERS
    )


def generate_new_filename(filename, index, options):
    """Generate a filename using the selected options."""

    # Replace text
    target = options.get("replace_target", "")
    replacement = options.get("replace_with", "")

    if target:
        filename = filename.replace(target, replacement)

    # Remove text
    remove_text = options.get("remove_text", "")

    if remove_text:
        filename = filename.replace(remove_text, "")

    # Separate filename and extension
    name, extension = os.path.splitext(filename)

    # Add prefix and suffix
    prefix = options.get("prefix", "")
    suffix = options.get("suffix", "")

    name = f"{prefix}{name}{suffix}"

    # Add sequential numbering
    if options.get("numbering", False):
        name += f"_{index + 1:03d}"

    # Combine and sanitize
    return sanitize_filename(name + extension)


def generate_preview(files, options):
    """Generate proposed filenames without changing files."""

    return [
        {
            "original": filename,
            "new": generate_new_filename(
                filename, index, options
            )
        }
        for index, filename in enumerate(files)
    ]


# ==================================================
# DIRECTORY UTILITIES
# ==================================================

def is_valid_directory(directory):
    """Check whether the directory exists."""

    return bool(directory) and os.path.isdir(directory)


def get_directory_files(directory, extension_filter=""):
    """Return sorted files matching the extension filter."""

    files = []

    for filename in os.listdir(directory):

        file_path = os.path.join(directory, filename)

        if not os.path.isfile(file_path):
            continue

        if extension_filter:
            if not filename.lower().endswith(extension_filter.lower()):
                continue

        files.append(filename)

    return sorted(files)


# ==================================================
# FILE ROUTES
# ==================================================

@app.route("/files", methods=["POST"])
def list_files():
    """List files inside a selected directory."""

    data = request.get_json(silent=True) or {}

    directory = data.get("directory", "")
    extension = data.get("extension_filter", "").strip()

    if not is_valid_directory(directory):
        return jsonify(error="Invalid directory path."), 400

    try:
        files = get_directory_files(directory, extension)
        return jsonify(files=files)

    except OSError as error:
        return jsonify(error=str(error)), 500


@app.route("/preview", methods=["POST"])
def preview():
    """Preview the renamed filenames."""

    data = request.get_json(silent=True) or {}

    files = data.get("files", [])
    options = data.get("options", {})

    preview_data = generate_preview(files, options)

    return jsonify(preview=preview_data)


# ==================================================
# RENAME OPERATIONS
# ==================================================

def rename_file(directory, original_name, new_name, allow_overwrite):
    """Rename a single file and return its operation record."""

    if not original_name or not new_name:
        return None, "Invalid rename entry."

    if original_name == new_name:
        return None, None

    old_path = os.path.join(directory, original_name)
    new_path = os.path.join(directory, new_name)

    if not os.path.isfile(old_path):
        return None, f"File not found: {original_name}"

    if os.path.exists(new_path) and not allow_overwrite:
        return None, f"File already exists: {new_name}"

    try:
        os.rename(old_path, new_path)

        operation = {
            "original_path": old_path,
            "new_path": new_path,
            "original_name": original_name,
            "new_name": new_name
        }

        return operation, None

    except OSError as error:
        return None, f"Failed to rename {original_name}: {error}"


@app.route("/rename", methods=["POST"])
def rename():
    """Rename selected files and record successful operations."""

    data = request.get_json(silent=True) or {}

    directory = data.get("directory", "")
    preview_data = data.get("preview_data", [])
    allow_overwrite = data.get("allow_overwrite", False)

    if not is_valid_directory(directory):
        return jsonify(error="Invalid directory path."), 400

    operations = []
    errors = []

    for item in preview_data:

        operation, error = rename_file(
            directory,
            item.get("original", ""),
            item.get("new", ""),
            allow_overwrite
        )

        if operation:
            operations.append(operation)

        if error:
            errors.append(error)

    if operations:
        add_to_history(operations)

    return jsonify(
        message=f"Successfully renamed {len(operations)} files.",
        errors=errors
    )


# ==================================================
# UNDO OPERATIONS
# ==================================================

def undo_file(operation):
    """Restore a renamed file to its original filename."""

    renamed_path = operation["new_path"]
    original_path = operation["original_path"]

    if not os.path.exists(renamed_path):
        return f"File not found: {renamed_path}"

    if os.path.exists(original_path):
        return f"Cannot undo: destination already exists: {original_path}"

    try:
        os.rename(renamed_path, original_path)
        return None

    except OSError as error:
        return f"Failed to undo {operation['new_name']}: {error}"


@app.route("/undo", methods=["POST"])
def undo():
    """Undo the latest batch of rename operations."""

    history = load_history()

    if not history:
        return jsonify(error="No recent operations to undo."), 400

    last_batch = history.pop()

    errors = []
    success_count = 0

    for operation in reversed(last_batch):

        error = undo_file(operation)

        if error:
            errors.append(error)
        else:
            success_count += 1

    save_history(history)

    return jsonify(
        message=f"Successfully undone {success_count} files.",
        errors=errors
    )


# ==================================================
# MAIN APPLICATION
# ==================================================

@app.route("/")
def index():
    """Display the main application page."""

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
