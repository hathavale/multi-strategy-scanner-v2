"""
Configuration module for Multi-Strategy Options Scanner.
Loads environment variables and provides configuration settings.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Alpha Vantage API - check both naming conventions
    ALPHAVANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY') or os.getenv('ALPHAVANTAGE_API_KEY')
    if not ALPHAVANTAGE_API_KEY:
        raise ValueError("ALPHA_VANTAGE_API_KEY or ALPHAVANTAGE_API_KEY environment variable is required")
    
    # Application Settings
    MAX_SYMBOLS_PER_SCAN = int(os.getenv('MAX_SYMBOLS_PER_SCAN', 10))
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))
    
    # Rate Limiting
    ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'True').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '')
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        pass


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    @staticmethod
    def init_app(app):
        """Production-specific initialization."""
        Config.init_app(app)
        
        # Log to stderr
        import logging
        from logging import StreamHandler
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Use separate test database
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', Config.DATABASE_URL)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    Get configuration object based on environment.
    
    Args:
        env: Environment name ('development', 'production', 'testing')
             If None, uses FLASK_ENV environment variable
    
    Returns:
        Config class
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])


# Convenience access to current configuration
current_config = get_config()


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration Test")
    print("=" * 50)
    print(f"Environment: {current_config.FLASK_ENV}")
    print(f"Debug Mode: {current_config.DEBUG}")
    print(f"Port: {current_config.PORT}")
    print(f"Database URL: {current_config.DATABASE_URL[:30]}...")  # Don't print full URL
    print(f"API Key Set: {'Yes' if current_config.ALPHAVANTAGE_API_KEY else 'No'}")
    print(f"Max Symbols: {current_config.MAX_SYMBOLS_PER_SCAN}")
    print(f"Rate Limiting: {'Enabled' if current_config.ENABLE_RATE_LIMITING else 'Disabled'}")
