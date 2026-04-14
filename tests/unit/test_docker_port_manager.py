"""
Unit tests for Docker Port Manager

Tests Docker port allocation, conflict detection, and cleanup
functionality for AI-DB-QC system.
"""

import unittest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.docker_port_manager import (
    DockerPortManager,
    PortConflictError,
    PortExhaustionError,
    PortAllocationError,
    get_global_port_manager,
    initialize_global_port_manager
)


class TestDockerPortManager(unittest.TestCase):
    """Test Docker port manager basic functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerPortManager(
            state_dir=str(Path(self.temp_dir) / "port_manager"),
            enable_auto_cleanup=False  # Disable auto cleanup for tests
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_port_allocation(self):
        """Test basic port allocation."""
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test",
            purpose="unit_test"
        )
        
        self.assertIsNotNone(port)
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
    
    def test_port_allocation_with_preferred_port(self):
        """Test port allocation with preferred port."""
        preferred_port = 9100
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test",
            preferred_port=preferred_port
        )
        
        self.assertEqual(port, preferred_port)
    
    def test_port_allocation_record(self):
        """Test that port allocation is recorded."""
        port = self.manager.allocate_port(
            service_type="milvus",
            allocated_by="test",
            run_id="test_run_123",
            purpose="database"
        )
        
        allocation_info = self.manager.get_allocation_info(port)
        
        self.assertIsNotNone(allocation_info)
        self.assertEqual(allocation_info.port, port)
        self.assertEqual(allocation_info.is_active, True)
        self.assertEqual(allocation_info.run_id, "test_run_123")
        self.assertEqual(allocation_info.service_type, "milvus")
    
    def test_port_release(self):
        """Test port release."""
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test"
        )
        
        # Verify port is allocated
        allocation_info = self.manager.get_allocation_info(port)
        self.assertIsNotNone(allocation_info)
        self.assertTrue(allocation_info.is_active)
        
        # Release port
        success = self.manager.release_port(port)
        
        self.assertTrue(success)
        
        # Verify port is released
        allocation_info = self.manager.get_allocation_info(port)
        self.assertIsNotNone(allocation_info)
        self.assertFalse(allocation_info.is_active)
    
    def test_active_allocations(self):
        """Test getting active allocations."""
        port1 = self.manager.allocate_port(
            service_type="general",
            allocated_by="test1"
        )
        port2 = self.manager.allocate_port(
            service_type="milvus",
            allocated_by="test2"
        )
        
        active_allocations = self.manager.get_active_allocations()
        
        active_ports = [alloc.port for alloc in active_allocations]
        self.assertIn(port1, active_ports)
        self.assertIn(port2, active_ports)
        self.assertEqual(len(active_allocations), 2)
    
    def test_port_usage_stats(self):
        """Test port usage statistics."""
        # Allocate some ports
        port1 = self.manager.allocate_port(
            service_type="general",
            allocated_by="test1"
        )
        port2 = self.manager.allocate_port(
            service_type="milvus",
            allocated_by="test2"
        )
        
        # Release one port
        self.manager.release_port(port1)
        
        # Get stats
        stats = self.manager.get_port_usage_stats()
        
        self.assertEqual(stats["total_allocations"], 2)
        self.assertEqual(stats["active_allocations"], 1)
        self.assertEqual(stats["inactive_allocations"], 1)
        self.assertIn(port2, stats["ports_in_use"])
    
    def test_port_heartbeat(self):
        """Test port heartbeat update."""
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test"
        )
        
        # Get initial heartbeat
        initial_allocation = self.manager.get_allocation_info(port)
        initial_heartbeat = initial_allocation.last_heartbeat
        
        # Wait a bit and update heartbeat
        time.sleep(0.1)
        success = self.manager.heartbeat_port(port)
        
        self.assertTrue(success)
        
        # Get updated heartbeat
        updated_allocation = self.manager.get_allocation_info(port)
        updated_heartbeat = updated_allocation.last_heartbeat
        
        self.assertNotEqual(initial_heartbeat, updated_heartbeat)
    
    def test_context_manager(self):
        """Test port allocation with context manager."""
        with self.manager.allocated_port(
            service_type="general",
            allocated_by="context_test"
        ) as port:
            # Port should be allocated
            allocation_info = self.manager.get_allocation_info(port)
            self.assertIsNotNone(allocation_info)
            self.assertTrue(allocation_info.is_active)
        
        # Port should be released after context exit
        allocation_info = self.manager.get_allocation_info(port)
        self.assertIsNotNone(allocation_info)
        self.assertFalse(allocation_info.is_active)
    
    def test_port_persistence(self):
        """Test that port allocations persist to disk."""
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test",
            run_id="persist_test"
        )
        
        # Create new manager with same state directory
        new_manager = DockerPortManager(
            state_dir=str(Path(self.temp_dir) / "port_manager"),
            enable_auto_cleanup=False
        )
        
        # Verify port allocation is loaded
        allocation_info = new_manager.get_allocation_info(port)
        
        self.assertIsNotNone(allocation_info)
        self.assertEqual(allocation_info.port, port)
        self.assertEqual(allocation_info.run_id, "persist_test")
        
        new_manager.shutdown()
    
    def test_service_specific_port_ranges(self):
        """Test that different services use appropriate port ranges."""
        milvus_port = self.manager.allocate_port(
            service_type="milvus",
            allocated_by="test"
        )
        
        qdrant_port = self.manager.allocate_port(
            service_type="qdrant",
            allocated_by="test"
        )
        
        weaviate_port = self.manager.allocate_port(
            service_type="weaviate",
            allocated_by="test"
        )
        
        # Verify ports are in expected ranges
        self.assertGreaterEqual(milvus_port, 19530)
        self.assertLessEqual(milvus_port, 19600)
        
        self.assertGreaterEqual(qdrant_port, 6333)
        self.assertLessEqual(qdrant_port, 6400)
        
        self.assertGreaterEqual(weaviate_port, 8080)
        self.assertLessEqual(weaviate_port, 8150)


class TestPortConflictDetection(unittest.TestCase):
    """Test port conflict detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerPortManager(
            state_dir=str(Path(self.temp_dir) / "port_manager"),
            enable_auto_cleanup=False
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.docker_port_manager.socket.socket')
    def test_port_availability_check(self, mock_socket):
        """Test port availability check."""
        # Mock successful connection (port in use)
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Port in use
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        available = self.manager._check_port_available(8080)
        self.assertFalse(available)
        
        # Mock failed connection (port available)
        mock_sock.connect_ex.return_value = 1  # Port available
        available = self.manager._check_port_available(8081)
        self.assertTrue(available)
    
    def test_preferred_port_conflict(self):
        """Test that preferred port conflict raises error."""
        # Allocate a port
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test1",
            preferred_port=9100
        )
        
        # Try to allocate same port again
        with self.assertRaises(PortConflictError):
            self.manager.allocate_port(
                service_type="general",
                allocated_by="test2",
                preferred_port=9100
            )
    
    def test_custom_port_range(self):
        """Test port allocation with custom range."""
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test",
            port_range=(10000, 10010)
        )
        
        self.assertGreaterEqual(port, 10000)
        self.assertLessEqual(port, 10010)


class TestOrphanedPortCleanup(unittest.TestCase):
    """Test orphaned port cleanup functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerPortManager(
            state_dir=str(Path(self.temp_dir) / "port_manager"),
            enable_auto_cleanup=False,
            orphan_timeout_minutes=1  # Short timeout for tests
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cleanup_inactive_ports(self):
        """Test cleanup of inactive ports."""
        # Allocate and release ports
        port1 = self.manager.allocate_port(
            service_type="general",
            allocated_by="test1"
        )
        port2 = self.manager.allocate_port(
            service_type="milvus",
            allocated_by="test2"
        )
        
        self.manager.release_port(port1)
        self.manager.release_port(port2)
        
        # Clean up orphaned ports
        cleaned_ports = self.manager.cleanup_orphaned_ports()
        
        # Both ports should be cleaned up
        self.assertEqual(len(cleaned_ports), 2)
        self.assertIn(port1, cleaned_ports)
        self.assertIn(port2, cleaned_ports)
    
    def test_cleanup_dry_run(self):
        """Test dry run mode for cleanup."""
        # Allocate and release a port
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test"
        )
        self.manager.release_port(port)
        
        # Dry run should report what would be cleaned but not actually clean
        cleaned_ports = self.manager.cleanup_orphaned_ports(dry_run=True)
        
        self.assertIn(port, cleaned_ports)
        
        # Port should still be in allocations
        allocation_info = self.manager.get_allocation_info(port)
        self.assertIsNotNone(allocation_info)
    
    def test_cleanup_with_force(self):
        """Test force cleanup of active ports."""
        # Allocate a port
        port = self.manager.allocate_port(
            service_type="general",
            allocated_by="test"
        )
        
        # Force cleanup should remove even active allocations
        cleaned_ports = self.manager.cleanup_orphaned_ports(force=True)
        
        self.assertIn(port, cleaned_ports)
        
        # Port should be removed from allocations
        allocation_info = self.manager.get_allocation_info(port)
        self.assertIsNone(allocation_info)


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of port manager operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerPortManager(
            state_dir=str(Path(self.temp_dir) / "port_manager"),
            enable_auto_cleanup=False
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_port_allocation(self):
        """Test concurrent port allocation from multiple threads."""
        num_threads = 10
        ports = []
        errors = []
        
        def allocate_port(thread_id):
            try:
                port = self.manager.allocate_port(
                    service_type="general",
                    allocated_by=f"thread_{thread_id}"
                )
                ports.append(port)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=allocate_port, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all allocations succeeded
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(ports), num_threads)
        
        # Verify all ports are unique
        self.assertEqual(len(set(ports)), num_threads, "Ports should be unique")


class TestGlobalPortManager(unittest.TestCase):
    """Test global port manager instance."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global manager
        import src.docker_port_manager as dpm
        dpm._global_port_manager = None
    
    def test_global_manager_initialization(self):
        """Test that global manager can be initialized."""
        manager = get_global_port_manager()
        
        self.assertIsNotNone(manager)
        self.assertIsInstance(manager, DockerPortManager)
    
    def test_global_manager_singleton(self):
        """Test that global manager is a singleton."""
        manager1 = get_global_port_manager()
        manager2 = get_global_port_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_global_manager_custom_initialization(self):
        """Test that global manager can be initialized with custom parameters."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            manager = initialize_global_port_manager(
                state_dir=str(Path(temp_dir) / "port_manager"),
                enable_auto_cleanup=False
            )
            
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, DockerPortManager)
            
            # Verify same instance is returned
            manager2 = get_global_port_manager()
            self.assertIs(manager, manager2)
        
        finally:
            manager.shutdown()
            shutil.rmtree(temp_dir, ignore_errors=True)
            # Reset global manager
            import src.docker_port_manager as dpm
            dpm._global_port_manager = None


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_find_available_port(self):
        """Test finding an available port."""
        port = DockerPortManager._find_available_port(
            None,  # Create temp manager
            (10000, 10010)
        )
        
        self.assertIsNotNone(port)
        self.assertGreaterEqual(port, 10000)
        self.assertLessEqual(port, 10010)
    
    @patch('src.docker_port_manager.get_global_port_manager')
    def test_is_port_available(self, mock_get_global):
        """Test port availability check utility."""
        mock_manager = MagicMock()
        mock_manager._check_port_available.return_value = True
        mock_get_global.return_value = mock_manager
        
        from src.docker_port_manager import is_port_available
        
        result = is_port_available(8080)
        
        self.assertTrue(result)
        mock_manager._check_port_available.assert_called_once_with(8080)


if __name__ == "__main__":
    unittest.main()