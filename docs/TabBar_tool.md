# `get_tab_bar` — TabBar 定位与切换工具

> 优先级：最高 | 状态：方案设计 | 归属组：交互工具

---

## 1. 背景与动机

多 Tab App（微信、淘宝、Boss 直聘等）的操作起点几乎总是「确认当前在哪个 Tab → 切换到目标 Tab」。目前 DAgent 只能用三件套：

```
observe_screen → 人肉解析 XML，找 XCUIElementTypeTabBar → tap_by_name
```

这带来四个问题：

| 痛点 | 表现 |
|------|------|
| **定位成本高** | LLM 需要从数千行 XML 中寻找 `XCUIElementTypeTabBar`，理解嵌套结构 |
| **纯图标 Tab 无法定位** | 很多 App 的 Tab 无 label/name，`tap_by_name` 直接失效 |
| **XML 截断丢失 TabBar** | `observe_screen` 截断 25000 字符时，底部的 TabBar 大概率被切掉 |
| **不知当前选中哪个** | XML 中 `selected` 属性并非总能可靠获取，LLM 容易误判 |

**`get_tab_bar` 的目标：一个调用取代上述 3-4 轮推理，让 LLM 零解析成本完成 Tab 感知和切换。**

---

## 2. 参数设计

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:--:|--------|------|
| `action` | string | 否 | `"list"` | `"list"` — 列出所有 Tab；`"switch"` — 切换到指定 Tab |
| `index` | int | 否 | — | 当 `action="switch"` 时，按索引切换（0-based） |
| `tab_name` | string | 否 | — | 当 `action="switch"` 时，按名称模糊匹配切换（不区分大小写，优先精确匹配） |

**规则**：
- `action="switch"` 时 `index` 和 `tab_name` **二选一**（都提供时报错）
- `action="list"` 时忽略 `index` 和 `tab_name`

### 调用示例

```
// 场景 1：查看 Tab 结构
get_tab_bar(action="list")

// 场景 2：按索引切换
get_tab_bar(action="switch", index=4)

// 场景 3：按名称切换
get_tab_bar(action="switch", tab_name="我的")

// 场景 4：纯图标 Tab，不知道名字，先用 list 看一眼索引
get_tab_bar(action="list")
→ 返回 tabs: [{index:0,name:""}, {index:1,name:""}, {index:2,name:"消息"}, ...]
get_tab_bar(action="switch", index=0)
```

---

## 3. 返回值设计

### 3.1 正常情况（`action="list"`）

```json
{
  "found": true,
  "tab_count": 5,
  "selected_index": 2,
  "selected_name": "消息",
  "tabs": [
    { "index": 0, "name": "首页",   "label": "首页",
      "rect": { "x": 0, "y": 778, "width": 75, "height": 48 } },
    { "index": 1, "name": "职位",   "label": "职位",
      "rect": { "x": 75, "y": 778, "width": 75, "height": 48 } },
    { "index": 2, "name": "消息",   "label": "消息",
      "rect": { "x": 150, "y": 778, "width": 75, "height": 48 } },
    { "index": 3, "name": "通讯录", "label": "通讯录",
      "rect": { "x": 225, "y": 778, "width": 75, "height": 48 } },
    { "index": 4, "name": "我的",   "label": "我的",
      "rect": { "x": 300, "y": 778, "width": 75, "height": 48 } }
  ]
}
```

### 3.2 纯图标 Tab（无 label/name）

```json
{
  "found": true,
  "tab_count": 4,
  "selected_index": 1,
  "selected_name": "",
  "tabs": [
    { "index": 0, "name": "", "label": "",
      "rect": { "x": 0, "y": 778, "width": 93, "height": 48 }, "accessible": true },
    { "index": 1, "name": "", "label": "",
      "rect": { "x": 93, "y": 778, "width": 93, "height": 48 }, "accessible": true },
    { "index": 2, "name": "", "label": "",
      "rect": { "x": 186, "y": 778, "width": 93, "height": 48 }, "accessible": true },
    { "index": 3, "name": "", "label": "",
      "rect": { "x": 279, "y": 778, "width": 93, "height": 48 }, "accessible": true }
  ]
}
```

> 纯图标 Tab 仍返回完整索引列表，支持 `get_tab_bar(action="switch", index=3)` 按位置点击。每个 Tab 附带 `accessible` 字段标识该元素是否可通过无障碍访问。

### 3.3 页面无 TabBar

```json
{
  "found": false,
  "tab_count": 0,
  "selected_index": -1,
  "selected_name": "",
  "tabs": [],
  "reason": "当前页面未检测到 XCUIElementTypeTabBar"
}
```

> `reason` 字段帮助 LLM 理解失败原因并决策下一步（例如：这不是一个多 Tab 页面，用其他导航方式）。

---

## 4. 错误场景处理

| 场景 | 返回值 |
|------|--------|
| 页面无 TabBar | `{"found": false, "reason": "当前页面未检测到 XCUIElementTypeTabBar"}` |
| `action="switch"` 但 `index` 和 `tab_name` 都提供了 | 报错：`"请只提供 index 或 tab_name 之一"` |
| `action="switch"` 时 `index` 超出范围 | `{"found": true, "error": "索引 8 超出范围，有效索引: 0-4"}` |
| `action="switch"` 时 `tab_name` 匹配到多个 | 返回候选列表，让 LLM 二选一 |
| `action="switch"` 时 `tab_name` 未匹配到任何 Tab | `{"found": true, "error": "未找到匹配 'xxx' 的 Tab，可用: ['首页','职位','消息','通讯录','我的']"}` |
| TabBar 存在但找不到子 Button | `{"found": true, "tab_count": 0, "reason": "TabBar 存在但无子 Button，可能为自定义实现"}` |

---

## 5. 核心实现流程

```
1. wda.find_elements("class name", "XCUIElementTypeTabBar")
   → 找到 TabBar 容器 element_id

2. 若未找到 → 返回 {"found": false, ...}

3. wda.find_elements_from_element(tabbar_id, "class name", "XCUIElementTypeButton")
   → 找到 TabBar 下的所有按钮

4. 遍历每个按钮，提取：
   - label = wda.get_element_attribute(btn_id, "label") or ""
   - name  = wda.get_element_name(btn_id) or ""
   - rect  = wda.get_element_rect(btn_id)
   - selected = wda.is_element_selected(btn_id)          ← 最可靠的选中判定
   - accessible = wda.is_element_accessible(btn_id)      ← 纯图标 Tab 的兜底
   - display_name = label or name or f"（无标签，索引 {i}）"

5. 构造结构化 JSON 返回

6. 如果 action="switch"：
   - 按 index 或 tab_name（模糊匹配，优先精确）定位目标按钮
   - wda.click_element(target_btn_id)
   - wda.wait(0.5)
   - 返回切换结果
```

### 选中状态判定优先级

```
wda.is_element_selected(btn_id)          ← 最优先，WDA 原生 API
  ↓ 不可用时
wda.get_element_attribute(btn_id, "value") == "1"  ← 部分 App 的选中标记
  ↓ 不可用时
wda.get_element_attribute(btn_id, "selected") == "true"  ← 极少情况
  ↓ 全部不可用时
假定第一个为选中（极少场景的降级处理）
```

---

## 6. 与现有工具的关系

| 现有方式 | `get_tab_bar` |
|----------|---------------|
| `observe_screen → 人肉找 TabBar` | 一步到位返回结构化 JSON |
| `tap_by_name("消息")` | `get_tab_bar(action="switch", tab_name="消息")` |
| 纯图标 Tab 无法操作 | `get_tab_bar(action="switch", index=3)` |
| XML 截断丢失底部 TabBar | XPath 精准定位，不受截断影响 |

**`get_tab_bar` 不替代任何现有工具**，它是 `observe_screen` + `tap_by_name` 在 Tab 场景下的高效组合封装。

---

## 7. 不做的范围（明确拒绝）

| 需求 | 原因 |
|------|------|
| `action="highlight"` 截图标注模式 | 视觉标注是 `observe_screen(mode="screenshot")` 的扩展方向，不应混入 TabBar 工具 |
| 支持 `UIToolBar` / `UINavigationBar` | 定位逻辑和语义完全不同，应分别建独立工具 |
| 支持自定义 TabBar（非原生 `XCUIElementTypeTabBar`） | 自定义实现千差万别，无法通用化；此类 App 应在 SKILL.md 中提供页面级导航指导 |