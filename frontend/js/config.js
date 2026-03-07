// API Configuration
const API_CONFIG = {
    // Backend API URL - change this for production
    baseURL: window.location.hostname === 'localhost' 
        ? 'http://localhost:5000/api' 
        : '/api',
    
    // Polling interval for progress updates (ms)
    pollInterval: 500,
    
    // Request timeout (ms)
    timeout: 300000  // 5 minutes
};

// Export for use in other scripts
window.API_CONFIG = API_CONFIG;
