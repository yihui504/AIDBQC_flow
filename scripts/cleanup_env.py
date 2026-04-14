#!/usr/bin/env python3
"""
环境清理脚本 - 清理Docker容器、卷、缓存与运行态状态

功能：
1. 停止并删除所有相关Docker容器（weaviate, milvus, qdrant相关）
2. 清理Docker卷（weaviate_data等）
3. 清理.trae/runs/目录下的旧运行数据（但保留最近的运行目录）
4. 清理.trae/cache/目录
5. 清理.trae/monitoring/和.trae/monitor_alerts/目录
6. 清理.trae/error_reports/和.trae/error_knowledge_base/目录
7. 清理.trae/mres/目录
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class CleanupReport:
    """清理报告收集器"""

    def __init__(self):
        self.start_time = datetime.now()
        self.sections: Dict[str, dict] = {}

    def add_section(self, name: str, success: bool, message: str, details: Optional[List[str]] = None):
        self.sections[name] = {
            "success": success,
            "message": message,
            "details": details or [],
            "timestamp": datetime.now().isoformat()
        }

    def add_detail(self, name: str, detail: str):
        if name in self.sections and "details" in self.sections[name]:
            self.sections[name]["details"].append(detail)

    def get_summary(self) -> str:
        elapsed = datetime.now() - self.start_time
        total = len(self.sections)
        successful = sum(1 for s in self.sections.values() if s["success"])
        failed = total - successful

        summary_lines = [
            "=" * 60,
            "环境清理报告",
            "=" * 60,
            f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"耗时: {elapsed.total_seconds():.2f} 秒",
            f"总步骤: {total} | 成功: {successful} | 失败: {failed}",
            "-" * 60,
        ]

        for name, section in self.sections.items():
            status = "SUCCESS" if section["success"] else "FAILED"
            summary_lines.append(f"\n[{status}] {name}")
            summary_lines.append(f"  {section['message']}")
            if section["details"]:
                for detail in section["details"]:
                    summary_lines.append(f"    - {detail}")

        summary_lines.append("\n" + "=" * 60)
        return "\n".join(summary_lines)


class EnvironmentCleaner:
    """环境清理器"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.trae_dir = self.project_root / ".trae"
        self.report = CleanupReport()

        # Docker compose 文件
        self.docker_compose_files = [
            self.project_root / "docker-compose.weaviate.yml",
            self.project_root / "docker-compose.milvus.yml",
            self.project_root / "docker-compose.qdrant.yml",
        ]

        # Docker 相关容器名称
        self.target_containers = [
            "weaviate",
            "milvus-etcd",
            "milvus-minio",
            "milvus-standalone",
            "qdrant",
        ]

        # Docker 卷名称
        self.target_volumes = [
            "weaviate_data",
            "milvus-etcd",
            "milvus-minio",
            "milvus-data",
            "qdrant_storage",
        ]

        # .trae 下的清理目录
        self.trae_cleanup_dirs = [
            ("runs", True),  # (目录名, 是否保留最近)
            ("cache", False),
            ("monitoring", False),
            ("monitor_alerts", False),
            ("error_reports", False),
            ("error_knowledge_base", False),
            ("mres", False),
        ]

    def run_command(self, cmd: List[str], description: str, capture: bool = True) -> Tuple[bool, str]:
        """执行 shell 命令"""
        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=120
                )
                success = result.returncode == 0
                output = result.stdout if success else result.stderr
                return success, output
            else:
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    timeout=120
                )
                return result.returncode == 0, ""
        except subprocess.TimeoutExpired:
            return False, f"{description} - 命令执行超时"
        except Exception as e:
            return False, f"{description} - 错误: {str(e)}"

    def check_docker_status(self) -> Dict[str, any]:
        """检查 Docker 容器运行状态"""
        status = {
            "docker_available": False,
            "running_containers": [],
            "target_containers_running": [],
            "total_containers": 0,
        }

        # 检查 Docker 是否可用
        success, output = self.run_command(["docker", "info"], "检查 Docker 是否可用")
        status["docker_available"] = success

        if not success:
            return status

        # 获取所有运行中的容器
        success, output = self.run_command(
            ["docker", "ps", "--format", "{{.Names}}"],
            "获取运行中的容器"
        )

        if success:
            status["running_containers"] = [c for c in output.strip().split("\n") if c]
            status["total_containers"] = len(status["running_containers"])
            status["target_containers_running"] = [
                c for c in status["running_containers"]
                if any(t in c for t in ["weaviate", "milvus", "qdrant"])
            ]

        return status

    def cleanup_docker_compose(self) -> Tuple[bool, str, List[str]]:
        """使用 docker-compose down -v 清理相关卷"""
        details = []
        any_success = False

        for compose_file in self.docker_compose_files:
            if not compose_file.exists():
                details.append(f"跳过 {compose_file.name} (文件不存在)")
                continue

            details.append(f"处理 {compose_file.name}...")
            success, output = self.run_command(
                ["docker-compose", "-f", compose_file.name, "down", "-v"],
                f"清理 {compose_file.name}"
            )

            if success:
                any_success = True
                details.append(f"  {compose_file.name} - 清理成功")
            else:
                details.append(f"  {compose_file.name} - 清理失败: {output[:200]}")

        return any_success, "Docker Compose 清理完成", details

    def cleanup_docker_prune(self) -> Tuple[bool, str, List[str]]:
        """使用 docker container prune 清理孤立容器"""
        details = []

        # 清理已停止的容器
        success, output = self.run_command(
            ["docker", "container", "prune", "-f"],
            "清理孤立容器"
        )

        if success:
            details.append("孤立容器清理成功")
        else:
            details.append(f"孤立容器清理失败: {output[:200]}")

        return success, "Docker 容器清理完成", details

    def cleanup_docker_volumes(self) -> Tuple[bool, str, List[str]]:
        """清理孤立的 Docker 卷"""
        details = []

        # 清理未使用的卷
        success, output = self.run_command(
            ["docker", "volume", "prune", "-f"],
            "清理未使用的卷"
        )

        if success:
            details.append("未使用卷清理成功")
        else:
            details.append(f"卷清理失败: {output[:200]}")

        return success, "Docker 卷清理完成", details

    def cleanup_trafe_dir(self, dir_name: str, keep_recent: bool = False, keep_count: int = 1) -> Tuple[bool, str, List[str]]:
        """清理 .trae 下的指定目录"""
        details = []
        target_dir = self.trae_dir / dir_name

        if not target_dir.exists():
            details.append(f"{dir_name} 目录不存在，跳过")
            return True, f"{dir_name} 清理完成 (目录不存在)", details

        if not target_dir.is_dir():
            details.append(f"{dir_name} 不是目录，跳过")
            return False, f"{dir_name} 清理失败 (不是目录)", details

        if keep_recent:
            # 获取所有子目录（按修改时间排序）
            subdirs = [d for d in target_dir.iterdir() if d.is_dir()]
            subdirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(subdirs) <= keep_count:
                details.append(f"保留 {keep_count} 个最近目录:")
                for d in subdirs:
                    details.append(f"  - {d.name}")
                details.append(f"{dir_name} 无需清理（目录数量 <= {keep_count}）")
                return True, f"{dir_name} 清理完成 (无需清理)", details

            # 删除旧目录
            dirs_to_remove = subdirs[keep_count:]
            dirs_to_keep = subdirs[:keep_count]

            details.append(f"保留 {keep_count} 个最近目录:")
            for d in dirs_to_keep:
                details.append(f"  - {d.name}")

            details.append(f"删除 {len(dirs_to_remove)} 个旧目录:")
            for d in dirs_to_remove:
                try:
                    shutil.rmtree(d)
                    details.append(f"  - 删除: {d.name}")
                except Exception as e:
                    details.append(f"  - 删除失败: {d.name} ({str(e)})")
        else:
            # 清空整个目录
            try:
                for item in target_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                details.append(f"已清空 {dir_name} 目录")
            except Exception as e:
                return False, f"{dir_name} 清理失败", [f"清空目录失败: {str(e)}"]

        return True, f"{dir_name} 清理完成", details

    def cleanup_all_trafe_dirs(self) -> Tuple[bool, str, List[str]]:
        """清理所有 .trae 下的目标目录"""
        all_details = []
        any_success = True

        for dir_name, keep_recent in self.trae_cleanup_dirs:
            success, message, details = self.cleanup_trafe_dir(dir_name, keep_recent)
            any_success = any_success and success
            all_details.extend(details)
            all_details.append("")  # 空行分隔

        return any_success, ".trae 目录清理完成", all_details

    def run(self) -> CleanupReport:
        """执行完整的环境清理"""
        print("开始环境清理...")
        print()

        # 1. 检查 Docker 状态
        print("[1/7] 检查 Docker 容器状态...")
        status = self.check_docker_status()

        if not status["docker_available"]:
            print("  Docker 不可用，跳过 Docker 相关清理")
            self.report.add_section(
                "Docker 状态检查",
                False,
                "Docker 不可用",
                ["请确保 Docker 已安装并运行"]
            )
        else:
            print(f"  运行中的容器总数: {status['total_containers']}")
            if status["target_containers_running"]:
                print(f"  目标容器运行中: {', '.join(status['target_containers_running'])}")
            else:
                print("  无目标容器运行")

            self.report.add_section(
                "Docker 状态检查",
                True,
                f"运行中容器: {status['total_containers']}, 目标容器: {len(status['target_containers_running'])}",
                status["running_containers"] if status["running_containers"] else ["无运行中的容器"]
            )

        # 2. 清理 Docker Compose 卷
        print("[2/7] 清理 Docker Compose 卷...")
        success, message, details = self.cleanup_docker_compose()
        self.report.add_section("Docker Compose 清理", success, message, details)
        print(f"  {message}")

        # 3. 清理孤立容器
        print("[3/7] 清理孤立 Docker 容器...")
        success, message, details = self.cleanup_docker_prune()
        self.report.add_section("Docker 容器清理", success, message, details)
        print(f"  {message}")

        # 4. 清理 Docker 卷
        print("[4/7] 清理 Docker 孤立的卷...")
        success, message, details = self.cleanup_docker_volumes()
        self.report.add_section("Docker 卷清理", success, message, details)
        print(f"  {message}")

        # 5. 清理 .trae 目录
        print("[5/7] 清理 .trae 目录...")
        success, message, details = self.cleanup_all_trafe_dirs()
        self.report.add_section(".trae 目录清理", success, message, details)
        print(f"  {message}")

        # 6. 最终状态检查
        print("[6/7] 执行最终状态检查...")
        final_status = self.check_docker_status()
        target_still_running = [
            c for c in final_status["running_containers"]
            if any(t in c for t in ["weaviate", "milvus", "qdrant"])
        ]

        if target_still_running:
            self.report.add_section(
                "最终状态检查",
                False,
                "仍有目标容器在运行",
                target_still_running
            )
        else:
            self.report.add_section(
                "最终状态检查",
                True,
                "所有目标容器已停止",
                ["环境清理成功完成"]
            )

        # 7. 打印清理报告
        print("[7/7] 生成清理报告...")
        print()
        print(self.report.get_summary())

        # 保存报告到文件
        report_file = self.trae_dir / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            report_data = {
                "timestamp": self.report.start_time.isoformat(),
                "elapsed_seconds": (datetime.now() - self.report.start_time).total_seconds(),
                "sections": self.report.sections
            }
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n报告已保存到: {report_file}")
        except Exception as e:
            print(f"\n报告保存失败: {e}")

        return self.report


def main():
    """主函数"""
    # 获取项目根目录
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    print(f"项目根目录: {project_root}")
    print()

    # 确认操作
    print("警告: 此脚本将执行以下操作:")
    print("  - 停止并删除所有 weaviate, milvus, qdrant 相关容器")
    print("  - 删除所有相关的 Docker 卷")
    print("  - 清理 .trae/runs/ 目录（保留最近的运行目录）")
    print("  - 清空 .trae/cache/ 目录")
    print("  - 清空 .trae/monitoring/ 和 .trae/monitor_alerts/ 目录")
    print("  - 清空 .trae/error_reports/ 和 .trae/error_knowledge_base/ 目录")
    print("  - 清空 .trae/mres/ 目录")
    print()

    # 创建清理器并执行
    cleaner = EnvironmentCleaner(project_root)
    report = cleaner.run()

    # 返回退出码
    failed_sections = [name for name, s in report.sections.items() if not s["success"]]
    if failed_sections:
        print(f"\n警告: 以下步骤失败: {', '.join(failed_sections)}")
        sys.exit(1)
    else:
        print("\n环境清理成功完成!")
        sys.exit(0)


if __name__ == "__main__":
    main()
