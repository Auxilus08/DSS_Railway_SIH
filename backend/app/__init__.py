"""
Railway Traffic Management System with AI Integration
Production-ready railway optimization and management system
"""

__version__ = "2.0.0"  # Updated with AI integration

# AI Integration availability check
try:
    from .railway_optimization import OptimizationEngine
    from .railway_adapter import RailwayAIAdapter
    from .ai_config import AIConfig
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning(f"AI modules not available: {e}")

__all__ = [
    '__version__',
    'AI_AVAILABLE'
]