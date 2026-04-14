"""
Test script for QdrantAdapter in live Docker environment.
Tests all major operations: connect, create collection, insert, search, cleanup, disconnect.
"""

import sys
import os
import random
import time

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.adapters.db_adapter import QdrantAdapter


def generate_random_vector(dimension: int) -> list:
    """Generate a random vector of given dimension."""
    return [random.uniform(-1.0, 1.0) for _ in range(dimension)]


def main():
    print("=" * 60)
    print("QdrantAdapter Live Environment Test")
    print("=" * 60)
    
    # Test configuration
    endpoint = "localhost:6333"
    test_collection = "test_collection_128"
    dimension = 128
    num_vectors = 10
    
    results = {
        "connect": None,
        "create_collection": None,
        "insert_data": None,
        "search": None,
        "cleanup": None,
        "disconnect": None
    }
    
    # Step 1: Initialize adapter
    print("\n[Step 1] Initializing QdrantAdapter...")
    try:
        adapter = QdrantAdapter(endpoint)
        print(f"  [OK] Adapter initialized with endpoint: {endpoint}")
    except Exception as e:
        print(f"  [FAIL] Failed to initialize adapter: {e}")
        return
    
    # Step 2: Connect
    print("\n[Step 2] Connecting to Qdrant...")
    try:
        success = adapter.connect()
        if success:
            print(f"  [OK] Connected to Qdrant at {endpoint}")
            results["connect"] = True
        else:
            print(f"  [FAIL] Connection returned False")
            results["connect"] = False
    except Exception as e:
        print(f"  [FAIL] Connection failed with exception: {e}")
        results["connect"] = False
    
    if not results["connect"]:
        print("\nCannot proceed without connection. Exiting.")
        return
    
    # Step 3: Create collection
    print(f"\n[Step 3] Creating test collection '{test_collection}' with dimension {dimension}...")
    try:
        # First, delete if exists
        try:
            adapter.client.delete_collection(test_collection)
            print(f"  [INFO] Deleted existing collection")
            time.sleep(0.5)
        except:
            pass
        
        # Create new collection directly (not using pool)
        from qdrant_client.http.models import Distance, VectorParams
        adapter.client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.EUCLID)
        )
        print(f"  [OK] Collection '{test_collection}' created")
        results["create_collection"] = True
        time.sleep(0.5)
    except Exception as e:
        print(f"  [FAIL] Failed to create collection: {e}")
        import traceback
        traceback.print_exc()
        results["create_collection"] = False
    
    # Step 4: Insert test vectors
    print(f"\n[Step 4] Inserting {num_vectors} test vectors...")
    try:
        vectors = [generate_random_vector(dimension) for _ in range(num_vectors)]
        payloads = [{"index": i, "type": "test", "timestamp": time.time()} for i in range(num_vectors)]
        
        # Use insert_data method
        success = adapter.insert_data(test_collection, vectors, payloads)
        if success:
            print(f"  [OK] Inserted {num_vectors} vectors")
            results["insert_data"] = True
        else:
            print(f"  [FAIL] insert_data returned False")
            results["insert_data"] = False
    except Exception as e:
        print(f"  [FAIL] Failed to insert data: {e}")
        import traceback
        traceback.print_exc()
        results["insert_data"] = False
    
    # Step 5: Perform search
    print(f"\n[Step 5] Performing search query...")
    try:
        query_vector = generate_random_vector(dimension)
        search_result = adapter.search(test_collection, query_vector, top_k=5)
        
        if search_result.get("success"):
            hits = search_result.get("hits", [])
            print(f"  [OK] Search returned {len(hits)} results")
            for i, hit in enumerate(hits[:3]):  # Show top 3
                print(f"       Hit {i+1}: id={hit.get('id')}, distance={hit.get('distance'):.4f}")
            results["search"] = True
        else:
            error = search_result.get("error", "Unknown error")
            print(f"  [FAIL] Search failed: {error}")
            results["search"] = False
    except Exception as e:
        print(f"  [FAIL] Search failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["search"] = False
    
    # Step 6: Cleanup - delete collection
    print(f"\n[Step 6] Cleaning up (deleting collection '{test_collection}')...")
    try:
        adapter.client.delete_collection(test_collection)
        print(f"  [OK] Collection '{test_collection}' deleted")
        results["cleanup"] = True
    except Exception as e:
        print(f"  [FAIL] Failed to delete collection: {e}")
        results["cleanup"] = False
    
    # Step 7: Disconnect
    print(f"\n[Step 7] Disconnecting...")
    try:
        adapter.disconnect()
        print(f"  [OK] Disconnected from Qdrant")
        results["disconnect"] = True
    except Exception as e:
        print(f"  [FAIL] Disconnect failed: {e}")
        results["disconnect"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for step, result in results.items():
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"  {step}: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - See details above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    main()
