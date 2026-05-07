import os
import json
import chromadb
from datetime import datetime

class BenchmarkExtractor:
    """
    WBS 3.2: AI Evaluation Benchmark Extractor
    Extracts confirmed bugs from the ChromaDB Knowledge Base and formats them 
    into a JSONL dataset that can be used to evaluate other LLMs (like an Eval Harness).
    """
    def __init__(self, db_path: str = "./.trae/chroma_db"):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="defect_kb")
        self.output_dir = "./.trae/benchmarks"
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_to_jsonl(self):
        """Extract all defects and save as an evaluation benchmark dataset."""
        print("[Benchmark Extractor] Fetching historical defects from KB...")
        try:
            # Fetch all documents (in a real scenario, you'd paginate or filter)
            results = self.collection.get()
            
            if not results or not results['documents']:
                print("[Benchmark Extractor] No defects found to extract.")
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"ai_db_qc_benchmark_{timestamp}.jsonl")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for i in range(len(results['documents'])):
                    doc = results['documents'][i]
                    meta = results['metadatas'][i] if results['metadatas'] else {}
                    
                    # Skip meta-strategies, only extract concrete bugs for the benchmark
                    if meta.get("bug_type") == "Meta-Strategy":
                        continue
                        
                    benchmark_item = {
                        "task_id": meta.get("case_id", f"task_{i}"),
                        "category": meta.get("bug_type", "Unknown"),
                        "input_context": "Vector Database Fuzzing Scenario",
                        "expected_defect_pattern": doc,
                        "difficulty": meta.get("evidence_level", "Unknown")
                    }
                    f.write(json.dumps(benchmark_item, ensure_ascii=False) + '\n')
                    
            print(f"[Benchmark Extractor] Successfully extracted {len(results['documents'])} items to {output_file}")
            print("[Benchmark Extractor] This dataset can now be used with tools like EleutherAI LM Harness or Anthropic Inspect to evaluate LLMs.")
            
        except Exception as e:
            print(f"[Benchmark Extractor] Failed to extract benchmark: {e}")

if __name__ == "__main__":
    extractor = BenchmarkExtractor()
    extractor.extract_to_jsonl()
