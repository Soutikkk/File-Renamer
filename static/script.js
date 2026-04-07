document.addEventListener('DOMContentLoaded', () => {
    let currentFiles = [];
    let currentPreview = [];

    // DOM Elements
    const dirInput = document.getElementById('directory');
    const loadBtn = document.getElementById('loadFilesBtn');
    const extFilter = document.getElementById('extFilter');
    const prefixInput = document.getElementById('prefix');
    const suffixInput = document.getElementById('suffix');
    const replaceTarget = document.getElementById('replaceTarget');
    const replaceWith = document.getElementById('replaceWith');
    const removeText = document.getElementById('removeText');
    const numberingCheck = document.getElementById('numbering');
    const allowOverwrite = document.getElementById('allowOverwrite');
    
    const previewBody = document.getElementById('previewBody');
    const fileCount = document.getElementById('fileCount');
    const renameBtn = document.getElementById('renameBtn');
    const undoBtn = document.getElementById('undoBtn');
    
    const optionInputs = document.querySelectorAll('.option-input');
    
    const confirmModal = document.getElementById('confirmModal');
    const cancelBtn = document.getElementById('cancelRenameBtn');
    const proceedBtn = document.getElementById('proceedRenameBtn');
    const confirmCountSpan = document.getElementById('confirmCount');
    
    // Core Functions
    const showToast = (msg, isError = false) => {
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.style.borderColor = isError ? 'var(--danger)' : 'var(--success)';
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    };

    const loadFiles = async () => {
        const dir = dirInput.value.trim();
        if (!dir) {
            showToast('Please enter a directory path', true);
            return;
        }
        
        try {
            const res = await fetch('/files', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: dir,
                    extension_filter: extFilter.value
                })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Failed to load files');
            
            currentFiles = data.files;
            fileCount.textContent = `${currentFiles.length} files`;
            updatePreview();
        } catch (err) {
            showToast(err.message, true);
        }
    };

    const updatePreview = async () => {
        if (currentFiles.length === 0) {
            previewBody.innerHTML = '<tr><td colspan="2" class="empty-state">No files to preview</td></tr>';
            renameBtn.disabled = true;
            return;
        }

        const options = {
            prefix: prefixInput.value,
            suffix: suffixInput.value,
            replace_target: replaceTarget.value,
            replace_with: replaceWith.value,
            remove_text: removeText.value,
            numbering: numberingCheck.checked
        };

        try {
            const res = await fetch('/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: dirInput.value.trim(),
                    files: currentFiles,
                    options: options
                })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Preview failed');
            
            currentPreview = data.preview;
            renderPreviewTable();
        } catch (err) {
            showToast(err.message, true);
        }
    };

    const renderPreviewTable = () => {
        previewBody.innerHTML = '';
        let hasChanges = false;
        
        currentPreview.forEach(item => {
            const tr = document.createElement('tr');
            const changed = item.original !== item.new;
            if (changed) hasChanges = true;
            
            tr.innerHTML = `
                <td>${item.original}</td>
                <td class="${changed ? 'changed' : ''}">${item.new}</td>
            `;
            previewBody.appendChild(tr);
        });
        
        renameBtn.disabled = !hasChanges;
    };

    const applyRename = async () => {
        confirmModal.classList.remove('active');
        try {
            const res = await fetch('/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: dirInput.value.trim(),
                    preview_data: currentPreview,
                    allow_overwrite: allowOverwrite.checked
                })
            });
            const data = await res.json();
            
            if (data.errors && data.errors.length > 0) {
                console.error("Errors:", data.errors);
                showToast(`Issues occurred. Renamed partially. Check console.`, true);
            } else if (res.ok) {
                showToast(data.message);
            } else {
                throw new Error(data.error);
            }
            
            // Reload files
            loadFiles();
            
            // Clear inputs
            optionInputs.forEach(input => {
                if(input.type === 'checkbox') input.checked = false;
                else input.value = '';
            });
            
        } catch (err) {
            showToast(err.message, true);
        }
    };

    const undoLast = async () => {
        try {
            const res = await fetch('/undo', { method: 'POST' });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Undo failed');
            if (data.errors && data.errors.length > 0) {
                showToast(`Partial undo. Check console.`, true);
                console.error("Errors:", data.errors);
            } else {
                showToast(data.message);
            }
            // Reload files
            if(dirInput.value.trim()) loadFiles();
            else updatePreview();
        } catch (err) {
            showToast(err.message, true);
        }
    };

    // Event Listeners
    loadBtn.addEventListener('click', loadFiles);
    dirInput.addEventListener('keypress', (e) => e.key === 'Enter' && loadFiles());
    extFilter.addEventListener('change', loadFiles);
    
    optionInputs.forEach(input => {
        input.addEventListener('input', updatePreview);
        input.addEventListener('change', updatePreview);
    });

    renameBtn.addEventListener('click', () => {
        const changedCount = currentPreview.filter(i => i.original !== i.new).length;
        confirmCountSpan.textContent = changedCount;
        confirmModal.classList.add('active');
    });

    cancelBtn.addEventListener('click', () => confirmModal.classList.remove('active'));
    proceedBtn.addEventListener('click', applyRename);
    undoBtn.addEventListener('click', undoLast);
});
