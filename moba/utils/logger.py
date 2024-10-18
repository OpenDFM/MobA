import logging
import sys

sys.path.append('../..') 
from moba.utils.utils import print_with_color

class Logger:
    def __init__(self, name="task_logger", level=logging.INFO, file_path=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        print_with_color(f"Logger {name} is created.", "green")

    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)
    
    def debug(self, message):
        self.logger.debug(message)
