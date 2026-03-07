import os
from pathlib import Path


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Directory paths
    BASE_DIR = Path(__file__).parent
    ASSETS_DIR = BASE_DIR / 'assets'
    OUTPUT_DIR = BASE_DIR / 'output'
    
    # Unsplash API
    UNSPLASH_API_KEY = os.environ.get('UNSPLASH_API_KEY', '')
    
    # Instagram credentials
    INSTA_USERNAME = os.environ.get('INSTA_USERNAME', '')
    INSTA_PASSWORD = os.environ.get('INSTA_PASSWORD', '')
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')
    
    # File upload
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
    
    @staticmethod
    def init_app(app):
        """Initialize application directories"""
        Config.ASSETS_DIR.mkdir(exist_ok=True)
        Config.OUTPUT_DIR.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        pass


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
