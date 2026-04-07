import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# File to store history for undo functionality
HISTORY_FILE = "rename_history.json"

def save_history(operations):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except Exception:
                pass
    # operations is a list of dicts: {'original_path': '...', 'new_path': '...', ...}
    history.append(operations)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return []

def sanitize_filename(filename):
    """Remove characters that are invalid in Windows file names."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

def get_preview_names(directory, files, options):
    """Apply renaming logic on the fly to generate a preview."""
    preview = []
    for index, filename in enumerate(files):
        new_name = filename
        name_part, ext_part = os.path.splitext(filename)
        
        # 1. Replace text
        if options.get('replace_target'):
            new_name = new_name.replace(options['replace_target'], options.get('replace_with', ''))
            
        # 2. Remove text
        if options.get('remove_text'):
            new_name = new_name.replace(options['remove_text'], '')
            
        name_part, ext_part = os.path.splitext(new_name)
            
        # 3. Add Prefix
        if options.get('prefix'):
            new_name = f"{options['prefix']}{new_name}"
            
        # 4. Add Suffix (added to name before extension)
        if options.get('suffix'):
            name_part, ext_part = os.path.splitext(new_name)
            new_name = f"{name_part}{options['suffix']}{ext_part}"
            
        # 5. Numbering
        if options.get('numbering'):
            name_part, ext_part = os.path.splitext(new_name)
            new_name = f"{name_part}_{str(index + 1).zfill(3)}{ext_part}"
            
        new_name = sanitize_filename(new_name)
        preview.append({
            'original': filename,
            'new': new_name
        })
    return preview

@app.route('/')
def index():
    """Render the main application UI."""
    return render_template('index.html')

@app.route('/files', methods=['POST'])
def list_files():
    """Retrieve all files in the given directory according to filter."""
    data = request.json
    directory = data.get('directory', '')
    ext_filter = data.get('extension_filter', '').strip().lower()
    
    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid directory path.'}), 400
        
    try:
        files = []
        for f in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, f)):
                if not ext_filter or f.lower().endswith(ext_filter):
                    files.append(f)
        return jsonify({'files': sorted(files)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    """Generate a live preview of filename changes without applying them."""
    data = request.json
    directory = data.get('directory', '')
    files = data.get('files', [])
    options = data.get('options', {})
    
    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid directory path.'}), 400
        
    preview_data = get_preview_names(directory, files, options)
    return jsonify({'preview': preview_data})

@app.route('/rename', methods=['POST'])
def rename():
    """Apply the rename logic based on the approved preview."""
    data = request.json
    directory = data.get('directory', '')
    preview_data = data.get('preview_data', [])
    allow_overwrite = data.get('allow_overwrite', False)
    
    if not directory or not os.path.isdir(directory):
        return jsonify({'error': 'Invalid directory path.'}), 400
        
    operations = []
    errors = []
    success_count = 0
    
    for item in preview_data:
        original = item['original']
        new_name = item['new']
        
        if original == new_name:
            continue
            
        old_path = os.path.join(directory, original)
        new_path = os.path.join(directory, new_name)
        
        # Safely checks
        if not os.path.exists(old_path):
            errors.append(f"File not found: {original}")
            continue
            
        if os.path.exists(new_path) and not allow_overwrite:
            errors.append(f"File already exists: {new_name}")
            continue
            
        try:
            os.rename(old_path, new_path)
            operations.append({
                'original_path': old_path,
                'new_path': new_path,
                'original_name': original,
                'new_name': new_name
            })
            success_count += 1
        except Exception as e:
            errors.append(f"Failed to rename {original}: {str(e)}")
            
    # Save the successful renames to our history for the 'Undo' function
    if operations:
        save_history(operations)
        
    return jsonify({
        'message': f"Successfully renamed {success_count} files.",
        'errors': errors
    })

@app.route('/undo', methods=['POST'])
def undo():
    """Revert the most recent batch renaming operations."""
    history = load_history()
    if not history:
        return jsonify({'error': 'No recent operations to undo.'}), 400
        
    # Get the last batch operation
    last_operation = history.pop()
    errors = []
    success_count = 0
    
    # Needs to be reverted in reverse (so we don't accidentally trample paths).
    for op in reversed(last_operation):
        try:
            if os.path.exists(op['new_path']):
                os.rename(op['new_path'], op['original_path'])
                success_count += 1
            else:
                errors.append(f"File not found: {op['new_path']}")
        except Exception as e:
            errors.append(f"Failed to undo {op['new_name']}: {str(e)}")
            
    # Explicitly rewrite the file without the popped history chunk
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)
        
    return jsonify({
        'message': f"Successfully undone {success_count} files.",
        'errors': errors
    })

if __name__ == '__main__':
    app.run(debug=True)
