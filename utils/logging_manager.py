import logging
import sys

def setup_logging():
    """Configure and return the root logger"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add FileHandler here if needed
        ]
    )
    return logging.getLogger("AI_Tutor")

class LoggingManager:
    def __init__(self):
        self.logger = logging.getLogger("AI_Tutor")
    
    def log(self, message):
        self.logger.info(message)
