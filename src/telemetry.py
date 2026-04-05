import os
import json
import logging
import logging.handlers
import queue
import atexit
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """
    Structured trace event for observing the pipeline execution.
    """
    trace_id: str = Field(description="Unique identifier for the current run")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    node_name: str = Field(description="Name of the LangGraph node executed")
    event_type: str = Field(description="Type of event: START, END, ERROR, CIRCUIT_BREAK")
    token_usage: int = Field(default=0, description="Tokens consumed during this node's execution")
    state_delta: Dict[str, Any] = Field(default_factory=dict, description="State changes produced by this node")


class JSONLFormatter(logging.Formatter):
    """
    Custom formatter that converts LogRecord to JSONL format.
    """
    def format(self, record):
        try:
            if hasattr(record, 'telemetry_event'):
                event = record.telemetry_event
                return json.dumps(event.model_dump(mode='json'))
            return ""
        except Exception:
            return ""


class TelemetryManager:
    """
    Handles structured logging of TelemetryEvents to a JSONL file with async support and log rotation.
    """
    
    def __init__(
        self,
        log_dir: str = None,
        filename: str = "telemetry.jsonl",
        async_enabled: bool = False,
        max_file_size_mb: int = 50,
        backup_count: int = 10
    ):
        if log_dir is None:
            log_dir = os.path.join(os.getcwd(), ".trae", "runs")
        self.log_dir = os.path.abspath(log_dir)
        self.filename = filename
        self.filepath = os.path.join(self.log_dir, self.filename)
        self.async_enabled = async_enabled
        self.max_file_size_mb = max_file_size_mb
        self.backup_count = backup_count
        self._initialized = False
        
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            self._setup_logging()
            self._initialized = True
        except Exception as e:
            print(f"[Telemetry Error] Failed to initialize telemetry: {e}")
            raise
        
        atexit.register(self.shutdown)
    
    def _setup_logging(self):
        """Setup logging handlers based on configuration."""
        # Create logger
        self.logger = logging.getLogger(f"telemetry_{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        if self.async_enabled:
            # Async logging with QueueHandler
            self._setup_async_logging()
        else:
            # Sync logging with RotatingFileHandler
            self._setup_sync_logging()
    
    def _setup_async_logging(self):
        """Setup async logging with QueueHandler and QueueListener."""
        self.log_queue = queue.Queue(-1)
        
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.logger.addHandler(queue_handler)
        
        self._file_handler = self._create_rotating_file_handler()
        
        self.queue_listener = logging.handlers.QueueListener(
            self.log_queue,
            self._file_handler,
            respect_handler_level=True
        )
        self.queue_listener.start()
    
    def _setup_sync_logging(self):
        """Setup sync logging with RotatingFileHandler."""
        self._file_handler = self._create_rotating_file_handler()
        self.logger.addHandler(self._file_handler)
    
    def _create_rotating_file_handler(self):
        """Create a rotating file handler with custom naming."""
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self.filepath,
                mode='a',
                maxBytes=self.max_file_size_mb * 1024 * 1024,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        except Exception as e:
            print(f"[Telemetry Error] Failed to create file handler at {self.filepath}: {e}")
            raise
        
        def custom_namer(default_name):
            base, ext = os.path.splitext(default_name)
            if '.' in base:
                base, number = base.rsplit('.', 1)
                try:
                    number = int(number)
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    return f"{base}_{timestamp}{ext}"
                except ValueError:
                    pass
            return default_name
        
        file_handler.namer = custom_namer
        file_handler.setFormatter(JSONLFormatter())
        
        return file_handler
    
    def log_event(self, event: TelemetryEvent) -> None:
        """
        Appends a TelemetryEvent as a JSON line to the telemetry sink.
        """
        if not self._initialized:
            print(f"[Telemetry Warning] TelemetryManager not initialized, skipping event: {event.node_name}")
            return
        
        try:
            record = self.logger.makeRecord(
                name=self.logger.name,
                level=logging.INFO,
                fn="",
                lno=0,
                msg="",
                args=(),
                exc_info=None
            )
            record.telemetry_event = event
            
            self.logger.handle(record)
        except Exception as e:
            print(f"[Telemetry Error] Failed to write event: {e}")
    
    def shutdown(self):
        """
        Gracefully shutdown the telemetry manager.
        Ensures all queued logs are written before exit.
        """
        if not self._initialized:
            return
            
        try:
            if self.async_enabled and hasattr(self, 'queue_listener'):
                self.queue_listener.stop()
            
            if hasattr(self, '_file_handler'):
                self._file_handler.flush()
                self._file_handler.close()
            
            if hasattr(self, 'logger'):
                for handler in self.logger.handlers[:]:
                    handler.close()
                    self.logger.removeHandler(handler)
        except Exception as e:
            print(f"[Telemetry Error] Failed to shutdown gracefully: {e}")


# Global instance for easy access (backwards compatible with old name)
telemetry_sink = TelemetryManager()

# Also provide old class name for backwards compatibility
TelemetryLogger = TelemetryManager

def log_node_execution(trace_id: str, node_name: str, state_update: Dict[str, Any], previous_tokens: int) -> None:
    """
    Helper function to log a node's execution result.
    Extracts token usage delta and state delta from the LangGraph output.
    """
    # Calculate token usage for this specific node
    current_tokens = state_update.get("total_tokens_used", previous_tokens)
    tokens_used = current_tokens - previous_tokens
    
    # Clean up state delta for logging (remove large unreadable objects if necessary)
    # Pydantic models in the state update need to be converted to dicts
    clean_delta = {}
    for k, v in state_update.items():
        if hasattr(v, 'model_dump'):
            clean_delta[k] = v.model_dump(mode='json')
        elif isinstance(v, list) and len(v) > 0 and hasattr(v[0], 'model_dump'):
            clean_delta[k] = [item.model_dump(mode='json') for item in v]
        else:
            # Attempt basic serialization check, or just keep it
            clean_delta[k] = v
            
    # Remove potentially massive context strings from the delta to save space
    # BUT only if we are not in the environment recon or contract analysis phase where we might need them later
    # Actually, per WBS 2.0, we will save full docs to a file, so we can truncate here to keep telemetry clean
    if "db_config" in clean_delta and isinstance(clean_delta["db_config"], dict):
        if "docs_context" in clean_delta["db_config"]:
            # We keep it for the first few nodes, then truncate
            if node_name not in ["agent0_env", "agent1_contract"]:
                clean_delta["db_config"]["docs_context"] = "<TRUNCATED - SEE raw_docs.json>"

    event = TelemetryEvent(
        trace_id=trace_id,
        node_name=node_name,
        event_type="END",
        token_usage=tokens_used if tokens_used > 0 else 0,
        state_delta=clean_delta
    )
    telemetry_sink.log_event(event)
