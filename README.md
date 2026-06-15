# DAgent - iOS 自动化测试 Agent

一个基于大语言模型和 WebDriverAgent 的 iOS 自动化测试框架，通过自然语言指令控制 iPhone 设备执行测试任务。

## 🌟 特性

- **自然语言控制**: 使用自然语言描述任务，Agent 自动执行
- **智能感知**: 实时获取屏幕状态，理解当前 UI 上下文
- **知识库增强**: 预定义应用结构和操作流程，提升任务执行准确性
- **丰富的工具集**: 102 个 WDA 工具，覆盖所有 iOS 交互场景
- **多步规划**: 自动拆解复杂任务为多个步骤
- **错误恢复**: 智能识别异常并尝试恢复

## 📋 前置要求

### 硬件要求
- iPhone 设备（已越狱或使用开发者证书签名 WDA）
- USB 数据线连接 iPhone 到电脑
- Mac 或 Linux 电脑

### 软件要求
- Python 3.8+
- WebDriverAgent 已安装并在 iPhone 上运行
- `iproxy` 工具（用于端口转发）

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/liuzedong/Workspace/DAgent
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# OpenAI API 配置
LLM_API_KEY="your-api-key-here"
LLM_BASE_URL="https://api.openai.com/v1"
LLM_MODEL_ID="gpt-4"

# WDA 配置（可选，默认值为 localhost:8100）
WDA_BASE_URL="http://localhost:8100"
```

### 3. 启动 WDA 并设置端口转发

在 iPhone 上运行 WebDriverAgent，然后在电脑上执行：

```bash
iproxy 8100 8100
```

### 4. 运行示例

```bash
# 基础使用示例
python example_basic_usage.py

# 知识库增强示例
python example_with_knowledge.py

# 直接使用主程序
python main.py
```

## 📁 项目结构

```
DAgent/
├── agent.py              # 核心 Agent 逻辑（感知-思考-行动循环）
├── wda_client.py         # WDA HTTP 客户端封装（113 个 API 方法）
├── tools.py              # 工具定义和执行器（102 个工具）
├── main.py               # 主程序入口
├── knowledge/            # 知识库目录
│   ├── app_knowledge.py  # 知识库管理器
│   └── ios_settings/     # iOS 设置应用知识库
│       └── app.json      # 应用结构和操作流程定义
├── example_basic_usage.py      # 基础使用示例
├── example_with_knowledge.py   # 知识库增强示例
├── requirements.txt            # Python 依赖
└── .env                        # 环境变量配置（需自行创建）
```

## 🎯 使用指南

### 基础使用

```python
from agent import iOSAgent

# 创建 Agent
agent = iOSAgent(
    wda_url="http://localhost:8100",
    max_steps=30
)

# 连接设备
agent.connect()

# 执行任务
result = agent.run("打开设置应用")
print(result)

# 断开连接
agent.disconnect()
```

### 使用知识库

```python
from agent import iOSAgent
from knowledge import AppKnowledge

# 加载知识库
knowledge = AppKnowledge("knowledge")

# 创建 Agent 并注入知识库
agent = iOSAgent(wda_url="http://localhost:8100")
agent.knowledge = knowledge

# 连接并执行任务
agent.connect()
result = agent.run("关闭无线局域网")  # 知识库会自动提供上下文
agent.disconnect()
```

### 交互式使用

```bash
python main.py
```

启动后可以连续输入任务：
```
🎯 任务: 打开设置应用
🎯 任务: 查看设备信息
🎯 任务: 退出
```

## 📚 知识库

### 知识库结构

知识库使用 JSON 格式定义应用结构和操作流程：

```json
{
  "name": "设置",
  "bundle_id": "com.apple.Preferences",
  "description": "iOS 系统设置应用",
  "pages": {
    "首页": {
      "keywords": ["设置", "Settings"],
      "description": "设置应用主页面",
      "elements": [
        {
          "name": "无线局域网",
          "locator": {"type": "name", "value": "无线局域网"},
          "description": "WiFi 设置入口"
        }
      ]
    }
  },
  "flows": {
    "关闭WiFi": [
      "打开设置应用",
      "点击'无线局域网'",
      "关闭 WiFi 开关"
    ]
  }
}
```

### 添加新应用知识库

1. 在 `knowledge/` 目录下创建应用目录：
   ```bash
   mkdir knowledge/my_app
   ```

2. 创建 `app.json` 文件，定义应用结构和操作流程

3. 重启 Agent，知识库会自动加载

## 🛠️ 可用工具（102 个）

### 感知类
- `get_screenshot` - 获取屏幕截图
- `get_source` - 获取 UI 元素树（XML）
- `get_element_text` - 获取元素文本
- `get_element_attribute` - 获取元素属性
- `is_element_displayed` - 检查元素可见性
- `get_element_rect` - 获取元素位置和大小

### 查找类
- `find_element` - 查找单个元素
- `find_elements` - 查找多个元素
- `get_active_element` - 获取当前活跃元素
- `get_visible_cells` - 获取可见单元格

### 交互类
- `click_element` - 点击元素
- `tap` - 点击坐标
- `send_keys` - 输入文本
- `clear_element` - 清空输入框
- `swipe` - 滑动
- `scroll` - 滚动
- `drag` - 拖拽
- `pinch` - 捏合
- `double_tap` - 双击
- `long_press` - 长按

### 应用管理类
- `launch_app` - 启动应用
- `kill_app` - 关闭应用
- `activate_app` - 激活应用
- `get_app_state` - 获取应用状态
- `list_apps` - 列出已安装应用

### 设备控制类
- `press_home` - 按 Home 键
- `press_button` - 按系统按钮
- `lock_screen` - 锁屏
- `get_orientation` - 获取屏幕方向
- `set_orientation` - 设置屏幕方向

### 系统类
- `get_alert_text` - 获取弹窗文本
- `accept_alert` - 接受弹窗
- `dismiss_alert` - 关闭弹窗
- `dismiss_keyboard` - 隐藏键盘
- `get_clipboard` - 获取剪贴板
- `set_clipboard` - 设置剪贴板

完整工具列表请参考 `tools.py` 中的 `get_tools()` 函数。

## 🔧 高级用法

### 自定义工具

```python
from tools import ToolExecutor
from wda_client import WDAClient

class CustomToolExecutor(ToolExecutor):
    def __init__(self, wda_client):
        super().__init__(wda_client)
        
    def custom_action(self, element_id: str):
        """自定义操作"""
        # 获取元素信息
        rect = self.wda_client.get_element_rect(element_id)
        # 执行自定义逻辑
        x = rect['x'] + rect['width'] / 2
        y = rect['y'] + rect['height'] / 2
        self.wda_client.tap(x, y)
```

### 自定义知识库匹配逻辑

```python
from knowledge import AppKnowledge

class EnhancedAppKnowledge(AppKnowledge):
    def get_relevant_context(self, task: str) -> str:
        """增强版上下文匹配"""
        context = super().get_relevant_context(task)
        
        # 添加自定义逻辑
        if "网络" in task:
            context += "\n提示：网络设置通常在'无线局域网'或'蜂窝网络'页面"
        
        return context
```

### 任务规划和执行

```python
from agent import iOSAgent

agent = iOSAgent()
agent.connect()

# 复杂任务会被自动拆解
complex_task = """
1. 打开设置应用
2. 进入无线局域网设置
3. 关闭 WiFi
4. 等待 5 秒
5. 重新打开 WiFi
6. 返回设置首页
"""

result = agent.run(complex_task)
print(result)

agent.disconnect()
```

## 🐛 故障排查

### 连接失败

**问题**: 无法连接到 WDA

**解决方案**:
1. 确认 iPhone 已连接并信任电脑
2. 确认 WDA 已在 iPhone 上运行
3. 执行 `iproxy 8100 8100` 进行端口转发
4. 检查 `.env` 文件中的 `WDA_BASE_URL` 配置

### 元素找不到

**问题**: Agent 无法找到指定元素

**解决方案**:
1. 使用 `get_source` 获取当前 UI 元素树
2. 检查元素定位策略（name、class、xpath 等）
3. 确保元素在当前页面可见
4. 考虑添加等待时间等待页面加载

### API 调用失败

**问题**: OpenAI API 调用失败

**解决方案**:
1. 检查 `.env` 文件中的 API Key 和 Base URL
2. 确认网络连接正常
3. 检查 API 额度是否充足

## 📝 开发指南

### 添加新的 WDA 工具

1. 在 `wda_client.py` 中添加 HTTP 方法：
   ```python
   def new_method(self, param: str) -> dict:
       return self._post("/session/{session_id}/new_endpoint", {"param": param})
   ```

2. 在 `tools.py` 中注册工具：
   ```python
   TOOLS.append({
       "name": "new_tool",
       "description": "工具描述",
       "parameters": {
           "type": "object",
           "properties": {
               "param": {"type": "string"}
           },
           "required": ["param"]
       }
   })
   ```

3. 在 `ToolExecutor` 中实现执行逻辑：
   ```python
   def execute_new_tool(self, args):
       return self.wda_client.new_method(args["param"])
   ```

### 扩展知识库

知识库支持以下字段：
- `name`: 应用名称
- `bundle_id`: 应用 Bundle ID
- `description`: 应用描述
- `pages`: 页面定义（包含元素定位信息）
- `flows`: 操作流程定义
- `tips`: 使用提示

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 GitHub Issues 反馈。
