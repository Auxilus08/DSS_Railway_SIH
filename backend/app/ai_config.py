"""
AI Integration Configuration
Manages settings for AI optimization integration with the railway system
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AIConfig:
    """Configuration class for AI integration settings"""
    
    # Core AI Settings
    ENABLE_AI_OPTIMIZATION = os.getenv('ENABLE_AI_OPTIMIZATION', 'true').lower() == 'true'
    
    # RL Training Settings
    TRAIN_RL_ON_STARTUP = os.getenv('TRAIN_RL_ON_STARTUP', 'false').lower() == 'true'
    RL_TRAINING_EPISODES = int(os.getenv('RL_TRAINING_EPISODES', '300'))
    
    # Performance Settings
    MAX_OPTIMIZATION_TIMEOUT = float(os.getenv('MAX_OPTIMIZATION_TIMEOUT', '15.0'))
    MAX_CONCURRENT_OPTIMIZATIONS = int(os.getenv('MAX_CONCURRENT_OPTIMIZATIONS', '5'))
    
    # Integration Settings
    AI_CONFIDENCE_THRESHOLD = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.7'))
    FALLBACK_TO_MANUAL = os.getenv('FALLBACK_TO_MANUAL', 'true').lower() == 'true'
    
    # Data Mapping Settings
    CARGO_VALUE_PER_TON = float(os.getenv('CARGO_VALUE_PER_TON', '500.0'))
    DEFAULT_PASSENGER_COUNT = int(os.getenv('DEFAULT_PASSENGER_COUNT', '150'))
    
    # Logging Settings
    AI_LOG_LEVEL = os.getenv('AI_LOG_LEVEL', 'INFO')
    ENABLE_AI_METRICS = os.getenv('ENABLE_AI_METRICS', 'true').lower() == 'true'
    
    # Safety Settings
    REQUIRE_HUMAN_APPROVAL = os.getenv('REQUIRE_HUMAN_APPROVAL', 'false').lower() == 'true'
    AUTO_EXECUTE_THRESHOLD = float(os.getenv('AUTO_EXECUTE_THRESHOLD', '0.9'))
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            'ai_enabled': cls.ENABLE_AI_OPTIMIZATION,
            'rl_training_on_startup': cls.TRAIN_RL_ON_STARTUP,
            'rl_episodes': cls.RL_TRAINING_EPISODES,
            'max_timeout': cls.MAX_OPTIMIZATION_TIMEOUT,
            'confidence_threshold': cls.AI_CONFIDENCE_THRESHOLD,
            'fallback_enabled': cls.FALLBACK_TO_MANUAL,
            'cargo_value_per_ton': cls.CARGO_VALUE_PER_TON,
            'default_passengers': cls.DEFAULT_PASSENGER_COUNT,
            'require_approval': cls.REQUIRE_HUMAN_APPROVAL,
            'auto_execute_threshold': cls.AUTO_EXECUTE_THRESHOLD
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration values"""
        try:
            # Validate numeric ranges
            assert 0.0 <= cls.AI_CONFIDENCE_THRESHOLD <= 1.0, "AI confidence threshold must be between 0.0 and 1.0"
            assert cls.MAX_OPTIMIZATION_TIMEOUT > 0, "Optimization timeout must be positive"
            assert cls.RL_TRAINING_EPISODES > 0, "RL training episodes must be positive"
            assert cls.CARGO_VALUE_PER_TON >= 0, "Cargo value per ton must be non-negative"
            assert cls.DEFAULT_PASSENGER_COUNT >= 0, "Default passenger count must be non-negative"
            assert 0.0 <= cls.AUTO_EXECUTE_THRESHOLD <= 1.0, "Auto execute threshold must be between 0.0 and 1.0"
            
            logger.info("AI configuration validation successful")
            return True
            
        except AssertionError as e:
            logger.error(f"AI configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during AI configuration validation: {e}")
            return False
    
    @classmethod
    def log_config(cls):
        """Log current configuration (for debugging)"""
        config = cls.get_config_dict()
        logger.info("AI Integration Configuration:")
        for key, value in config.items():
            logger.info(f"  {key}: {value}")


# Initialize configuration validation on import
if not AIConfig.validate_config():
    logger.warning("AI configuration validation failed - some features may not work correctly")