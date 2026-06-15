# 快速开始指南

## 环境准备

### 1. 安装 WebDriverAgent

在 iPhone 上安装并运行 WebDriverAgent：

```bash
# 克隆 WDA
git clone https://github.com/appium/WebDriverAgent.git
cd WebDriverAgent

# 使用 Xcode 打开项目
open WebDriverAgent.xcodeproj

# 在 Xcode 中：
# 1. 选择你的开发者团队（Team）
# 2. 选择你的 iPhone 设备
# 3. 点击运行按钮（▶️）
```

### 2. 设置端口转发

在电脑上执行：

```bash
# 安装 iproxy（如果未安装）
brew install libimobiledevice

# 启动端口转发
iproxy 8100 8100
```

保持此终端窗口打开。

### 3. 验证连接

```bash
# 测试 WDA 连接
curl http://localhost:8100/status

# 应该返回 JSON 格式的响应
```

## 首次使用

### 最简单的使用方式

```python
from agent import iOSAgent

# 创建并连接
agent = iOSAgent()
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

# 创建 Agent
agent = iOSAgent()
agent.knowledge = knowledge
agent.connect()

# 执行任务（知识库会自动增强上下文）
result = agent.run("关闭 WiFi")
print(result)

agent.disconnect()
```

## 常用任务示例

### 系统设置相关

```python
agent.run("打开设置应用")
agent.run("查看当前 WiFi 连接状态")
agent.run("关闭无线局域网")
agent.run("打开蓝牙设置")
agent.run("查看设备信息")
agent.run("调整屏幕亮度到 50%")
```

### 应用管理相关

```python
agent.run("列出所有已安装的应用")
agent.run("打开 Safari 浏览器")
agent.run("关闭 Safari")
agent.run("检查微信是否在运行")
```

### 屏幕交互相关

```python
agent.run("截取当前屏幕")
agent.run("向上滑动屏幕")
agent.run("点击屏幕中央")
agent.run("查看当前页面上的所有按钮")
```

### 系统控制相关

```python
agent.run("按 Home 键")
agent.run("锁定屏幕")
agent.run("解锁屏幕")
agent.run("旋转屏幕到横屏模式")
```

## 交互式模式

启动交互式模式可以连续执行多个任务：

```bash
python main.py
```

然后输入任务：
```
🎯 任务: 打开设置
🎯 任务: 进入 WiFi 设置
🎯 任务: 关闭 WiFi
🎯 任务: 退出
```

## 调试技巧

### 1. 查看当前屏幕状态

```python
from wda_client import WDAClient

wda = WDAClient()
wda.create_session()

# 获取截图
screenshot = wda.get_screenshot()
print(f"截图大小: {len(screenshot)} bytes")

# 获取元素树
source = wda.get_source()
print(source[:1000])  # 打印前 1000 个字符
```

### 2. 手动查找元素

```python
from wda_client import WDAClient

wda = WDAClient()
wda.create_session()

# 按名称查找
element_id = wda.find_element("name", "无线局域网")
print(f"找到元素: {element_id}")

# 获取元素属性
if element_id:
    text = wda.get_element_text(element_id)
    print(f"元素文本: {text}")
    
    rect = wda.get_element_rect(element_id)
    print(f"元素位置: {rect}")
```

### 3. 手动执行操作

```python
from wda_client import WDAClient

wda = WDAClient()
wda.create_session()

# 点击元素
element_id = wda.find_element("name", "设置")
if element_id:
    wda.click_element(element_id)
    print("已点击")

# 点击坐标
wda.tap(x=200, y=300)
print("已点击坐标 (200, 300)")

# 滑动
wda.swipe(from_x=200, from_y=500, to_x=200, to_y=200, duration=0.5)
print("已滑动")
```

## 常见问题

### Q: Agent 找不到元素怎么办？

A: 可能的原因：
1. 元素名称不正确 - 使用 `get_source()` 查看实际的元素树
2. 页面未加载完成 - 在操作前添加等待时间
3. 元素不在当前视图中 - 先滑动页面

```python
import time
agent.run("打开设置")
time.sleep(2)  # 等待页面加载
agent.run("点击无线局域网")
```

### Q: 如何提高任务执行成功率？

A: 
1. **使用知识库**: 预定义应用结构和操作流程
2. **分解复杂任务**: 将复杂任务拆分为多个简单步骤
3. **添加等待时间**: 在关键操作后等待页面加载
4. **验证结果**: 执行操作后检查结果是否符合预期

### Q: 如何添加自定义知识库？

A: 在 `knowledge/` 目录下创建应用目录和 `app.json`：

```bash
mkdir knowledge/my_app
```

创建 `knowledge/my_app/app.json`：

```json
{
  "name": "我的应用",
  "bundle_id": "com.example.myapp",
  "pages": {
    "首页": {
      "keywords": ["首页", "Home"],
      "elements": [
        {
          "name": "登录按钮",
          "locator": {"type": "name", "value": "登录"},
          "description": "用户登录按钮"
        }
      ]
    }
  },
  "flows": {
    "用户登录": [
      "点击登录按钮",
      "输入用户名",
      "输入密码",
      "点击确认"
    ]
  }
}
```

## 性能优化

### 1. 减少截图次数

Agent 默认会在每次操作后截图。可以通过调整参数减少截图：

```python
agent = iOSAgent(
    max_steps=50,  # 增加最大步数
    screenshot_frequency=3  # 每 3 步截一次图
)
```

### 2. 使用缓存

对于重复查询的信息，可以使用缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=10)
def get_device_info():
    return wda.get_device_info()
```

### 3. 批量操作

将多个相关操作组合在一起：

```python
# 不推荐：多次单独操作
agent.run("打开设置")
agent.run("点击 WiFi")
agent.run("关闭 WiFi")

# 推荐：一次完成
agent.run("打开设置，进入 WiFi 设置，关闭 WiFi")
```

## 下一步

- 查看 `README.md` 了解完整的项目文档
- 运行示例文件学习更多用法
- 创建自己的知识库来增强特定应用的自动化能力
- 贡献代码或报告问题到 GitHub

祝你使用愉快！🎉
