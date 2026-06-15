# DAgent 使用示例

本目录包含 DAgent 的各种使用示例。

## 示例文件说明

### 1. example_basic_usage.py
基础使用示例，展示如何使用 iOSAgent 执行自动化任务。

**运行方式：**
```bash
cd DAgent/examples
python example_basic_usage.py
```

**内容：**
- 初始化知识库
- 创建和连接 Agent
- 执行多个自动化任务（查看屏幕、打开应用、查找元素）

---

### 2. example_wda_tools.py
直接调用 WDA 工具的示例，展示如何绕过 Agent 直接使用底层 API。

**运行方式：**
```bash
cd DAgent/examples
python example_wda_tools.py
```

**内容：**
- 获取设备状态和信息
- 创建和管理会话
- 截图和元素树
- 元素查找和操作
- 手势操作（滑动、点击）
- 剪贴板操作

---

### 3. example_with_knowledge.py
知识库增强示例，展示如何利用预定义的知识库提升 Agent 的上下文理解能力。

**运行方式：**
```bash
cd DAgent/examples
python example_with_knowledge.py
```

**内容：**
- 加载 iOS 设置应用知识库
- 显示知识库结构（页面、操作流程）
- 执行需要知识库支持的任务（关闭 WiFi、查看设备信息）

---

## 前置条件

所有示例都需要：
1. iPhone 已连接并信任电脑
2. WebDriverAgent 已在 iPhone 上运行
3. 已执行端口转发：`iproxy 8100 8100`

## 运行顺序建议

1. 先运行 `example_wda_tools.py` 了解底层 API
2. 再运行 `example_basic_usage.py` 了解 Agent 的基本使用
3. 最后运行 `example_with_knowledge.py` 了解知识库的高级用法

## 自定义示例

你可以基于这些示例创建自己的测试脚本：

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import iOSAgent
from knowledge import AppKnowledge

# 你的自定义代码...
```

