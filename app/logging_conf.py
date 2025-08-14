import logging
import sys
import json
from app.config import settings

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if hasattr(record, 'request'):
            log_record['request'] = record.request
        if hasattr(record, 'response'):
            log_record['response'] = record.response
            
        return json.dumps(log_record)

def setup_logging():
    # File handler for JSON logs
    file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
    file_handler.setFormatter(JsonFormatter())
    
    # Console handler for human-readable logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )

    # Uvicorn and other library log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
