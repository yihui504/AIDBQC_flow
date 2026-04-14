import subprocess

class DockerLogsProbe:
    """
    WBS 2.1: Docker Probe for Deep Observability.
    When a black-box API fails or times out, this probe bypasses the API
    and directly fetches the underlying C++ / Go logs from the Docker container.
    """
    
    def __init__(self, container_name: str = "milvus-standalone"):
        self.container_name = container_name
        self._vector_db_keywords = ["qdrant", "milvus", "weaviate"]

    def fetch_recent_logs(self, tail: int = 100) -> str:
        """Fetch the most recent logs from the target docker container."""
        try:
            # 1. Try with the primary container name
            result = subprocess.run(
                ["docker", "logs", "--tail", str(tail), self.container_name],
                capture_output=True,
                text=True,
                check=False # Don't raise error yet
            )
            
            if result.returncode == 0:
                return (result.stdout + "\n" + result.stderr).strip()
            
            # 2. If failed, try to find a container that looks like Milvus
            print(f"[DockerProbe] Primary container '{self.container_name}' not found. Searching for alternatives...")
            list_cmd = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            containers = list_cmd.stdout.strip().split('\n')
            vdb_containers = [c for c in containers if any(kw in c.lower() for kw in self._vector_db_keywords)]
            
            if vdb_containers:
                alt_name = vdb_containers[0]
                print(f"[DockerProbe] Found alternative container: {alt_name}. Fetching logs...")
                result = subprocess.run(
                    ["docker", "logs", "--tail", str(tail), alt_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return (result.stdout + "\n" + result.stderr).strip()
            
            return f"Failed to fetch docker logs: Container '{self.container_name}' not found and no vector DB (qdrant/milvus/weaviate) alternatives detected."
            
        except Exception as e:
            return f"Failed to fetch docker logs for {self.container_name}: {e}"
