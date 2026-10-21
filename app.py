
import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

HISTORY_FILE = "rename_history.json"


# --------------------------------------------------
# History Management
# --------------------------------------------------

def load_history():
    """Load rename history from the JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(operations):
    """Save a batch of successful rename operations."""
    history = load_history()
    history.append(operations)

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


# --------------------------------------------------
# Filename Utilities
# --------------------------------------------------

def sanitize_filename(filename):
    """Remove characters that are invalid in Windows filenames."""
    invalid_chars = '<>:"/\\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, "")

    return filename


def generate_new_filename(filename, index, options):
    """Generate a new filename using the selected options."""
    new_name = filename

    # Replace specified text
    replace_target = options.get("replace_target", "")
    replace_with = options.get("replace_with", "")

    if replace_target:
        new_name = new_name.replace(replace_target, replace_with)

    # Remove specified text
    remove_text = options.get("remove_text", "")

    if remove_text:
        new_name = new_name.replace(remove_text, "")

    # Separate filename and extension
    name, extension = os.path.splitext(new_name)

    # Add prefix
    prefix = options.get("prefix", "")

    if prefix:
        new_name = f"{prefix}{name}{extension}"

    # Add suffix before extension
    name, extension = os.path.splitext(new_name)
    suffix = options.get("suffix", "")

    if suffix:
        new_name = f"{name}{suffix}{extension}"

    # Add sequential numbering
    if options.get("numbering"):
        name, extension = os.path.splitext(new_name)
        new_name = f"{name}_{str(index + 1).zfill(3)}{extension}"

    return sanitize_filename(new_name)


def get_preview_names(files, options):
    """Generate a preview without renaming any files."""
    preview = []

    for index, filename in enumerate(files):
        new_name = generate_new_filename(
            filename,
            index,
            options
        )

        preview.append({
            "original": filename,
            "new": new_name
        })

    return preview


# --------------------------------------------------
# File Listing
# --------------------------------------------------

@app.route("/files", methods=["POST"])
def list_files():
    """Return files in a directory, optionally filtered by extension."""
    data = request.get_json(silent=True) or {}

    directory = data.get("directory", "")
    extension_filter = data.get("extension_filter", "").strip().lower()

    if not directory or not os.path.isdir(directory):
        return jsonify({"error": "Invalid directory path."}), 400

    try:
        files = []

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            if not os.path.isfile(file_path):
                continue

            if extension_filter and not filename.lower().endswith(extension_filter):
                continue

            files.append(filename)

        return jsonify({"files": sorted(files)})

    except OSError as error:
        return jsonify({"error": str(error)}), 500


# --------------------------------------------------
# Rename Preview
# --------------------------------------------------

@app.route("/preview", methods=["POST"])
def preview():
    """Preview filename changes without modifying files."""
    data = request.get_json(silent=True) or {}

    files = data.get("files", [])
    options = data.get("options", {})

    preview_data = get_preview_names(files, options)

    return jsonify({"preview": preview_data})


# --------------------------------------------------
# Rename Files
# --------------------------------------------------

@app.route("/rename", methods=["POST"])
def rename():
    """Rename files and save successful operations to history."""
    data = request.get_json(silent=True) or {}

    directory = data.get("directory", "")
    preview_data = data.get("preview_data", [])
    allow_overwrite = data.get("allow_overwrite", False)

    if not directory or not os.path.isdir(directory):
        return jsonify({"error": "Invalid directory path."}), 400

    operations = []
    errors = []
    success_count = 0

    for item in preview_data:
        original_name = item.get("original", "")
        new_name = item.get("new", "")

        if not original_name or not new_name:
            errors.append("Invalid rename entry.")
            continue

        if original_name == new_name:
            continue

        old_path = os.path.join(directory, original_name)
        new_path = os.path.join(directory, new_name)

        # Check whether the source file exists
        if not os.path.isfile(old_path):
            errors.append(f"File not found: {original_name}")
            continue

        # Prevent accidental replacement of existing files
        if os.path.exists(new_path) and not allow_overwrite:
            errors.append(f"File already exists: {new_name}")
            continue

        try:
            os.rename(old_path, new_path)

            operations.append({
                "original_path": old_path,
                "new_path": new_path,
                "original_name": original_name,
                "new_name": new_name
            })

            success_count += 1

        except OSError as error:
            errors.append(
                f"Failed to rename {original_name}: {error}"
            )

    # Save successful operations for undo
    if operations:
        save_history(operations)

    return jsonify({
        "message": f"Successfully renamed {success_count} files.",
        "errors": errors
    })


# --------------------------------------------------
# Undo Last Rename Batch
# --------------------------------------------------

@app.route("/undo", methods=["POST"])
def undo():
    """Undo the most recent batch of successful renames."""
    history = load_history()

    if not history:
        return jsonify({
            "error": "No recent operations to undo."
        }), 400

    last_batch = history.pop()
    errors = []
    success_count = 0

    # Reverse the operations in reverse order
    for operation in reversed(last_batch):
        old_path = operation["new_path"]
        original_path = operation["original_path"]

        try:
            if not os.path.exists(old_path):
                errors.append(f"File not found: {old_path}")
                continue

            if os.path.exists(original_path):
                errors.append(
                    f"Cannot undo: destination already exists: {original_path}"
                )
                continue

            os.rename(old_path, original_path)
            success_count += 1

        except OSError as error:
            errors.append(
                f"Failed to undo {operation['new_name']}: {error}"
            )

    # Persist the remaining history
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)

    return jsonify({
        "message": f"Successfully undone {success_count} files.",
        "errors": errors
    })


# --------------------------------------------------
# Main Application
# --------------------------------------------------

@app.route("/")
def index():
    """Render the main application page."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
