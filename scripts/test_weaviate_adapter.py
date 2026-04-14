"""
Test script for WeaviateAdapter in live Docker environment.
Tests all major operations: connect, create collection, insert, search, cleanup.
"""

import sys
import os
import random
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.db_adapter import WeaviateAdapter


def generate_random_vector(dimension: int):
    """Generate a random normalized vector."""
    vec = [random.gauss(0, 1) for _ in range(dimension)]
    magnitude = sum(x * x for x in vec) ** 0.5
    return [x / magnitude for x in vec]


def main():
    print("=" * 60)
    print("WeaviateAdapter Live Test")
    print("=" * 60)
    
    # Configuration
    WEAVIATE_HOST = "localhost"
    WEAVIATE_PORT = "8081"  # Mapped from container port 8080
    TEST_COLLECTION = "TestCollection"
    DIMENSION = 128
    NUM_VECTORS = 10
    
    results = {
        "connect": None,
        "create_collection": None,
        "insert_data": None,
        "search": None,
        "cleanup": None,
        "disconnect": None
    }
    
    # Step 1: Create adapter instance
    print("\n[Step 1] Creating WeaviateAdapter instance...")
    try:
        adapter = WeaviateAdapter(f"{WEAVIATE_HOST}:{WEAVIATE_PORT}")
        print("[Step 1] SUCCESS - Adapter instance created")
    except Exception as e:
        print(f"[Step 1] FAILED - {e}")
        return results
    
    # Step 2: Connect to Weaviate
    print("\n[Step 2] Connecting to Weaviate...")
    try:
        success = adapter.connect()
        if success:
            print(f"[Step 2] SUCCESS - Connected to Weaviate at {WEAVIATE_HOST}:{WEAVIATE_PORT}")
            results["connect"] = True
        else:
            print(f"[Step 2] FAILED - Connection returned False")
            results["connect"] = False
    except Exception as e:
        print(f"[Step 2] FAILED - {e}")
        results["connect"] = False
        import traceback
        traceback.print_exc()
    
    if not results["connect"]:
        print("\nCannot proceed without connection. Exiting.")
        return results
    
    # Step 3: Create test collection
    print(f"\n[Step 3] Creating test collection (dimension={DIMENSION})...")
    try:
        success = adapter.initialize_collection(TEST_COLLECTION, DIMENSION, "L2")
        if success:
            print(f"[Step 3] SUCCESS - Collection created/initialized")
            results["create_collection"] = True
            collection_name = adapter.current_collection_name
            print(f"           Collection name: {collection_name}")
        else:
            print(f"[Step 3] FAILED - initialize_collection returned False")
            results["create_collection"] = False
    except Exception as e:
        print(f"[Step 3] FAILED - {e}")
        results["create_collection"] = False
        import traceback
        traceback.print_exc()
    
    if not results["create_collection"]:
        print("\nCannot proceed without collection. Cleaning up...")
        adapter.disconnect()
        return results
    
    # Step 4: Insert test vectors
    print(f"\n[Step 4] Inserting {NUM_VECTORS} test vectors...")
    try:
        vectors = [generate_random_vector(DIMENSION) for _ in range(NUM_VECTORS)]
        payloads = [{"id": i, "data": f"test_data_{i}", "value": random.random()} for i in range(NUM_VECTORS)]
        
        collection_name = adapter.current_collection_name
        success = adapter.insert_data(collection_name, vectors, payloads)
        
        if success:
            print(f"[Step 4] SUCCESS - Inserted {NUM_VECTORS} vectors")
            results["insert_data"] = True
        else:
            print(f"[Step 4] FAILED - insert_data returned False")
            results["insert_data"] = False
    except Exception as e:
        print(f"[Step 4] FAILED - {e}")
        results["insert_data"] = False
        import traceback
        traceback.print_exc()
    
    # Step 5: Perform search query
    print(f"\n[Step 5] Performing search query...")
    try:
        query_vector = generate_random_vector(DIMENSION)
        collection_name = adapter.current_collection_name
        
        search_result = adapter.search(collection_name, query_vector, top_k=5)
        
        if search_result.get("success"):
            hits = search_result.get("hits", [])
            print(f"[Step 5] SUCCESS - Search returned {len(hits)} results")
            results["search"] = True
            
            # Print sample results
            for i, hit in enumerate(hits[:3]):
                print(f"           Hit {i+1}: id={hit.get('id')}, distance={hit.get('distance')}")
        else:
            error = search_result.get("error", "Unknown error")
            print(f"[Step 5] FAILED - Search failed: {error}")
            results["search"] = False
    except Exception as e:
        print(f"[Step 5] FAILED - {e}")
        results["search"] = False
        import traceback
        traceback.print_exc()
    
    # Step 6: Cleanup - Delete test collection
    print(f"\n[Step 6] Cleaning up (deleting test collection)...")
    try:
        collection_name = adapter.current_collection_name
        # For pooled collections, teardown_harness skips deletion
        # We need to manually delete for testing
        if collection_name:
            # Check if it's a pooled collection
            is_pooled = any(name == collection_name for name in adapter.collection_pool.values())
            
            if is_pooled:
                # Remove from pool first to allow deletion
                for dim, name in list(adapter.collection_pool.items()):
                    if name == collection_name:
                        del adapter.collection_pool[dim]
                        break
            
            # Now delete the collection
            adapter.client.collections.delete(collection_name)
            print(f"[Step 6] SUCCESS - Collection '{collection_name}' deleted")
            results["cleanup"] = True
        else:
            print(f"[Step 6] SKIPPED - No collection to delete")
            results["cleanup"] = True
    except Exception as e:
        print(f"[Step 6] FAILED - {e}")
        results["cleanup"] = False
        import traceback
        traceback.print_exc()
    
    # Step 7: Disconnect
    print(f"\n[Step 7] Disconnecting from Weaviate...")
    try:
        adapter.disconnect()
        print(f"[Step 7] SUCCESS - Disconnected")
        results["disconnect"] = True
    except Exception as e:
        print(f"[Step 7] FAILED - {e}")
        results["disconnect"] = False
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for step, result in results.items():
        status = "PASSED" if result else ("FAILED" if result is False else "SKIPPED")
        if result is False:
            all_passed = False
        print(f"  {step}: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - See details above")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
