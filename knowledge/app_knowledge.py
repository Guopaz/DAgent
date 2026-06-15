"""App 知识库：加载、查询、动态注入页面结构和操作流程"""
import json
import os
from pathlib import Path


class AppKnowledge:
    """管理目标 App 的知识库，包括页面结构、元素地图、操作流程"""

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.apps: dict[str, dict] = {}
        self._load_all_apps()

    def _load_all_apps(self):
        """加载 knowledge 目录下所有 App 的知识库"""
        if not self.knowledge_dir.exists():
            return
        for app_dir in self.knowledge_dir.iterdir():
            if app_dir.is_dir() and (app_dir / "app.json").exists():
                try:
                    with open(app_dir / "app.json") as f:
                        app_data = json.load(f)
                    bundle_id = app_data.get("bundle_id", app_dir.name)
                    self.apps[bundle_id] = {
                        "data": app_data,
                        "dir": app_dir,
                    }
                except Exception as e:
                    print(f"⚠️  加载知识库 {app_dir.name} 失败: {e}")

    def get_app_info(self, bundle_id: str) -> dict | None:
        """获取 App 基本信息"""
        app = self.apps.get(bundle_id)
        return app["data"] if app else None

    def get_page_knowledge(self, bundle_id: str, page_name: str) -> dict | None:
        """获取指定页面的知识结构"""
        app = self.apps.get(bundle_id)
        if not app:
            return None
        pages = app["data"].get("pages", {})
        return pages.get(page_name)

    def get_element_map(self, bundle_id: str, page_name: str) -> str:
        """获取页面的元素地图（精简文本格式，用于注入 prompt）"""
        page = self.get_page_knowledge(bundle_id, page_name)
        if not page:
            return ""
        elements = page.get("elements", [])
        if not elements:
            return ""
        lines = [f"页面 [{page_name}] 的关键元素："]
        for elem in elements:
            label = elem.get("label", "")
            strategy = elem.get("strategy", "")
            value = elem.get("value", "")
            desc = elem.get("description", "")
            parts = []
            if label:
                parts.append(f'"{label}"')
            if strategy and value:
                parts.append(f"({strategy}={value})")
            if desc:
                parts.append(f"- {desc}")
            lines.append("  " + " ".join(parts))
        return "\n".join(lines)

    def get_flow(self, bundle_id: str, flow_name: str) -> str:
        """获取操作流程描述"""
        app = self.apps.get(bundle_id)
        if not app:
            return ""
        flows = app["data"].get("flows", {})
        flow = flows.get(flow_name)
        if not flow:
            return ""
        lines = [f"操作流程 [{flow_name}]："]
        for i, step in enumerate(flow, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)

    def get_all_flows_summary(self, bundle_id: str) -> str:
        """获取 App 所有操作流程的摘要"""
        app = self.apps.get(bundle_id)
        if not app:
            return ""
        flows = app["data"].get("flows", {})
        if not flows:
            return ""
        lines = [f"App [{bundle_id}] 支持的操作流程："]
        for name, steps in flows.items():
            first_step = steps[0] if steps else ""
            lines.append(f"  - {name}: {first_step}... (共{len(steps)}步)")
        return "\n".join(lines)

    def build_context_for_task(self, bundle_id: str, task: str, page_source: str = "") -> str:
        """
        根据当前 App 和任务，构建要注入到 prompt 中的知识库上下文。
        会匹配页面名称、流程名称，返回相关知识。
        """
        app = self.apps.get(bundle_id)
        if not app:
            return ""

        context_parts = []

        # 1. App 基本信息
        app_name = app["data"].get("name", bundle_id)
        app_desc = app["data"].get("description", "")
        if app_desc:
            context_parts.append(f"📱 App: {app_name}\n{app_desc}")

        # 2. 匹配页面 — 从 page_source 中提取页面特征
        pages = app["data"].get("pages", {})
        matched_pages = self._match_pages(task, page_source, pages)
        for page_name in matched_pages:
            elem_map = self.get_element_map(bundle_id, page_name)
            if elem_map:
                context_parts.append(elem_map)

        # 3. 匹配流程 — 从任务描述中匹配
        flows = app["data"].get("flows", {})
        matched_flows = self._match_flows(task, flows)
        for flow_name in matched_flows:
            flow_desc = self.get_flow(bundle_id, flow_name)
            if flow_desc:
                context_parts.append(flow_desc)

        # 4. 如果什么都没匹配到，给一个简要概览
        if not context_parts:
            summary = self.get_all_flows_summary(bundle_id)
            if summary:
                context_parts.append(summary)

        return "\n\n".join(context_parts) if context_parts else ""

    def _match_pages(self, task: str, page_source: str, pages: dict) -> list[str]:
        """根据任务描述和页面源码匹配相关页面"""
        matched = []
        task_lower = task.lower()
        source_lower = page_source.lower()
        for page_name, page_data in pages.items():
            keywords = page_data.get("keywords", [page_name])
            for kw in keywords:
                if kw.lower() in task_lower or kw.lower() in source_lower:
                    matched.append(page_name)
                    break
        return matched[:3]

    def _match_flows(self, task: str, flows: dict) -> list[str]:
        """根据任务描述匹配相关操作流程"""
        matched = []
        task_lower = task.lower()
        for flow_name, steps in flows.items():
            keywords = [flow_name]
            for step in steps[:2]:
                keywords.extend(step.lower().split())
            if any(kw.lower() in task_lower for kw in flow_name.split("_")):
                matched.append(flow_name)
            elif any(kw in task_lower for kw in keywords if len(kw) > 2):
                matched.append(flow_name)
        return matched[:2]
