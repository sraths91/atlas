"""
Atlas - Enhanced system monitor for Turing Atlass on macOS
"""

__version__ = "1.0.0"

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
