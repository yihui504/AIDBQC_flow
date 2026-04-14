"""
Debug script to test critical error detection
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.critical_error_handler import (
    CriticalErrorHandler,
    CriticalErrorType
)

def test_error_detection():
    """Test error detection with debugging."""
    print("Testing error detection with debugging...")
    
    handler = CriticalErrorHandler(
        log_dir=".trae/debug_logs",
        state_dir=".trae/debug_runs",
        enable_auto_cleanup=False
    )
    
    # Test different errors
    test_errors = [
        ("Docker port conflict", RuntimeError("port is already allocated")),
        ("API rate limit", RuntimeError("rate limit exceeded")),
        ("Memory exhaustion", MemoryError("cannot allocate memory")),
        ("Non-critical error", ValueError("invalid input"))
    ]
    
    for name, error in test_errors:
        print(f"\n{name}:")
        print(f"  Error message: {str(error)}")
        print(f"  Error type: {type(error).__name__}")
        
        critical_info = handler.classify_critical_error(error)
        
        if critical_info:
            print(f"  ✓ Detected as critical error")
            print(f"  ✓ Error type: {critical_info.error_type.value}")
            print(f"  ✓ Criticality: {critical_info.criticality_level.value}")
        else:
            print(f"  ✓ Not detected as critical error")


if __name__ == "__main__":
    test_error_detection()