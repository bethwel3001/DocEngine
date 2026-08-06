document.addEventListener('DOMContentLoaded', () => {
    fetchDocuments();
});

let pendingConfirmAction = null;

/* Custom Confirmation Modal */
function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmModalTitle');
    const messageEl = document.getElementById('confirmModalMessage');

    if (!modal) return;

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;

    pendingConfirmAction = onConfirm;
    modal.style.display = 'flex';
}

function closeConfirmModal(confirmed) {
    const modal = document.getElementById('confirmModal');
    if (modal) modal.style.display = 'none';

    if (confirmed && typeof pendingConfirmAction === 'function') {
        pendingConfirmAction();
    }
    pendingConfirmAction = null;
}

/* Toast Notifications */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/* Document Management */
async function fetchDocuments() {
    try {
        const res = await fetch('/api/v1/documents');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderDocumentList(data.documents);
    } catch (err) {
        showToast('Failed to load active documents.', 'error');
    }
}

function renderDocumentList(documents) {
    const listContainer = document.getElementById('documentList');
    const clearAllBtn = document.getElementById('clearAllBtn');

    if (!listContainer) return;

    if (!documents || documents.length === 0) {
        listContainer.innerHTML = '<p class="empty-text">No documents uploaded yet.</p>';
        if (clearAllBtn) clearAllBtn.style.display = 'none';
        return;
    }

    if (clearAllBtn) clearAllBtn.style.display = 'inline-block';

    listContainer.innerHTML = documents.map(doc => `
        <div class="doc-item">
            <div>
                <span class="doc-name">${escapeHtml(doc.filename)}</span>
                <span class="doc-meta">(${doc.chunk_count} ${doc.chunk_count === 1 ? 'chunk' : 'chunks'})</span>
            </div>
            <button type="button" class="text-btn danger" onclick="confirmDeleteDocument('${doc.doc_id}', '${escapeHtml(doc.filename)}')">Delete</button>
        </div>
    `).join('');
}

async function uploadSelectedFile() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput || !fileInput.files[0]) {
        showToast('Please select a file to upload.', 'error');
        return;
    }

    const file = fileInput.files[0];
    const uploadBtn = document.getElementById('uploadBtn');

    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';

    try {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/v1/documents/upload', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Failed to upload document.');
        }

        showToast(`Document "${data.document.filename}" uploaded successfully.`, 'success');
        fileInput.value = '';
        fetchDocuments();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload Document';
    }
}

function confirmDeleteDocument(docId, filename) {
    showConfirmModal(
        'Delete Document',
        `Are you sure you want to delete "${filename}" from knowledge memory?`,
        () => executeDeleteDocument(docId, filename)
    );
}

async function executeDeleteDocument(docId, filename) {
    try {
        const res = await fetch(`/api/v1/documents/${docId}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Failed to delete document');

        showToast(`Deleted "${filename}".`, 'success');
        fetchDocuments();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function requestClearAll() {
    showConfirmModal(
        'Clear Knowledge Base',
        'Are you sure you want to clear all uploaded documents and reset vector memory?',
        executeClearAll
    );
}

async function executeClearAll() {
    try {
        const res = await fetch('/api/v1/documents', {
            method: 'DELETE'
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Failed to clear documents');

        showToast('All documents cleared.', 'success');
        fetchDocuments();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

/* Query Execution */
async function submitQuery() {
    const queryInput = document.getElementById('queryInput');
    const prompt = queryInput ? queryInput.value.trim() : '';

    if (!prompt) {
        showToast('Please enter a question.', 'error');
        return;
    }

    const responseArea = document.getElementById('responseArea');
    const statusMessage = document.getElementById('statusMessage');
    const responseBody = document.getElementById('responseBody');
    const answerText = document.getElementById('answerText');
    const citationsWrapper = document.getElementById('citationsWrapper');
    const citationsList = document.getElementById('citationsList');
    const queryBtn = document.getElementById('queryBtn');

    if (responseArea) responseArea.style.display = 'block';
    if (statusMessage) {
        statusMessage.className = 'status-message info';
        statusMessage.textContent = 'Processing query...';
        statusMessage.style.display = 'block';
    }
    if (responseBody) responseBody.style.display = 'none';

    queryBtn.disabled = true;

    try {
        const res = await fetch('/api/v1/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, top_k: 3 })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Query processing failed.');
        }

        if (statusMessage) statusMessage.style.display = 'none';
        if (responseBody) responseBody.style.display = 'block';
        if (answerText) answerText.textContent = data.answer;

        if (citationsWrapper && citationsList) {
            if (data.citations && data.citations.length > 0) {
                citationsWrapper.style.display = 'block';
                citationsList.innerHTML = data.citations.map(c => `
                    <li class="citation-item">• ${escapeHtml(c.filename)} (Chunk ${c.chunk_id})</li>
                `).join('');
            } else {
                citationsWrapper.style.display = 'none';
            }
        }
    } catch (err) {
        if (statusMessage) {
            statusMessage.className = 'status-message error';
            statusMessage.textContent = err.message;
            statusMessage.style.display = 'block';
        }
        showToast(err.message, 'error');
    } finally {
        queryBtn.disabled = false;
    }
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
