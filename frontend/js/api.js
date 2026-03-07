// API Client for Auto Quran Backend

class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Request Failed:', error);
            throw error;
        }
    }

    // Health check
    async healthCheck() {
        return this.request('/health');
    }

    // Settings
    async getSettings() {
        return this.request('/settings');
    }

    async updateSettings(settings) {
        return this.request('/settings', {
            method: 'POST',
            body: settings
        });
    }

    async resetSettings() {
        return this.request('/settings/reset', { method: 'POST' });
    }

    // Progress
    async getProgress() {
        return this.request('/progress');
    }

    // Pipeline state
    async getPipelineState() {
        return this.request('/pipeline/state');
    }

    async stopPipeline() {
        return this.request('/pipeline/stop', { method: 'POST' });
    }

    // Operations
    async downloadImage(keyword = 'nature') {
        return this.request('/download-image', {
            method: 'POST',
            body: { keyword }
        });
    }

    async downloadVideo(channelUrl, keyword = 'سورة') {
        return this.request('/download-video', {
            method: 'POST',
            body: { channel_url: channelUrl, keyword }
        });
    }

    async extractText(videoPath = null) {
        return this.request('/extract-text', {
            method: 'POST',
            body: { video_path: videoPath }
        });
    }

    async createFinalVideo(imagePath = null, videoPath = null, overlayPath = null) {
        return this.request('/create-final-video', {
            method: 'POST',
            body: { 
                image_path: imagePath, 
                video_path: videoPath, 
                overlay_path: overlayPath 
            }
        });
    }

    async postToInstagram(videoPath = null, caption = null) {
        return this.request('/post-to-instagram', {
            method: 'POST',
            body: { video_path: videoPath, caption }
        });
    }

    // Preview file URL
    getPreviewURL(filename) {
        if (!filename) return null;
        // Extract just the filename from path
        const name = filename.split(/[/\\]/).pop();
        return `${this.baseURL}/preview/${name}`;
    }
}

// Create global API client instance
window.api = new APIClient(API_CONFIG.baseURL);
