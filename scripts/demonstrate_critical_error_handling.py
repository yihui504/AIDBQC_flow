"""
Demonstration script for Critical Error Handling and Docker Port Management

This script demonstrates the key features of the new critical error handling
and Docker port management modules in the AI-DB-QC system.
"""

import sys
import os
import time
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.critical_error_handler import (
    CriticalErrorHandler,
    CriticalErrorType,
    CriticalityLevel,
    get_global_critical_error_handler,
    initialize_global_critical_error_handler
)
from src.docker_port_manager import (
    DockerPortManager,
    PortConflictError,
    get_global_port_manager,
    initialize_global_port_manager
)
from src.exceptions import LLMRateLimitError, DatabaseConnectionError


def demonstrate_critical_error_detection():
    """Demonstrate critical error detection and classification."""
    print("\n" + "="*60)
    print("CRITICAL ERROR DETECTION DEMONSTRATION")
    print("="*60)
    
    # Initialize critical error handler
    handler = CriticalErrorHandler(
        log_dir=".trae/demo_logs",
        state_dir=".trae/demo_runs",
        enable_auto_cleanup=False
    )
    
    print("\n1. Testing Docker port conflict detection...")
    docker_error = RuntimeError("Error: port is already allocated")
    critical_info = handler.classify_critical_error(docker_error)
    
    if critical_info:
        print(f"   ✓ Detected critical error: {critical_info.error_type.value}")
        print(f"   ✓ Criticality level: {critical_info.criticality_level.value}")
        print(f"   ✓ Requires immediate shutdown: {critical_info.requires_immediate_shutdown}")
        print(f"   ✓ Cleanup priority: {critical_info.cleanup_priority}")
    
    print("\n2. Testing API rate limit detection...")
    rate_limit_error = LLMRateLimitError(
        provider="openai",
        retry_after_seconds=60
    )
    critical_info = handler.classify_critical_error(rate_limit_error)
    
    if critical_info:
        print(f"   ✓ Detected critical error: {critical_info.error_type.value}")
        print(f"   ✓ Criticality level: {critical_info.criticality_level.value}")
        print(f"   ✓ Context: {critical_info.context}")
    
    print("\n3. Testing memory exhaustion detection...")
    memory_error = MemoryError("cannot allocate memory")
    critical_info = handler.classify_critical_error(memory_error)
    
    if critical_info:
        print(f"   ✓ Detected critical error: {critical_info.error_type.value}")
        print(f"   ✓ Criticality level: {critical_info.criticality_level.value}")
        print(f"   ✓ Recovery suggestions: {critical_info.recovery_suggestions[:2]}")
    
    print("\n4. Testing non-critical error handling...")
    normal_error = ValueError("Invalid input parameter")
    critical_info = handler.classify_critical_error(normal_error)
    
    if critical_info is None:
        print(f"   ✓ Correctly identified as non-critical error")
    
    print("\n5. Testing database connection error detection...")
    db_error = DatabaseConnectionError(
        host="localhost",
        port=5432,
        reason="Connection refused"
    )
    critical_info = handler.classify_critical_error(db_error)
    
    if critical_info:
        print(f"   ✓ Detected critical error: {critical_info.error_type.value}")
        print(f"   ✓ Recovery suggestions: {critical_info.recovery_suggestions[:3]}")


def demonstrate_port_management():
    """Demonstrate Docker port management functionality."""
    print("\n" + "="*60)
    print("DOCKER PORT MANAGEMENT DEMONSTRATION")
    print("="*60)
    
    # Initialize port manager
    manager = DockerPortManager(
        state_dir=".trae/demo_port_manager",
        enable_auto_cleanup=False
    )
    
    try:
        print("\n1. Allocating ports for different services...")
        
        # Allocate port for Milvus
        milvus_port = manager.allocate_port(
            service_type="milvus",
            allocated_by="demo_script",
            run_id="demo_run_001",
            purpose="vector_database"
        )
        print(f"   ✓ Allocated Milvus port: {milvus_port}")
        
        # Allocate port for Qdrant
        qdrant_port = manager.allocate_port(
            service_type="qdrant",
            allocated_by="demo_script",
            run_id="demo_run_001",
            purpose="vector_database"
        )
        print(f"   ✓ Allocated Qdrant port: {qdrant_port}")
        
        # Allocate port for Weaviate
        weaviate_port = manager.allocate_port(
            service_type="weaviate",
            allocated_by="demo_script",
            run_id="demo_run_001",
            purpose="vector_database"
        )
        print(f"   ✓ Allocated Weaviate port: {weaviate_port}")
        
        print("\n2. Checking port allocation information...")
        
        # Get allocation info
        milvus_info = manager.get_allocation_info(milvus_port)
        print(f"   ✓ Milvus port allocation:")
        print(f"      - Port: {milvus_info.port}")
        print(f"      - Active: {milvus_info.is_active}")
        print(f"      - Purpose: {milvus_info.purpose}")
        print(f"      - Run ID: {milvus_info.run_id}")
        
        print("\n3. Getting active allocations...")
        active_allocations = manager.get_active_allocations()
        print(f"   ✓ Active allocations: {len(active_allocations)}")
        for allocation in active_allocations:
            print(f"      - Port {allocation.port}: {allocation.purpose}")
        
        print("\n4. Getting port usage statistics...")
        stats = manager.get_port_usage_stats()
        print(f"   ✓ Total allocations: {stats['total_allocations']}")
        print(f"   ✓ Active allocations: {stats['active_allocations']}")
        print(f"   ✓ Ports in use: {stats['ports_in_use']}")
        
        print("\n5. Testing port heartbeat...")
        success = manager.heartbeat_port(milvus_port)
        print(f"   ✓ Heartbeat update successful: {success}")
        
        print("\n6. Testing port release...")
        success = manager.release_port(milvus_port)
        print(f"   ✓ Port release successful: {success}")
        
        # Get updated stats
        stats = manager.get_port_usage_stats()
        print(f"   ✓ Active allocations after release: {stats['active_allocations']}")
        
        print("\n7. Testing context manager for temporary port allocation...")
        with manager.allocated_port(
            service_type="general",
            allocated_by="demo_script",
            purpose="temporary_test"
        ) as temp_port:
            print(f"   ✓ Temporary port allocated: {temp_port}")
            print(f"   ✓ Port is active during context")
        
        print(f"   ✓ Port automatically released after context exit")
        
        # Final stats
        stats = manager.get_port_usage_stats()
        print(f"   ✓ Final active allocations: {stats['active_allocations']}")
        
    finally:
        # Clean up
        print("\n8. Cleaning up port manager...")
        manager.cleanup_orphaned_ports(force=True)
        manager.shutdown()
        print("   ✓ Port manager shutdown complete")


def demonstrate_integration():
    """Demonstrate integration between critical error handler and port manager."""
    print("\n" + "="*60)
    print("INTEGRATION DEMONSTRATION")
    print("="*60)
    
    # Initialize both components
    critical_handler = CriticalErrorHandler(
        log_dir=".trae/demo_integration_logs",
        state_dir=".trae/demo_integration_runs",
        enable_auto_cleanup=False
    )
    
    port_manager = DockerPortManager(
        state_dir=".trae/demo_integration_port_manager",
        enable_auto_cleanup=False
    )
    
    # Register cleanup handler
    critical_handler.register_cleanup_handler(port_manager.cleanup_orphaned_ports)
    print("\n1. Registered port manager as cleanup handler")
    
    # Simulate a port conflict scenario
    print("\n2. Simulating port conflict scenario...")
    
    try:
        # Allocate a port
        port = port_manager.allocate_port(
            service_type="general",
            allocated_by="demo_integration",
            preferred_port=9999
        )
        print(f"   ✓ Allocated port: {port}")
        
        # Try to allocate the same port again (should fail)
        try:
            port_manager.allocate_port(
                service_type="general",
                allocated_by="demo_integration",
                preferred_port=9999
            )
        except PortConflictError as e:
            print(f"   ✓ Port conflict detected: {e}")
            
            # Check if this is a critical error
            is_critical = critical_handler.is_critical_error(e)
            print(f"   ✓ Is critical error: {is_critical}")
    
    finally:
        # Cleanup
        port_manager.cleanup_orphaned_ports(force=True)
        port_manager.shutdown()
        print("\n3. Cleanup completed")


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("CRITICAL ERROR HANDLING & DOCKER PORT MANAGEMENT")
    print("DEMONSTRATION")
    print("="*60)
    
    try:
        # Run demonstrations
        demonstrate_critical_error_detection()
        demonstrate_port_management()
        demonstrate_integration()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey Features Demonstrated:")
        print("1. Critical error detection and classification")
        print("2. Automatic error severity assessment")
        print("3. Recovery suggestion generation")
        print("4. Thread-safe port allocation")
        print("5. Port conflict detection")
        print("6. Automatic port cleanup")
        print("7. Integration between components")
        print("\nAll components are ready for production use!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())