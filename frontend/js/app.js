// Auto Quran Frontend Application Logic

// Global state
let pipelineState = {
    image_path: null,
    video_path: null,
    text_overlay_path: null,
    final_video_path: null
};

let isRunning = false;
let progressInterval = null;

// Utility Functions
function showNotification(title, message, type = 'info') {
    const notification = document.getElementById('notification');
    const titleEl = document.getElementById('notification-title');
    const messageEl = document.getElementById('notification-message');
    
    notification.className = 'notification show ' + type;
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

function showMessage(stepId, message, type = 'info') {
    const messageEl = document.getElementById(`message-${stepId}`);
    messageEl.className = `message show ${type}`;
    messageEl.textContent = message;
}

function hideMessage(stepId) {
    const messageEl = document.getElementById(`message-${stepId}`);
    messageEl.classList.remove('show');
}

function setStatus(stepId, status) {
    const statusEl = document.getElementById(`status-${stepId}`);
    statusEl.className = `step-status status-${status}`;
    statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

function showPreview(stepId, url, type = 'image') {
    const previewBox = document.getElementById(`preview-${stepId}`);
    const previewEl = document.getElementById(`${stepId}-preview`);
    
    if (type === 'image' || type === 'video') {
        previewEl.src = url;
        previewBox.classList.add('show');
    }
}

function setButtonState(buttonId, disabled, text = null) {
    const button = document.getElementById(buttonId);
    button.disabled = disabled;
    if (text) {
        const originalText = button.getAttribute('data-original-text') || button.textContent;
        if (!button.getAttribute('data-original-text')) {
            button.setAttribute('data-original-text', originalText);
        }
        button.textContent = text;
    } else if (button.getAttribute('data-original-text')) {
        button.textContent = button.getAttribute('data-original-text');
    }
}

function showLoader(buttonId) {
    const button = document.getElementById(buttonId);
    const loader = document.createElement('span');
    loader.className = 'loader';
    loader.id = `loader-${buttonId}`;
    button.appendChild(loader);
}

function hideLoader(buttonId) {
    const loader = document.getElementById(`loader-${buttonId}`);
    if (loader) loader.remove();
}

// Progress Monitoring
function startProgressMonitoring() {
    if (progressInterval) return;
    
    const progressWrap = document.getElementById('pipeline-progress-wrap');
    progressWrap.style.display = 'block';
    
    progressInterval = setInterval(async () => {
        try {
            const progress = await api.getProgress();
            updateProgress(progress);
        } catch (error) {
            console.error('Failed to fetch progress:', error);
        }
    }, API_CONFIG.pollInterval);
}

function stopProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgress(progress) {
    if (!progress.active) {
        stopProgressMonitoring();
        return;
    }
    
    const stepEl = document.getElementById('progress-step');
    const percentEl = document.getElementById('progress-percent');
    const fillEl = document.getElementById('progress-fill');
    
    stepEl.textContent = progress.overall_message || 'Processing...';
    percentEl.textContent = `${Math.round(progress.overall_percent)}%`;
    fillEl.style.width = `${progress.overall_percent}%`;
    
    if (progress.overall_percent >= 100) {
        fillEl.classList.add('success');
    }
}

// Step Functions
async function downloadImage() {
    const keyword = document.getElementById('image-keyword').value || 'nature';
    
    setButtonState('btn-download-image', true, 'Downloading...');
    setStatus('image', 'processing');
    hideMessage('image');
    showLoader('btn-download-image');
    
    try {
        startProgressMonitoring();
        const result = await api.downloadImage(keyword);
        
        if (result.success) {
            pipelineState.image_path = result.image_path;
            setStatus('image', 'completed');
            showMessage('image', '✅ Image downloaded successfully!', 'success');
            
            const previewURL = api.getPreviewURL(result.image_path);
            showPreview('image', previewURL, 'image');
            
            // Enable next steps
            updateButtonStates();
        }
    } catch (error) {
        setStatus('image', 'error');
        showMessage('image', `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonState('btn-download-image', false);
        hideLoader('btn-download-image');
        stopProgressMonitoring();
    }
}

async function downloadVideo() {
    const channelUrl = document.getElementById('channel-url').value;
    const keyword = document.getElementById('video-keyword').value || 'سورة';
    
    if (!channelUrl) {
        showMessage('video', '⚠️ Please enter a YouTube channel URL', 'error');
        return;
    }
    
    setButtonState('btn-download-video', true, 'Downloading...');
    setStatus('video', 'processing');
    hideMessage('video');
    showLoader('btn-download-video');
    
    try {
        startProgressMonitoring();
        const result = await api.downloadVideo(channelUrl, keyword);
        
        if (result.success) {
            pipelineState.video_path = result.video_path;
            setStatus('video', 'completed');
            showMessage('video', `✅ Video downloaded: ${result.video_title || 'Success'}`, 'success');
            
            const previewURL = api.getPreviewURL(result.video_path);
            showPreview('video', previewURL, 'video');
            
            // Enable next steps
            updateButtonStates();
        }
    } catch (error) {
        setStatus('video', 'error');
        showMessage('video', `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonState('btn-download-video', false);
        hideLoader('btn-download-video');
        stopProgressMonitoring();
    }
}

async function extractText() {
    setButtonState('btn-extract-text', true, 'Extracting...');
    setStatus('text', 'processing');
    hideMessage('text');
    showLoader('btn-extract-text');
    
    try {
        startProgressMonitoring();
        const result = await api.extractText(pipelineState.video_path);
        
        if (result.success) {
            pipelineState.text_overlay_path = result.overlay_path;
            setStatus('text', 'completed');
            showMessage('text', '✅ Text overlay extracted!', 'success');
            
            const previewURL = api.getPreviewURL(result.overlay_path);
            showPreview('text', previewURL, 'image');
            
            // Enable next steps
            updateButtonStates();
        }
    } catch (error) {
        setStatus('text', 'error');
        showMessage('text', `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonState('btn-extract-text', false);
        hideLoader('btn-extract-text');
        stopProgressMonitoring();
    }
}

async function createFinalVideo() {
    setButtonState('btn-create-final', true, 'Creating...');
    setStatus('final', 'processing');
    hideMessage('final');
    showLoader('btn-create-final');
    
    try {
        startProgressMonitoring();
        const result = await api.createFinalVideo(
            pipelineState.image_path,
            pipelineState.video_path,
            pipelineState.text_overlay_path
        );
        
        if (result.success) {
            pipelineState.final_video_path = result.final_video_path;
            setStatus('final', 'completed');
            showMessage('final', '✅ Final video created!', 'success');
            
            const previewURL = api.getPreviewURL(result.final_video_path);
            showPreview('final', previewURL, 'video');
            
            // Enable next steps
            updateButtonStates();
        }
    } catch (error) {
        setStatus('final', 'error');
        showMessage('final', `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonState('btn-create-final', false);
        hideLoader('btn-create-final');
        stopProgressMonitoring();
    }
}

async function postToInstagram() {
    const caption = document.getElementById('instagram-caption').value;
    
    setButtonState('btn-post-instagram', true, 'Posting...');
    setStatus('post', 'processing');
    hideMessage('post');
    showLoader('btn-post-instagram');
    
    try {
        startProgressMonitoring();
        const result = await api.postToInstagram(pipelineState.final_video_path, caption);
        
        if (result.success) {
            setStatus('post', 'completed');
            showMessage('post', '✅ Posted to Instagram successfully!', 'success');
            showNotification('Success!', 'Video posted to Instagram', 'success');
        }
    } catch (error) {
        setStatus('post', 'error');
        showMessage('post', `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonState('btn-post-instagram', false);
        hideLoader('btn-post-instagram');
        stopProgressMonitoring();
    }
}

// Full Pipeline
async function runFullPipeline() {
    if (isRunning) return;
    
    isRunning = true;
    setButtonState('btn-full-pipeline', true, '🚀 Running...');
    setButtonState('btn-stop-pipeline', false);
    
    const resultsDiv = document.getElementById('pipeline-results');
    resultsDiv.style.display = 'block';
    
    try {
        startProgressMonitoring();
        
        // Step 1: Download Image
        const keyword = document.getElementById('image-keyword').value || 'nature';
        const imageResult = await api.downloadImage(keyword);
        if (imageResult.success) {
            pipelineState.image_path = imageResult.image_path;
            document.getElementById('result-image').textContent = `📷 Image: ✅ Downloaded`;
            setStatus('image', 'completed');
        }
        
        // Step 2: Download Video
        const channelUrl = document.getElementById('channel-url').value;
        const videoKeyword = document.getElementById('video-keyword').value || 'سورة';
        const videoResult = await api.downloadVideo(channelUrl, videoKeyword);
        if (videoResult.success) {
            pipelineState.video_path = videoResult.video_path;
            document.getElementById('result-video').textContent = `🎥 Video: ✅ ${videoResult.video_title || 'Downloaded'}`;
            setStatus('video', 'completed');
        }
        
        // Step 3: Extract Text (optional)
        const textResult = await api.extractText(pipelineState.video_path);
        if (textResult.success) {
            pipelineState.text_overlay_path = textResult.overlay_path;
            setStatus('text', 'completed');
        }
        
        // Step 4: Create Final Video
        const finalResult = await api.createFinalVideo(
            pipelineState.image_path,
            pipelineState.video_path,
            pipelineState.text_overlay_path
        );
        if (finalResult.success) {
            pipelineState.final_video_path = finalResult.final_video_path;
            document.getElementById('result-final').textContent = `🎬 Final: ✅ Created`;
            setStatus('final', 'completed');
            
            const previewURL = api.getPreviewURL(finalResult.final_video_path);
            showPreview('final', previewURL, 'video');
        }
        
        // Step 5: Post to Instagram (if enabled)
        const autoPost = document.getElementById('auto-post-toggle').checked;
        if (autoPost) {
            const caption = document.getElementById('instagram-caption').value;
            const postResult = await api.postToInstagram(pipelineState.final_video_path, caption);
            if (postResult.success) {
                setStatus('post', 'completed');
                showNotification('Pipeline Complete!', 'Video posted to Instagram', 'success');
            }
        } else {
            showNotification('Pipeline Complete!', 'Video ready for posting', 'success');
        }
        
        updateButtonStates();
        
    } catch (error) {
        showNotification('Pipeline Failed', error.message, 'error');
        console.error('Pipeline error:', error);
    } finally {
        isRunning = false;
        setButtonState('btn-full-pipeline', false);
        setButtonState('btn-stop-pipeline', true);
        stopProgressMonitoring();
    }
}

async function stopPipeline() {
    try {
        await api.stopPipeline();
        isRunning = false;
        showNotification('Stopped', 'Pipeline stopped by user', 'info');
    } catch (error) {
        console.error('Failed to stop pipeline:', error);
    }
}

// Settings
async function loadSettings() {
    try {
        const settings = await api.getSettings();
        
        document.getElementById('channel-url').value = settings.default_channel_url || '';
        document.getElementById('video-keyword').value = settings.default_keyword || '';
        document.getElementById('instagram-caption').value = settings.default_caption || '';
        
        showNotification('Settings Loaded', 'Default settings applied', 'success');
    } catch (error) {
        showNotification('Error', 'Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        const settings = {
            default_channel_url: document.getElementById('channel-url').value,
            default_keyword: document.getElementById('video-keyword').value,
            default_caption: document.getElementById('instagram-caption').value
        };
        
        await api.updateSettings(settings);
        showNotification('Settings Saved', 'Your settings have been saved', 'success');
    } catch (error) {
        showNotification('Error', 'Failed to save settings', 'error');
    }
}

function resetAll() {
    if (!confirm('Are you sure you want to reset all steps?')) return;
    
    pipelineState = {
        image_path: null,
        video_path: null,
        text_overlay_path: null,
        final_video_path: null
    };
    
    // Reset all statuses
    ['image', 'video', 'text', 'final', 'post'].forEach(step => {
        setStatus(step, 'pending');
        hideMessage(step);
    });
    
    // Hide all previews
    document.querySelectorAll('.preview-box').forEach(box => {
        box.classList.remove('show');
    });
    
    // Hide results
    document.getElementById('pipeline-results').style.display = 'none';
    document.getElementById('pipeline-progress-wrap').style.display = 'none';
    
    updateButtonStates();
    showNotification('Reset', 'All steps have been reset', 'info');
}

function updateButtonStates() {
    // Enable buttons based on available data
    const hasVideo = pipelineState.video_path !== null;
    const hasImage = pipelineState.image_path !== null;
    const hasOverlay = pipelineState.text_overlay_path !== null;
    const hasFinal = pipelineState.final_video_path !== null;
    
    document.getElementById('btn-extract-text').disabled = !hasVideo;
    document.getElementById('btn-create-final').disabled = !hasVideo || !hasImage;
    document.getElementById('btn-post-instagram').disabled = !hasFinal;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Check backend health
    try {
        const health = await api.healthCheck();
        console.log('Backend health:', health);
    } catch (error) {
        showNotification('Backend Error', 'Cannot connect to backend server', 'error');
    }
    
    // Load initial settings
    await loadSettings();
    
    // Initial button states
    updateButtonStates();
});
