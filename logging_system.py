from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from threading import Lock, Thread, current_thread
from queue import Queue
import traceback
import json
import os


# ==================== Enums ====================

class LogLevel(Enum):
    """Log levels in order of severity"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    FATAL = 4
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


# ==================== Core Models ====================

class LogRecord:
    """Represents a single log record"""
    
    def __init__(self, logger_name: str, level: LogLevel, message: str,
                 timestamp: datetime = None, thread_name: str = None,
                 exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None):
        self.logger_name = logger_name
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.thread_name = thread_name or current_thread().name
        self.exception = exception
        self.exception_info = None
        
        if exception:
            self.exception_info = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        
        self.extra = extra or {}
    
    def __repr__(self) -> str:
        return f"LogRecord({self.level.name}, {self.message})"


# ==================== Strategy Pattern: Log Formatters ====================

class LogFormatter(ABC):
    """Abstract base class for log formatters"""
    
    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Format a log record into a string"""
        pass


class SimpleFormatter(LogFormatter):
    """Simple text formatter: [LEVEL] message"""
    
    def format(self, record: LogRecord) -> str:
        return f"[{record.level.name}] {record.message}"


class DetailedFormatter(LogFormatter):
    """Detailed text formatter with timestamp and thread"""
    
    def __init__(self, date_format: str = "%Y-%m-%d %H:%M:%S"):
        self._date_format = date_format
    
    def format(self, record: LogRecord) -> str:
        timestamp = record.timestamp.strftime(self._date_format)
        parts = [
            f"{timestamp}",
            f"[{record.level.name}]",
            f"[{record.logger_name}]",
            f"[{record.thread_name}]",
            f"{record.message}"
        ]
        
        formatted = " ".join(parts)
        
        if record.exception_info:
            formatted += f"\n{record.exception_info}"
        
        return formatted


class JSONFormatter(LogFormatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: LogRecord) -> str:
        log_dict = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "logger": record.logger_name,
            "thread": record.thread_name,
            "message": record.message
        }
        
        if record.exception:
            log_dict["exception"] = {
                "type": type(record.exception).__name__,
                "message": str(record.exception),
                "traceback": record.exception_info
            }
        
        if record.extra:
            log_dict["extra"] = record.extra
        
        return json.dumps(log_dict)


class CustomFormatter(LogFormatter):
    """Custom formatter with user-defined template"""
    
    def __init__(self, template: str = "{timestamp} [{level}] {logger}: {message}",
                 date_format: str = "%Y-%m-%d %H:%M:%S"):
        self._template = template
        self._date_format = date_format
    
    def format(self, record: LogRecord) -> str:
        context = {
            "timestamp": record.timestamp.strftime(self._date_format),
            "level": record.level.name,
            "logger": record.logger_name,
            "thread": record.thread_name,
            "message": record.message
        }
        
        # Add extra fields
        context.update(record.extra)
        
        formatted = self._template.format(**context)
        
        if record.exception_info:
            formatted += f"\n{record.exception_info}"
        
        return formatted


# ==================== Strategy Pattern: Log Destinations ====================

class LogHandler(ABC):
    """Abstract base class for log handlers (destinations)"""
    
    def __init__(self, level: LogLevel = LogLevel.DEBUG, 
                 formatter: Optional[LogFormatter] = None):
        self._level = level
        self._formatter = formatter or SimpleFormatter()
        self._lock = Lock()
    
    def get_level(self) -> LogLevel:
        return self._level
    
    def set_level(self, level: LogLevel) -> None:
        self._level = level
    
    def get_formatter(self) -> LogFormatter:
        return self._formatter
    
    def set_formatter(self, formatter: LogFormatter) -> None:
        self._formatter = formatter
    
    def handle(self, record: LogRecord) -> None:
        """Handle a log record if it meets the level threshold"""
        if record.level >= self._level:
            formatted = self._formatter.format(record)
            self.emit(formatted, record)
    
    @abstractmethod
    def emit(self, message: str, record: LogRecord) -> None:
        """Emit the formatted log message"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close and cleanup handler resources"""
        pass


class ConsoleHandler(LogHandler):
    """Outputs logs to console (stdout/stderr)"""
    
    def __init__(self, level: LogLevel = LogLevel.DEBUG,
                 formatter: Optional[LogFormatter] = None,
                 use_colors: bool = True):
        super().__init__(level, formatter)
        self._use_colors = use_colors
        
        # ANSI color codes
        self._colors = {
            LogLevel.DEBUG: '\033[36m',      # Cyan
            LogLevel.INFO: '\033[32m',       # Green
            LogLevel.WARNING: '\033[33m',    # Yellow
            LogLevel.ERROR: '\033[31m',      # Red
            LogLevel.FATAL: '\033[35m'       # Magenta
        }
        self._reset = '\033[0m'
    
    def emit(self, message: str, record: LogRecord) -> None:
        with self._lock:
            if self._use_colors:
                color = self._colors.get(record.level, '')
                print(f"{color}{message}{self._reset}")
            else:
                print(message)
    
    def close(self) -> None:
        pass


class FileHandler(LogHandler):
    """Outputs logs to a file"""
    
    def __init__(self, filename: str, level: LogLevel = LogLevel.DEBUG,
                 formatter: Optional[LogFormatter] = None,
                 mode: str = 'a', encoding: str = 'utf-8'):
        super().__init__(level, formatter)
        self._filename = filename
        self._mode = mode
        self._encoding = encoding
        self._file = None
        self._open_file()
    
    def _open_file(self) -> None:
        """Open the log file"""
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(self._filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            self._file = open(self._filename, self._mode, encoding=self._encoding)
        except Exception as e:
            print(f"Failed to open log file {self._filename}: {e}")
    
    def emit(self, message: str, record: LogRecord) -> None:
        if not self._file:
            return
        
        with self._lock:
            try:
                self._file.write(message + '\n')
                self._file.flush()
            except Exception as e:
                print(f"Failed to write to log file: {e}")
    
    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class RotatingFileHandler(LogHandler):
    """File handler with rotation based on size"""
    
    def __init__(self, filename: str, max_bytes: int = 10_000_000,
                 backup_count: int = 5, level: LogLevel = LogLevel.DEBUG,
                 formatter: Optional[LogFormatter] = None):
        super().__init__(level, formatter)
        self._filename = filename
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._file = None
        self._current_size = 0
        self._open_file()
    
    def _open_file(self) -> None:
        """Open the log file"""
        try:
            directory = os.path.dirname(self._filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            self._file = open(self._filename, 'a', encoding='utf-8')
            
            # Get current file size
            if os.path.exists(self._filename):
                self._current_size = os.path.getsize(self._filename)
        except Exception as e:
            print(f"Failed to open log file {self._filename}: {e}")
    
    def _rotate(self) -> None:
        """Rotate log files"""
        if self._file:
            self._file.close()
        
        # Rotate backup files
        for i in range(self._backup_count - 1, 0, -1):
            src = f"{self._filename}.{i}"
            dst = f"{self._filename}.{i + 1}"
            
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        
        # Rename current file to .1
        if os.path.exists(self._filename):
            os.rename(self._filename, f"{self._filename}.1")
        
        # Open new file
        self._current_size = 0
        self._open_file()
    
    def emit(self, message: str, record: LogRecord) -> None:
        if not self._file:
            return
        
        with self._lock:
            try:
                message_bytes = len(message.encode('utf-8')) + 1  # +1 for newline
                
                # Check if rotation is needed
                if self._current_size + message_bytes > self._max_bytes:
                    self._rotate()
                
                self._file.write(message + '\n')
                self._file.flush()
                self._current_size += message_bytes
            except Exception as e:
                print(f"Failed to write to log file: {e}")
    
    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class AsyncHandler(LogHandler):
    """Asynchronous handler that processes logs in background thread"""
    
    def __init__(self, wrapped_handler: LogHandler, queue_size: int = 1000):
        super().__init__(wrapped_handler.get_level(), wrapped_handler.get_formatter())
        self._wrapped_handler = wrapped_handler
        self._queue: Queue = Queue(maxsize=queue_size)
        self._running = False
        self._worker_thread: Optional[Thread] = None
    
    def start(self) -> None:
        """Start the background processing thread"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
    
    def _process_queue(self) -> None:
        """Process log records from queue"""
        while self._running:
            try:
                # Get from queue with timeout
                message, record = self._queue.get(timeout=0.1)
                self._wrapped_handler.emit(message, record)
                self._queue.task_done()
            except:
                # Queue empty or timeout
                continue
    
    def emit(self, message: str, record: LogRecord) -> None:
        """Add to queue for async processing"""
        try:
            self._queue.put_nowait((message, record))
        except:
            # Queue full, log dropped
            print(f"Warning: Log queue full, message dropped")
    
    def close(self) -> None:
        """Stop processing and close wrapped handler"""
        self._running = False
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        
        # Drain remaining items
        while not self._queue.empty():
            try:
                message, record = self._queue.get_nowait()
                self._wrapped_handler.emit(message, record)
            except:
                break
        
        self._wrapped_handler.close()


class FilteredHandler(LogHandler):
    """Handler that filters logs based on custom criteria"""
    
    def __init__(self, wrapped_handler: LogHandler, 
                 filter_func: callable):
        super().__init__(wrapped_handler.get_level(), wrapped_handler.get_formatter())
        self._wrapped_handler = wrapped_handler
        self._filter_func = filter_func
    
    def emit(self, message: str, record: LogRecord) -> None:
        """Only emit if filter passes"""
        if self._filter_func(record):
            self._wrapped_handler.emit(message, record)
    
    def close(self) -> None:
        self._wrapped_handler.close()


# ==================== Logger ====================

class Logger:
    """Main logger class"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self._name = name
        self._level = level
        self._handlers: List[LogHandler] = []
        self._lock = Lock()
    
    def get_name(self) -> str:
        return self._name
    
    def get_level(self) -> LogLevel:
        with self._lock:
            return self._level
    
    def set_level(self, level: LogLevel) -> None:
        with self._lock:
            self._level = level
    
    def add_handler(self, handler: LogHandler) -> None:
        """Add a log handler"""
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler) -> None:
        """Remove a log handler"""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
    
    def _log(self, level: LogLevel, message: str, 
             exception: Optional[Exception] = None,
             extra: Optional[Dict[str, Any]] = None) -> None:
        """Internal logging method"""
        # Check if should log
        if level < self._level:
            return
        
        # Create log record
        record = LogRecord(
            logger_name=self._name,
            level=level,
            message=message,
            exception=exception,
            extra=extra
        )
        
        # Send to all handlers
        with self._lock:
            handlers = self._handlers.copy()
        
        for handler in handlers:
            try:
                handler.handle(record)
            except Exception as e:
                print(f"Error in log handler: {e}")
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message, exception=exception, **kwargs)
    
    def fatal(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log fatal message"""
        self._log(LogLevel.FATAL, message, exception=exception, **kwargs)
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Log with custom level"""
        self._log(level, message, **kwargs)
    
    def close(self) -> None:
        """Close all handlers"""
        with self._lock:
            for handler in self._handlers:
                handler.close()


# ==================== Logger Manager ====================

class LoggerManager:
    """Manages multiple loggers (Singleton)"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._loggers: Dict[str, Logger] = {}
        self._default_level = LogLevel.INFO
        self._default_handlers: List[LogHandler] = []
        self._initialized = True
    
    def get_logger(self, name: str) -> Logger:
        """Get or create a logger"""
        if name not in self._loggers:
            logger = Logger(name, self._default_level)
            
            # Add default handlers
            for handler in self._default_handlers:
                logger.add_handler(handler)
            
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_default_level(self, level: LogLevel) -> None:
        """Set default level for new loggers"""
        self._default_level = level
    
    def add_default_handler(self, handler: LogHandler) -> None:
        """Add default handler for all new loggers"""
        self._default_handlers.append(handler)
    
    def configure_root_logger(self, level: LogLevel = LogLevel.INFO,
                             handlers: Optional[List[LogHandler]] = None) -> Logger:
        """Configure the root logger"""
        root = self.get_logger("root")
        root.set_level(level)
        
        if handlers:
            for handler in handlers:
                root.add_handler(handler)
        
        return root
    
    def shutdown(self) -> None:
        """Shutdown all loggers"""
        for logger in self._loggers.values():
            logger.close()


# ==================== Convenience Functions ====================

def get_logger(name: str = "root") -> Logger:
    """Get a logger instance"""
    manager = LoggerManager()
    return manager.get_logger(name)


def configure_logging(level: LogLevel = LogLevel.INFO,
                     format_type: str = "detailed",
                     output_file: Optional[str] = None,
                     console: bool = True) -> None:
    """Quick configuration of logging system"""
    manager = LoggerManager()
    
    # Choose formatter
    if format_type == "simple":
        formatter = SimpleFormatter()
    elif format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = DetailedFormatter()
    
    handlers = []
    
    # Console handler
    if console:
        console_handler = ConsoleHandler(level, formatter)
        handlers.append(console_handler)
    
    # File handler
    if output_file:
        file_handler = FileHandler(output_file, level, formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    manager.configure_root_logger(level, handlers)


# ==================== Demo Usage ====================

def demo_basic_logging():
    """Demo basic logging functionality"""
    print("=== Basic Logging Demo ===\n")
    
    # Simple configuration
    configure_logging(
        level=LogLevel.DEBUG,
        format_type="detailed",
        console=True
    )
    
    logger = get_logger("demo")
    
    logger.debug("This is a debug message")
    logger.info("Application started")
    logger.warning("This is a warning")
    logger.error("An error occurred")
    logger.fatal("Fatal error!")
    
    print()


def demo_multiple_handlers():
    """Demo using multiple handlers"""
    print("\n=== Multiple Handlers Demo ===\n")
    
    logger = get_logger("multi_handler")
    logger.set_level(LogLevel.DEBUG)
    
    # Console with colors
    console = ConsoleHandler(LogLevel.INFO, DetailedFormatter())
    logger.add_handler(console)
    
    # File with all logs
    file_handler = FileHandler("logs/app.log", LogLevel.DEBUG, DetailedFormatter())
    logger.add_handler(file_handler)
    
    # JSON file for structured logging
    json_handler = FileHandler("logs/app.json", LogLevel.INFO, JSONFormatter())
    logger.add_handler(json_handler)
    
    logger.debug("Debug - only in file")
    logger.info("Info - in console and files")
    logger.error("Error - in console and files")
    
    # Cleanup
    logger.close()
    print()


def demo_custom_formatter():
    """Demo custom formatter"""
    print("\n=== Custom Formatter Demo ===\n")
    
    logger = get_logger("custom")
    logger.set_level(LogLevel.DEBUG)
    
    # Custom format
    formatter = CustomFormatter(
        template="[{timestamp}] {level} | {logger} | {message}",
        date_format="%H:%M:%S"
    )
    
    console = ConsoleHandler(LogLevel.DEBUG, formatter, use_colors=False)
    logger.add_handler(console)
    
    logger.info("Custom formatted message")
    logger.warning("Another message")
    
    logger.close()
    print()


def demo_exception_logging():
    """Demo exception logging"""
    print("\n=== Exception Logging Demo ===\n")
    
    logger = get_logger("exceptions")
    logger.set_level(LogLevel.DEBUG)
    
    console = ConsoleHandler(LogLevel.DEBUG, DetailedFormatter())
    logger.add_handler(console)
    
    try:
        result = 10 / 0
    except Exception as e:
        logger.error("Division by zero error", exception=e)
    
    try:
        data = {"key": "value"}
        value = data["nonexistent"]
    except Exception as e:
        logger.error("Key error occurred", exception=e)
    
    logger.close()
    print()


def demo_filtered_logging():
    """Demo filtered logging"""
    print("\n=== Filtered Logging Demo ===\n")
    
    logger = get_logger("filtered")
    logger.set_level(LogLevel.DEBUG)
    
    # Only log messages containing "important"
    def important_filter(record: LogRecord) -> bool:
        return "important" in record.message.lower()
    
    console = ConsoleHandler(LogLevel.DEBUG, SimpleFormatter())
    filtered = FilteredHandler(console, important_filter)
    logger.add_handler(filtered)
    
    logger.info("This is a regular message")  # Won't appear
    logger.info("This is an IMPORTANT message")  # Will appear
    logger.warning("Important warning")  # Will appear
    logger.error("Regular error")  # Won't appear
    
    logger.close()
    print()


def demo_rotating_logs():
    """Demo rotating file handler"""
    print("\n=== Rotating Logs Demo ===\n")
    
    logger = get_logger("rotating")
    logger.set_level(LogLevel.INFO)
    
    # Rotate when file reaches 1KB
    rotating = RotatingFileHandler(
        "logs/rotating.log",
        max_bytes=1024,
        backup_count=3,
        level=LogLevel.INFO,
        formatter=DetailedFormatter()
    )
    logger.add_handler(rotating)
    
    # Generate lots of logs
    for i in range(100):
        logger.info(f"Log message number {i} with some additional text to increase size")
    
    print("Generated 100 log messages with rotation")
    print("Check logs/rotating.log and backup files")
    
    logger.close()
    print()


def demo_async_logging():
    """Demo asynchronous logging"""
    print("\n=== Async Logging Demo ===\n")
    
    logger = get_logger("async")
    logger.set_level(LogLevel.INFO)
    
    # Wrap console handler in async handler
    console = ConsoleHandler(LogLevel.INFO, SimpleFormatter())
    async_handler = AsyncHandler(console, queue_size=100)
    async_handler.start()
    logger.add_handler(async_handler)
    
    # Log from multiple threads
    def log_from_thread(thread_id: int):
        for i in range(10):
            logger.info(f"Thread {thread_id}, message {i}")
    
    threads = []
    for tid in range(3):
        thread = Thread(target=log_from_thread, args=(tid,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    logger.close()
    print()


def demo_structured_logging():
    """Demo structured logging with extra fields"""
    print("\n=== Structured Logging Demo ===\n")
    
    logger = get_logger("structured")
    logger.set_level(LogLevel.INFO)
    
    json_formatter = JSONFormatter()
    console = ConsoleHandler(LogLevel.INFO, json_formatter, use_colors=False)
    logger.add_handler(console)
    
    # Log with extra structured data
    logger.info("User login", extra={"user_id": 12345, "ip": "192.168.1.1"})
    logger.info("API request", extra={"endpoint": "/api/users", "method": "GET", "duration_ms": 45})
    logger.error("Database error", extra={"query": "SELECT * FROM users", "error_code": 1045})
    
    logger.close()
    print()


def main():
    """Run all demos"""
    demo_basic_logging()
    demo_multiple_handlers()
    demo_custom_formatter()
    demo_exception_logging()
    demo_filtered_logging()
    demo_rotating_logs()
    demo_async_logging()
    demo_structured_logging()
    
    # Shutdown all loggers
    manager = LoggerManager()
    manager.shutdown()
    
    print("\n=== All Demos Complete ===")


if __name__ == "__main__":
    main()


# ## Key Design Decisions

# ### **Design Patterns Used:**

# 1. **Strategy Pattern** - Multiple uses:
#    - **Formatters**: Simple, Detailed, JSON, Custom
#    - **Handlers**: Console, File, Rotating, Async, Filtered

# 2. **Singleton Pattern**:
#    - `LoggerManager`: Single instance manages all loggers

# 3. **Decorator Pattern**:
#    - `AsyncHandler`: Wraps another handler with async processing
#    - `FilteredHandler`: Adds filtering to another handler

# 4. **Chain of Responsibility** (implicit):
#    - Log records passed through multiple handlers
#    - Each handler decides whether to process

# ### **Core Features:**

# ✅ **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, FATAL  
# ✅ **Multiple Formatters**: Simple, Detailed, JSON, Custom templates  
# ✅ **Multiple Destinations**: Console, File, Rotating files  
# ✅ **Async Logging**: Background thread processing  
# ✅ **Structured Logging**: JSON with extra fields  
# ✅ **Exception Logging**: Full stack traces  
# ✅ **Colored Output**: ANSI colors for console  
# ✅ **Log Rotation**: Size-based file rotation  
# ✅ **Filtering**: Custom filter functions  
# ✅ **Thread-Safe**: All operations protected  

# ### **Log Levels (Severity Order):**
# ```
# DEBUG    → Detailed diagnostic info
# INFO     → General informational messages
# WARNING  → Warning messages
# ERROR    → Error messages
# FATAL    → Critical failures
# ```

# ### **Formatter Examples:**

# **Simple**:
# ```
# [INFO] Application started
# ```

# **Detailed**:
# ```
# 2025-10-17 14:30:45 [INFO] [myapp] [MainThread] Application started
# JSON:
# json{
#   "timestamp": "2025-10-17T14:30:45.123456",
#   "level": "INFO",
#   "logger": "myapp",
#   "thread": "MainThread",
#   "message": "Application started"
# }
# ```

# **Custom**:
# ```
# [14:30:45] INFO | myapp | Application started
# Handler Types:

# ConsoleHandler:

# Outputs to stdout
# Optional ANSI colors
# Real-time display


# FileHandler:

# Writes to file
# Append or overwrite mode
# Creates directories automatically


# RotatingFileHandler:

# Size-based rotation
# Keeps N backup files
# app.log → app.log.1 → app.log.2


# AsyncHandler:

# Background queue processing
# Non-blocking logging
# Prevents I/O bottlenecks


# FilteredHandler:

# Custom filter functions
# Conditional logging
# Can filter by level, message content, etc.



# Concurrency Handling:

# Thread Locks:

# Logger: Protects handler list
# Handler: Protects file writes
# Queue: Built-in thread-safe


# Async Processing:

# Separate worker thread
# Queue-based buffering
# Graceful shutdown with drain



# Real-World Usage Patterns:
# Application Logging:
# pythonlogger = get_logger("myapp")
# logger.info("Application started")
# logger.debug("Processing request", extra={"request_id": "123"})
# logger.error("Database connection failed", exception=e)
# Structured Logging:
# pythonlogger.info("API call", extra={
#     "endpoint": "/api/users",
#     "method": "POST",
#     "status_code": 200,
#     "duration_ms": 45,
#     "user_id": 12345
# })
# Different Handlers for Different Levels:
# python# Console: INFO and above
# console = ConsoleHandler(LogLevel.INFO)

# # File: DEBUG and above (everything)
# file = FileHandler("app.log", LogLevel.DEBUG)

# # Error file: Only errors
# error_file = FileHandler("errors.log", LogLevel.ERROR)
# Advanced Features:
# Log Rotation:

# Automatically rotates when size limit reached
# Keeps configurable number of backups
# Prevents disk space issues

# Async Logging:

# Non-blocking for high-performance apps
# Queue buffering
# Background processing thread

# Custom Filters:

# # Only log from specific modules
# def module_filter(record):
#     return record.logger_name.startswith("myapp.")

# # Only log expensive operations
# def slow_query_filter(record):
#     return record.extra.get("duration_ms", 0) > 1000
