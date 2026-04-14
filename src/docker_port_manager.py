"""
Docker Port Manager for AI-DB-QC

This module provides comprehensive Docker port management functionality including:
- Port allocation and release management
- Port conflict detection and resolution
- Automatic port cleanup and orphan handling
- Port pool management for concurrent operations

Features:
- Thread-safe port allocation
- Automatic conflict detection
- Orphaned port cleanup
- Port usage tracking and monitoring
- Integration with Docker operations

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-04-14
"""

import os
import json
import socket
import subprocess
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from contextlib import contextmanager

from src.exceptions import AIDBQCException, capture_evidence


# ============================================================================
# Port Management Exceptions
# ============================================================================

class PortConflictError(AIDBQCException):
    """Raised when a port conflict is detected."""
    
    def __init__(
        self,
        port: int,
        conflicting_process: Optional[str] = None,
        evidence=None
    ):
        message = f"Port {port} is already in use"
        if conflicting_process:
            message += f" by process: {conflicting_process}"
        super().__init__(message, "E_PORT_001", evidence)


class PortExhaustionError(AIDBQCException):
    """Raised when no available ports are found."""
    
    def __init__(
        self,
        port_range: Tuple[int, int],
        evidence=None
    ):
        message = f"No available ports in range {port_range[0]}-{port_range[1]}"
        super().__init__(message, "E_PORT_002", evidence)


class PortAllocationError(AIDBQCException):
    """Raised when port allocation fails."""
    
    def __init__(
        self,
        port: int,
        reason: str,
        evidence=None
    ):
        message = f"Failed to allocate port {port}: {reason}"
        super().__init__(message, "E_PORT_003", evidence)


# ============================================================================
# Port Allocation Record
# ============================================================================

@dataclass
class PortAllocation:
    """Record of a port allocation."""
    
    port: int
    allocated_at: str
    allocated_by: str  # Component or process that allocated the port
    run_id: Optional[str] = None
    container_id: Optional[str] = None
    purpose: str = "general"
    is_active: bool = True
    last_heartbeat: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ============================================================================
# Docker Port Manager
# ============================================================================

class DockerPortManager:
    """
    Manages Docker port allocation, conflict detection, and cleanup.
    
    Features:
    - Thread-safe port allocation
    - Automatic conflict detection
    - Orphaned port cleanup
    - Port usage tracking
    - Integration with Docker operations
    """
    
    # Default port ranges for different services
    DEFAULT_PORT_RANGES = {
        "milvus": (19530, 19600),
        "qdrant": (6333, 6400),
        "weaviate": (8080, 8150),
        "chroma": (8000, 8050),
        "general": (9000, 9500),
        "monitoring": (3000, 3050)
    }
    
    def __init__(
        self,
        state_dir: str = ".trae/port_manager",
        enable_auto_cleanup: bool = True,
        cleanup_interval_seconds: int = 300,
        orphan_timeout_minutes: int = 60
    ):
        """
        Initialize the Docker port manager.
        
        Args:
            state_dir: Directory for storing port allocation state
            enable_auto_cleanup: Enable automatic orphaned port cleanup
            cleanup_interval_seconds: Interval between cleanup operations
            orphan_timeout_minutes: Time before considering a port orphaned
        """
        self.state_dir = Path(state_dir)
        self.enable_auto_cleanup = enable_auto_cleanup
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.orphan_timeout_minutes = orphan_timeout_minutes
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create state directory
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Port allocation storage
        self._allocations: Dict[int, PortAllocation] = {}
        self._port_lock = threading.Lock()
        
        # Port usage tracking
        self._port_usage_history: List[Dict] = []
        
        # Load existing allocations from disk
        self._load_allocations()
        
        # Start cleanup thread if enabled
        self._cleanup_thread = None
        if self.enable_auto_cleanup:
            self._start_cleanup_thread()
        
        self.logger.info("DockerPortManager initialized")
    
    def _load_allocations(self) -> None:
        """Load port allocations from disk."""
        allocation_file = self.state_dir / "port_allocations.json"
        
        if not allocation_file.exists():
            self.logger.info("No existing port allocations found")
            return
        
        try:
            with open(allocation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for port, allocation_data in data.items():
                port_int = int(port)
                self._allocations[port_int] = PortAllocation(**allocation_data)
            
            self.logger.info(f"Loaded {len(self._allocations)} port allocations from disk")
        
        except Exception as e:
            self.logger.error(f"Failed to load port allocations: {e}")
    
    def _save_allocations(self) -> None:
        """Save port allocations to disk."""
        allocation_file = self.state_dir / "port_allocations.json"
        
        try:
            with self._port_lock:
                data = {
                    str(port): allocation.to_dict()
                    for port, allocation in self._allocations.items()
                }
                
            with open(allocation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.logger.error(f"Failed to save port allocations: {e}")
    
    def _start_cleanup_thread(self) -> None:
        """Start the automatic cleanup thread."""
        import time
        
        def cleanup_loop():
            while True:
                try:
                    time.sleep(self.cleanup_interval_seconds)
                    self.cleanup_orphaned_ports()
                except Exception as e:
                    self.logger.error(f"Error in cleanup thread: {e}")
        
        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="PortManagerCleanup"
        )
        self._cleanup_thread.start()
        self.logger.info("Port cleanup thread started")
    
    def _check_port_available(self, port: int) -> bool:
        """
        Check if a port is available for use.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        # Check socket availability
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    return False  # Port is in use
        except Exception:
            return False
        
        # Check if port is allocated in our records
        with self._port_lock:
            if port in self._allocations and self._allocations[port].is_active:
                return False
        
        # Check Docker for port conflicts
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Ports}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if f":{port}->" in line or f":{port}/" in line:
                    return False
        
        except Exception as e:
            self.logger.warning(f"Docker port check failed: {e}")
        
        return True
    
    def _find_available_port(
        self,
        port_range: Tuple[int, int],
        exclude_ports: Optional[Set[int]] = None
    ) -> Optional[int]:
        """
        Find an available port within the given range.
        
        Args:
            port_range: Tuple of (start_port, end_port)
            exclude_ports: Set of ports to exclude from consideration
            
        Returns:
            Available port number or None if no port is available
        """
        exclude_ports = exclude_ports or set()
        
        # Add currently allocated ports to exclude set
        with self._port_lock:
            exclude_ports.update(self._allocations.keys())
        
        for port in range(port_range[0], port_range[1] + 1):
            if port in exclude_ports:
                continue
            
            if self._check_port_available(port):
                return port
        
        return None
    
    def allocate_port(
        self,
        service_type: str = "general",
        allocated_by: str = "unknown",
        run_id: Optional[str] = None,
        container_id: Optional[str] = None,
        purpose: str = "general",
        preferred_port: Optional[int] = None,
        port_range: Optional[Tuple[int, int]] = None
    ) -> int:
        """
        Allocate a port for Docker service.
        
        Args:
            service_type: Type of service (milvus, qdrant, weaviate, etc.)
            allocated_by: Component or process allocating the port
            run_id: Optional run ID for tracking
            container_id: Optional Docker container ID
            purpose: Purpose of port allocation
            preferred_port: Preferred port number (if available)
            port_range: Custom port range (overrides defaults)
            
        Returns:
            Allocated port number
            
        Raises:
            PortConflictError: If preferred port is in use
            PortExhaustionError: If no available ports are found
            PortAllocationError: If port allocation fails
        """
        # Determine port range
        if port_range is None:
            port_range = self.DEFAULT_PORT_RANGES.get(service_type, self.DEFAULT_PORT_RANGES["general"])
        
        # Check preferred port if specified
        if preferred_port is not None:
            if not self._check_port_available(preferred_port):
                # Find conflicting process
                conflicting_process = self._find_process_using_port(preferred_port)
                raise PortConflictError(
                    port=preferred_port,
                    conflicting_process=conflicting_process,
                    evidence=capture_evidence(
                        component="docker_port_manager",
                        service_type=service_type,
                        allocated_by=allocated_by
                    )
                )
            
            # Allocate preferred port
            return self._allocate_port_internal(
                port=preferred_port,
                service_type=service_type,
                allocated_by=allocated_by,
                run_id=run_id,
                container_id=container_id,
                purpose=purpose
            )
        
        # Find available port in range
        available_port = self._find_available_port(port_range)
        
        if available_port is None:
            raise PortExhaustionError(
                port_range=port_range,
                evidence=capture_evidence(
                    component="docker_port_manager",
                    service_type=service_type,
                    allocated_by=allocated_by
                )
            )
        
        # Allocate the port
        return self._allocate_port_internal(
            port=available_port,
            service_type=service_type,
            allocated_by=allocated_by,
            run_id=run_id,
            container_id=container_id,
            purpose=purpose
        )
    
    def _allocate_port_internal(
        self,
        port: int,
        service_type: str,
        allocated_by: str,
        run_id: Optional[str],
        container_id: Optional[str],
        purpose: str
    ) -> int:
        """Internal method to allocate a port."""
        try:
            allocation = PortAllocation(
                port=port,
                allocated_at=datetime.now().isoformat(),
                allocated_by=allocated_by,
                run_id=run_id,
                container_id=container_id,
                purpose=purpose,
                is_active=True,
                last_heartbeat=datetime.now().isoformat()
            )
            
            with self._port_lock:
                self._allocations[port] = allocation
            
            # Save to disk
            self._save_allocations()
            
            # Log usage
            self._log_port_usage(port, "allocated", {
                "service_type": service_type,
                "allocated_by": allocated_by,
                "run_id": run_id
            })
            
            self.logger.info(f"Allocated port {port} for {service_type} by {allocated_by}")
            return port
        
        except Exception as e:
            self.logger.error(f"Failed to allocate port {port}: {e}")
            raise PortAllocationError(
                port=port,
                reason=str(e),
                evidence=capture_evidence(
                    component="docker_port_manager",
                    port=port,
                    service_type=service_type
                )
            )
    
    def release_port(
        self,
        port: int,
        force: bool = False,
        cleanup_container: bool = False
    ) -> bool:
        """
        Release a previously allocated port.
        
        Args:
            port: Port number to release
            force: Force release even if container is still running
            cleanup_container: Attempt to cleanup container if exists
            
        Returns:
            True if port was released, False otherwise
        """
        try:
            with self._port_lock:
                if port not in self._allocations:
                    self.logger.warning(f"Port {port} was not allocated")
                    return False
                
                allocation = self._allocations[port]
                
                # Check if container is still running
                if allocation.container_id and not force:
                    if self._is_container_running(allocation.container_id):
                        self.logger.warning(
                            f"Container {allocation.container_id} still running, "
                            f"use force=True to release port {port}"
                        )
                        return False
                    
                    # Cleanup container if requested
                    if cleanup_container:
                        self._cleanup_container(allocation.container_id)
                
                # Mark as inactive
                allocation.is_active = False
            
            # Save to disk
            self._save_allocations()
            
            # Log usage
            self._log_port_usage(port, "released", {
                "force": force,
                "cleanup_container": cleanup_container
            })
            
            self.logger.info(f"Released port {port}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to release port {port}: {e}")
            return False
    
    def _find_process_using_port(self, port: int) -> Optional[str]:
        """Find the process using the specified port."""
        try:
            # Try to find the process using the port
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    ['netstat', '-ano', '-p', 'tcp'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                # Get process name
                                proc_result = subprocess.run(
                                    ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                                    capture_output=True,
                                    text=True,
                                    check=True
                                )
                                if len(proc_result.stdout.split('\n')) > 1:
                                    process_info = proc_result.stdout.split('\n')[1]
                                    return process_info.split(',')[0].strip('"')
                            except Exception:
                                return f"PID: {pid}"
            else:  # Unix-like systems
                result = subprocess.run(
                    ['lsof', '-i', f':{port}', '-n', '-P'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    if len(lines) > 1:
                        return lines[1].strip()
        
        except Exception as e:
            self.logger.debug(f"Failed to find process for port {port}: {e}")
        
        return None
    
    def _is_container_running(self, container_id: str) -> bool:
        """Check if a Docker container is still running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().lower() == "true"
        
        except Exception as e:
            self.logger.debug(f"Failed to check container status: {e}")
            return False
    
    def _cleanup_container(self, container_id: str) -> bool:
        """Cleanup a Docker container."""
        try:
            self.logger.info(f"Cleaning up container {container_id}")
            
            # Stop the container
            subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Remove the container
            subprocess.run(
                ["docker", "rm", container_id],
                capture_output=True,
                text=True,
                check=False
            )
            
            self.logger.info(f"Successfully cleaned up container {container_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup container {container_id}: {e}")
            return False
    
    def cleanup_orphaned_ports(
        self,
        force: bool = False,
        dry_run: bool = False
    ) -> List[int]:
        """
        Clean up orphaned port allocations.
        
        Args:
            force: Force cleanup of all inactive ports
            dry_run: Don't actually cleanup, just report what would be done
            
        Returns:
            List of ports that were cleaned up
        """
        cleaned_ports = []
        current_time = datetime.now()
        
        try:
            with self._port_lock:
                ports_to_remove = []
                
                for port, allocation in self._allocations.items():
                    # Skip active allocations unless forced
                    if allocation.is_active and not force:
                        continue
                    
                    # Check if port is orphaned (no heartbeat for timeout period)
                    if allocation.last_heartbeat:
                        last_heartbeat = datetime.fromisoformat(allocation.last_heartbeat)
                        time_since_heartbeat = (current_time - last_heartbeat).total_seconds()
                        
                        if time_since_heartbeat > (self.orphan_timeout_minutes * 60):
                            ports_to_remove.append(port)
                    elif force:
                        ports_to_remove.append(port)
                
                if dry_run:
                    self.logger.info(f"Dry run: Would clean up {len(ports_to_remove)} orphaned ports")
                    return ports_to_remove
                
                # Actually cleanup the ports
                for port in ports_to_remove:
                    allocation = self._allocations[port]
                    
                    # Cleanup container if exists
                    if allocation.container_id:
                        self._cleanup_container(allocation.container_id)
                    
                    # Remove allocation
                    del self._allocations[port]
                    cleaned_ports.append(port)
                
                # Save to disk
                if cleaned_ports:
                    self._save_allocations()
            
            if cleaned_ports:
                self.logger.info(f"Cleaned up {len(cleaned_ports)} orphaned ports: {cleaned_ports}")
            
            return cleaned_ports
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup orphaned ports: {e}")
            return cleaned_ports
    
    def _log_port_usage(
        self,
        port: int,
        action: str,
        metadata: Dict
    ) -> None:
        """Log port usage for tracking."""
        usage_record = {
            "port": port,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        
        self._port_usage_history.append(usage_record)
        
        # Keep only last 1000 records
        if len(self._port_usage_history) > 1000:
            self._port_usage_history = self._port_usage_history[-1000:]
    
    def get_allocation_info(self, port: int) -> Optional[PortAllocation]:
        """
        Get allocation information for a port.
        
        Args:
            port: Port number
            
        Returns:
            PortAllocation object or None if not allocated
        """
        with self._port_lock:
            return self._allocations.get(port)
    
    def get_active_allocations(self) -> List[PortAllocation]:
        """Get list of all active port allocations."""
        with self._port_lock:
            return [
                allocation for allocation in self._allocations.values()
                if allocation.is_active
            ]
    
    def get_port_usage_stats(self) -> Dict:
        """Get port usage statistics."""
        with self._port_lock:
            active_allocations = [
                allocation for allocation in self._allocations.values()
                if allocation.is_active
            ]
            
            return {
                "total_allocations": len(self._allocations),
                "active_allocations": len(active_allocations),
                "inactive_allocations": len(self._allocations) - len(active_allocations),
                "usage_history_count": len(self._port_usage_history),
                "ports_in_use": [allocation.port for allocation in active_allocations]
            }
    
    def heartbeat_port(self, port: int) -> bool:
        """
        Update heartbeat for a port allocation to prevent orphan cleanup.
        
        Args:
            port: Port number to update heartbeat for
            
        Returns:
            True if heartbeat was updated, False otherwise
        """
        with self._port_lock:
            if port in self._allocations and self._allocations[port].is_active:
                self._allocations[port].last_heartbeat = datetime.now().isoformat()
                self._save_allocations()
                return True
            return False
    
    @contextmanager
    def allocated_port(
        self,
        service_type: str = "general",
        allocated_by: str = "context_manager",
        run_id: Optional[str] = None,
        purpose: str = "temporary"
    ):
        """
        Context manager for temporary port allocation.
        
        Args:
            service_type: Type of service
            allocated_by: Component allocating the port
            run_id: Optional run ID
            purpose: Purpose of allocation
            
        Yields:
            Allocated port number
        """
        port = None
        try:
            port = self.allocate_port(
                service_type=service_type,
                allocated_by=allocated_by,
                run_id=run_id,
                purpose=purpose
            )
            yield port
        finally:
            if port is not None:
                self.release_port(port)
    
    def shutdown(self) -> None:
        """Shutdown the port manager and cleanup resources."""
        self.logger.info("Shutting down DockerPortManager")
        
        # Stop cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            # Thread is daemon, so it will be terminated automatically
            self.logger.info("Cleanup thread will terminate automatically")
        
        # Save final state
        self._save_allocations()
        
        self.logger.info("DockerPortManager shutdown complete")


# ============================================================================
# Global Port Manager Instance
# ============================================================================

_global_port_manager: Optional[DockerPortManager] = None


def get_global_port_manager() -> DockerPortManager:
    """
    Get the global port manager instance.
    
    Returns:
        The global DockerPortManager instance
    """
    global _global_port_manager
    if _global_port_manager is None:
        _global_port_manager = DockerPortManager()
    return _global_port_manager


def initialize_global_port_manager(
    state_dir: str = ".trae/port_manager",
    enable_auto_cleanup: bool = True,
    cleanup_interval_seconds: int = 300,
    orphan_timeout_minutes: int = 60
) -> DockerPortManager:
    """
    Initialize the global port manager with custom parameters.
    
    Args:
        state_dir: Directory for storing port allocation state
        enable_auto_cleanup: Enable automatic orphaned port cleanup
        cleanup_interval_seconds: Interval between cleanup operations
        orphan_timeout_minutes: Time before considering a port orphaned
        
    Returns:
        The initialized DockerPortManager instance
    """
    global _global_port_manager
    _global_port_manager = DockerPortManager(
        state_dir=state_dir,
        enable_auto_cleanup=enable_auto_cleanup,
        cleanup_interval_seconds=cleanup_interval_seconds,
        orphan_timeout_minutes=orphan_timeout_minutes
    )
    return _global_port_manager


# ============================================================================
# Utility Functions
# ============================================================================

def find_available_port(
    start_port: int,
    end_port: int,
    exclude_ports: Optional[Set[int]] = None
) -> Optional[int]:
    """
    Find an available port in the given range.
    
    Args:
        start_port: Starting port number
        end_port: Ending port number
        exclude_ports: Set of ports to exclude
        
    Returns:
        Available port number or None if no port is available
    """
    port_manager = get_global_port_manager()
    return port_manager._find_available_port((start_port, end_port), exclude_ports)


def is_port_available(port: int) -> bool:
    """
    Check if a port is available.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is available, False otherwise
    """
    port_manager = get_global_port_manager()
    return port_manager._check_port_available(port)


def get_process_using_port(port: int) -> Optional[str]:
    """
    Get the process using the specified port.
    
    Args:
        port: Port number
        
    Returns:
        Process name or description, or None if port is not in use
    """
    port_manager = get_global_port_manager()
    return port_manager._find_process_using_port(port)