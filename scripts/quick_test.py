"""
Quick test script to verify critical error handling and port management
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_critical_error_handler():
    """Test critical error handler basic functionality."""
    print("Testing Critical Error Handler...")
    
    from src.critical_error_handler import (
        CriticalErrorHandler,
        get_global_critical_error_handler,
        CriticalErrorType
    )
    
    # Create handler
    handler = CriticalErrorHandler(
        log_dir=".trae/test_logs",
        state_dir=".trae/test_runs",
        enable_auto_cleanup=False
    )
    
    # Test error detection
    test_errors = [
        ("Docker port conflict", RuntimeError("port is already allocated"), CriticalErrorType.DOCKER_PORT_CONFLICT),
        ("API rate limit", RuntimeError("rate limit exceeded"), CriticalErrorType.API_RATE_LIMIT),
        ("Memory exhaustion", MemoryError("cannot allocate memory"), CriticalErrorType.RESOURCE_EXHAUSTION),
        ("Non-critical error", ValueError("invalid input"), None)
    ]
    
    for name, error, expected_type in test_errors:
        critical_info = handler.classify_critical_error(error)
        if expected_type:
            assert critical_info is not None, f"{name}: Expected critical error"
            assert critical_info.error_type == expected_type, f"{name}: Wrong error type"
            print(f"  ✓ {name}: Detected correctly")
        else:
            assert critical_info is None, f"{name}: Should not be critical"
            print(f"  ✓ {name}: Correctly identified as non-critical")
    
    # Test global handler
    global_handler = get_global_critical_error_handler()
    assert global_handler is not None, "Global handler should exist"
    print("  ✓ Global handler accessible")
    
    print("✓ Critical Error Handler tests passed!")
    return True


def test_docker_port_manager():
    """Test Docker port manager basic functionality."""
    print("\nTesting Docker Port Manager...")
    
    from src.docker_port_manager import (
        DockerPortManager,
        get_global_port_manager,
        PortConflictError
    )
    
    # Create manager
    manager = DockerPortManager(
        state_dir=".trae/test_port_manager",
        enable_auto_cleanup=False
    )
    
    # Test port allocation
    port = manager.allocate_port(
        service_type="general",
        allocated_by="test_script",
        purpose="testing"
    )
    assert port is not None, "Port should be allocated"
    print(f"  ✓ Port allocated: {port}")
    
    # Test allocation info
    info = manager.get_allocation_info(port)
    assert info is not None, "Allocation info should exist"
    assert info.port == port, "Port number should match"
    assert info.is_active == True, "Port should be active"
    print("  ✓ Allocation info retrieved correctly")
    
    # Test active allocations
    active = manager.get_active_allocations()
    assert len(active) == 1, "Should have one active allocation"
    print("  ✓ Active allocations retrieved correctly")
    
    # Test port release
    success = manager.release_port(port)
    assert success == True, "Port release should succeed"
    print("  ✓ Port released successfully")
    
    # Test stats
    stats = manager.get_port_usage_stats()
    assert stats["active_allocations"] == 0, "Should have no active allocations"
    assert stats["total_allocations"] == 1, "Should have one total allocation"
    print("  ✓ Port usage statistics correct")
    
    # Test global manager
    global_manager = get_global_port_manager()
    assert global_manager is not None, "Global manager should exist"
    print("  ✓ Global manager accessible")
    
    # Cleanup
    manager.cleanup_orphaned_ports(force=True)
    manager.shutdown()
    print("  ✓ Manager shutdown successfully")
    
    print("✓ Docker Port Manager tests passed!")
    return True


def main():
    """Run all tests."""
    print("="*50)
    print("QUICK FUNCTIONALITY TEST")
    print("="*50)
    
    try:
        success = True
        success &= test_critical_error_handler()
        success &= test_docker_port_manager()
        
        if success:
            print("\n" + "="*50)
            print("✓ ALL TESTS PASSED!")
            print("="*50)
            return 0
        else:
            print("\n❌ SOME TESTS FAILED")
            return 1
    
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())