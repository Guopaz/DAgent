# DAgent 项目结构

```
DAgent/
├── agent.py                    # Agent 核心逻辑（感知-思考-行动循环）
├── wda_client.py              # WebDriverAgent HTTP 客户端封装
├── tools.py                   # 工具定义和注册
├── main.py                    # 交互式入口程序
├── requirements.txt           # Python 依赖
├── .env                       # 环境变量配置
│
├── knowledge/                 # 知识库目录
│   ├── __init__.py
│   ├── app_knowledge.py       # 知识库管理器
│   ├── ios_settings/          # iOS 设置应用知识库
│   │   └── app.json           # 应用页面和操作流程定义
│   └── examples/              # 知识库示例
│
├── examples/                  # 使用示例目录
│   ├── README.md              # 示例说明文档
│   ├── example_basic_usage.py # 基础使用示例
│   ├── example_wda_tools.py   # WDA 工具直接调用示例
│   └── example_with_knowledge.py # 知识库增强示例
│
├── docs/                      # 文档目录（待创建）
│
├── README.md                  # 项目主文档
├── QUICKSTART.md              # 快速开始指南
└── PROJECT_STRUCTURE.md       # 本文件
```

## 核心文件说明

### agent.py
- iOSAgent 类实现
- 感知-思考-行动循环逻辑
- LLM 交互和工具调用
- 任务执行流程控制

### wda_client.py
- WDAClient 类实现
- WebDriverAgent HTTP API 封装
- 113 个底层 API 方法
- Session 管理

### tools.py
- ToolExecutor 类实现
- 102 个工具定义
- 工具注册和调度
- 参数验证和转换

### main.py
- 交互式命令行入口
- 用户输入处理
- 任务循环执行

### knowledge/app_knowledge.py
- AppKnowledge 类实现
- JSON 知识库加载
- 上下文匹配算法
- 页面和流程查询

## 快速导航

- 想了解如何使用？→ 查看 `examples/README.md`
- 想快速上手？→ 查看 `QUICKSTART.md`
- 想了解项目？→ 查看 `README.md`
- 想看代码结构？→ 查看本文件
