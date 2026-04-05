"""
AI-DB-QC 文档增强功能性能基准测试
Phase 3.2: 性能基准测试
"""
import time
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.knowledge_base import DefectKnowledgeBase, BugRecord
from src.validators.reference_validator import ReferenceValidator


def seed_test_data(kb, count: int = 100):
    """生成测试数据并填充知识库

    Args:
        kb: DefectKnowledgeBase 实例
        count: 生成的测试数据数量
    """
    import random

    bug_types = ["Type-1", "Type-2", "Type-3", "Type-4"]
    dbs = ["milvus", "qdrant", "weaviate", "pgvector"]
    versions = ["v2.3.0", "v1.7.0", "v1.20.0", "0.5.0"]

    # 测试约束关键词
    constraints = [
        "dimension", "metric", "top_k", "index", "HNSW", "IVF",
        "payload", "collection", "filter", "distance", "L2", "COSINE"
    ]

    error_messages = [
        "Dimension exceeds maximum",
        "Invalid metric type",
        "Index creation failed",
        "Filter not working",
        "Top_k returns wrong count",
        "Payload size too large"
    ]

    print(f"[Benchmark] 生成 {count} 条测试数据...")

    for i in range(count):
        # 生成随机缺陷描述
        constraint = random.choice(constraints)
        error = random.choice(error_messages)
        db = random.choice(dbs)
        version = random.choice(versions)

        root_cause = f"{db} {error}: {constraint} constraint violation in {version}"

        kb.add_defect(BugRecord(
            case_id=f"test-{i:04d}",
            bug_type=random.choice(bug_types),
            root_cause_analysis=root_cause,
            evidence_level=random.choice(["L1", "L2", "L3"]),
            related_db=db,
            related_version=version,
            error_message=error,
            reproduction_steps=f"1. Create collection with invalid {constraint}\n2. Attempt operation\n3. Error occurs"
        ))

    print(f"[Benchmark] 完成 {count} 条测试数据生成")


def benchmark_crawling():
    """基准测试：文档爬取性能

    目标:
    - 爬取时间 < 30s/数据库
    - 内容长度 > 10K 字符
    - URL 数量 >= 5
    """
    print("\n" + "="*60)
    print("基准测试 1: 文档爬取性能")
    print("="*60)

    from src.agents.agent0_env_recon import EnvReconAgent, DBInfo

    agent = EnvReconAgent()

    # 测试数据集（使用真实数据库）
    test_dbs = [
        ("milvus", "v2.3.0"),
        # ("qdrant", "v1.7.0"),  # 可选：测试更多数据库
        # ("weaviate", "v1.20.0"),
    ]

    results = []

    for db_name, version in test_dbs:
        print(f"\n[测试] 爬取 {db_name} {version} 文档...")

        try:
            start = time.time()

            # 执行文档爬取
            db_info = DBInfo(db_name=db_name, version=version)
            docs = agent._fetch_documentation(db_info)

            elapsed = time.time() - start

            # 分析结果
            content_length = len(docs)
            urls_found = docs.count("Source:")
            urls_per_source = docs.count("http")

            result = {
                "db": db_name,
                "version": version,
                "time_seconds": round(elapsed, 2),
                "content_length": content_length,
                "urls_found": urls_found,
                "success": elapsed < 30.0 and content_length > 10000
            }
            results.append(result)

            # 打印结果
            print(f"  耗时: {elapsed:.2f}s {'✓' if elapsed < 30 else '✗'} (目标: < 30s)")
            print(f"  内容长度: {content_length:,} 字符 {'✓' if content_length > 10000 else '✗'} (目标: > 10K)")
            print(f"  发现URL: {urls_found} 个 {'✓' if urls_found >= 5 else '✗'} (目标: >= 5)")

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results.append({
                "db": db_name,
                "version": version,
                "error": str(e),
                "success": False
            })

    # 总结
    print("\n[总结]")
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"  通过: {success_count}/{len(results)}")

    return results


def benchmark_rag_search():
    """基准测试：RAG 搜索性能

    目标:
    - 搜索延迟 < 2s/查询
    - 相关性得分 > 0.5
    - 返回结果数量 = top_k
    """
    print("\n" + "="*60)
    print("基准测试 2: RAG 搜索性能")
    print("="*60)

    kb = DefectKnowledgeBase()

    # 生成测试数据
    seed_test_data(kb, count=100)

    # 测试查询集
    test_queries = [
        "dimension limit exceeded",
        "index type HNSW error",
        "metric COSINE not supported",
        "top_k returns wrong results",
        "payload size constraint violation",
        "collection filter not working",
        "L2 distance metric bug",
        "IVF index creation failed"
    ]

    print(f"\n[测试] 执行 {len(test_queries)} 个查询...")

    latencies = []
    relevance_scores = []

    for query in test_queries:
        start = time.time()

        results = kb.search_similar_defects(query, top_k=5, alpha=0.7)

        elapsed = time.time() - start
        latencies.append(elapsed)

        # 收集相关性得分
        if results:
            relevance_scores.append(results[0].get("combined_score", 0))

        status = "✓" if elapsed < 2.0 else "✗"
        print(f"  查询: '{query[:30]}...' -> {elapsed:.3f}s {status} (返回 {len(results)} 条结果)")

    # 统计
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

    print(f"\n[统计]")
    print(f"  平均延迟: {avg_latency:.3f}s {'✓' if avg_latency < 2.0 else '✗'} (目标: < 2s)")
    print(f"  最大延迟: {max_latency:.3f}s")
    print(f"  平均相关性: {avg_relevance:.3f} {'✓' if avg_relevance > 0.5 else '✗'} (目标: > 0.5)")

    return {
        "avg_latency": avg_latency,
        "max_latency": max_latency,
        "avg_relevance": avg_relevance,
        "success": avg_latency < 2.0 and avg_relevance > 0.5
    }


def benchmark_reference_validation():
    """基准测试：引用验证性能

    目标:
    - 验证时间 < 1s/引用
    - 准确率 > 80%
    """
    print("\n" + "="*60)
    print("基准测试 3: 引用验证性能")
    print("="*60)

    validator = ReferenceValidator(threshold=0.65)

    # 测试用例
    test_cases = [
        {
            "bug": "Vector dimension exceeds maximum",
            "doc": "Maximum dimension is 32768 for all collections.",
            "expected_relevant": True
        },
        {
            "bug": "HNSW index configuration error",
            "doc": "HNSW index parameters include M and ef_construction.",
            "expected_relevant": True
        },
        {
            "bug": "Top_k returns incorrect results",
            "doc": "Python client installation guide for Windows.",
            "expected_relevant": False
        },
        {
            "bug": "Filter expression syntax error",
            "doc": "Filter expressions support logical operators AND, OR, NOT.",
            "expected_relevant": True
        },
        {
            "bug": "Connection timeout error",
            "doc": "Qdrant REST API reference documentation.",
            "expected_relevant": False
        }
    ]

    print(f"\n[测试] 验证 {len(test_cases)} 个引用...")

    latencies = []
    correct = 0

    for i, case in enumerate(test_cases, 1):
        start = time.time()

        is_relevant, score, reasoning = validator.validate_reference(
            case["bug"],
            case["doc"],
            f"https://example.com/docs/{i}"
        )

        elapsed = time.time() - start
        latencies.append(elapsed)

        # 检查准确性
        is_correct = is_relevant == case["expected_relevant"]
        if is_correct:
            correct += 1

        status = "✓" if is_correct else "✗"
        expected = "相关" if case["expected_relevant"] else "不相关"
        actual = "相关" if is_relevant else "不相关"

        print(f"  测试 {i}: {elapsed:.3f}s {status} (预期: {expected}, 实际: {actual}, 得分: {score:.2f})")

    # 统计
    avg_latency = sum(latencies) / len(latencies)
    accuracy = correct / len(test_cases)

    print(f"\n[统计]")
    print(f"  平均延迟: {avg_latency:.3f}s {'✓' if avg_latency < 1.0 else '✗'} (目标: < 1s)")
    print(f"  准确率: {accuracy:.1%} {'✓' if accuracy > 0.8 else '✗'} (目标: > 80%)")

    return {
        "avg_latency": avg_latency,
        "accuracy": accuracy,
        "success": avg_latency < 1.0 and accuracy > 0.8
    }


def benchmark_memory_usage():
    """基准测试：内存使用

    目标:
    - 1000 条缺陷内存使用 < 2GB
    """
    print("\n" + "="*60)
    print("基准测试 4: 内存使用")
    print("="*60)

    import psutil
    import gc

    process = psutil.Process()

    # 记录初始内存
    gc.collect()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"[测试] 初始内存: {initial_memory:.1f} MB")

    # 创建知识库并添加数据
    kb = DefectKnowledgeBase()

    # 添加不同数量的缺陷并测量内存
    test_sizes = [100, 500, 1000]

    memory_results = []

    for size in test_sizes:
        # 清理并创建新知识库
        kb = DefectKnowledgeBase()
        gc.collect()

        seed_test_data(kb, count=size)

        gc.collect()
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        result = {
            "size": size,
            "memory_mb": round(current_memory, 1),
            "increase_mb": round(memory_increase, 1)
        }
        memory_results.append(result)

        status = "✓" if current_memory < 2048 else "✗"
        print(f"  {size} 条缺陷: {current_memory:.1f} MB (+{memory_increase:.1f} MB) {status}")

    # 检查 1000 条是否在限制内
    result_1000 = next((r for r in memory_results if r["size"] == 1000), None)
    success = result_1000 and result_1000["memory_mb"] < 2048

    print(f"\n[总结]")
    print(f"  1000条缺陷内存: {result_1000['memory_mb'] if result_1000 else 'N/A'} MB {'✓' if success else '✗'} (目标: < 2GB)")

    return {
        "memory_results": memory_results,
        "success": success
    }


def run_all_benchmarks():
    """运行所有基准测试"""
    print("\n" + "="*60)
    print("AI-DB-QC 文档增强功能 - 性能基准测试套件")
    print("="*60)

    all_results = {}

    try:
        all_results["crawling"] = benchmark_crawling()
    except Exception as e:
        print(f"\n✗ 爬取基准测试失败: {e}")
        all_results["crawling"] = {"success": False, "error": str(e)}

    try:
        all_results["rag_search"] = benchmark_rag_search()
    except Exception as e:
        print(f"\n✗ RAG搜索基准测试失败: {e}")
        all_results["rag_search"] = {"success": False, "error": str(e)}

    try:
        all_results["reference_validation"] = benchmark_reference_validation()
    except Exception as e:
        print(f"\n✗ 引用验证基准测试失败: {e}")
        all_results["reference_validation"] = {"success": False, "error": str(e)}

    try:
        all_results["memory_usage"] = benchmark_memory_usage()
    except Exception as e:
        print(f"\n✗ 内存使用基准测试失败: {e}")
        all_results["memory_usage"] = {"success": False, "error": str(e)}

    # 最终总结
    print("\n" + "="*60)
    print("最终总结")
    print("="*60)

    passed = sum(1 for r in all_results.values() if r.get("success", False))
    total = len(all_results)

    for name, result in all_results.items():
        status = "✓ 通过" if result.get("success", False) else "✗ 失败"
        print(f"  {name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    return all_results


if __name__ == "__main__":
    results = run_all_benchmarks()

    # 退出码
    all_passed = all(r.get("success", False) for r in results.values())
    sys.exit(0 if all_passed else 1)
