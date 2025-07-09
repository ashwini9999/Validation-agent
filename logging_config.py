import logging
import sys
from datetime import datetime
import os

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Format the message
        formatted = super().format(record)
        
        # Add colors if we're outputting to terminal
        if sys.stdout.isatty():
            formatted = f"{level_color}{formatted}{reset_color}"
        
        return formatted

def setup_logging(log_level=logging.INFO):
    """Setup logging configuration for all agents"""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for persistent logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(f'logs/agent_logs_{timestamp}.log')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def get_agent_logger(agent_name):
    """Get a logger for a specific agent"""
    return logging.getLogger(f"Agent.{agent_name}")

# Agent-specific emojis for better visual identification
AGENT_EMOJIS = {
    'UIA': '🧠',      # User Interaction Agent
    'TSPA': '📋',     # Test Scenario Planning Agent  
    'BUVA': '🎨',     # Branding UX Validation Agent
    'PMEA': '🎭',     # Playwright Execution Agent
    'RAA': '📊',      # Result Analysis Agent
    'RCA': '📝'       # Reporting Communication Agent
}

def log_agent_start(agent_name, input_data):
    """Log when an agent starts processing"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.info(f"{emoji} {agent_name} STARTED")
    logger.debug(f"{emoji} {agent_name} Input: {input_data}")

def log_agent_thinking(agent_name, thought):
    """Log what an agent is thinking about"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.info(f"{emoji} {agent_name} THINKING: {thought}")

def log_llm_prompt(agent_name, prompt):
    """Log the prompt being sent to LLM"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.info(f"{emoji} {agent_name} SENDING TO LLM:")
    logger.debug(f"--- PROMPT START ---\n{prompt}\n--- PROMPT END ---")

def log_llm_response(agent_name, response):
    """Log the response received from LLM"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.info(f"{emoji} {agent_name} RECEIVED FROM LLM:")
    logger.debug(f"--- RESPONSE START ---\n{response}\n--- RESPONSE END ---")

def log_agent_complete(agent_name, output_data):
    """Log when an agent completes processing"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.info(f"{emoji} {agent_name} COMPLETED")
    logger.debug(f"{emoji} {agent_name} Output: {output_data}")

def log_agent_error(agent_name, error):
    """Log when an agent encounters an error"""
    logger = get_agent_logger(agent_name)
    emoji = AGENT_EMOJIS.get(agent_name, '🤖')
    logger.error(f"{emoji} {agent_name} ERROR: {error}")

def log_playwright_action(action_description):
    """Log playwright actions"""
    logger = get_agent_logger('PMEA')
    logger.info(f"🎭 PLAYWRIGHT ACTION: {action_description}")

def log_page_analysis(analysis_type, details):
    """Log page analysis details"""
    logger = get_agent_logger('PMEA')
    logger.info(f"🎭 PAGE ANALYSIS ({analysis_type}): {details}") 