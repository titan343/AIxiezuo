# 小说生成系统 - 高度模块化架构

## 项目概述
基于LangChain的智能小说生成系统，采用高度模块化和插件式架构设计。系统通过全局配置管理器和统一调用接口实现完全的参数化控制，无硬编码提示词或占位符。

## 核心架构特性
- 🔧 **全局配置管理** - 统一的大模型配置获取
- 🚀 **全局LLM调用器** - 插件式大模型调用接口
- ⚙️ **接口参数化** - 所有功能通过参数控制
- 🧩 **高度模块化** - 组件间完全解耦
- 💾 **智能状态管理** - 自动状态追踪和更新
- 🧠 **增强记忆管理** - 分片存储、索引、压缩的记忆系统
- 🚫 **零硬编码** - 文档中所有代码示例的字符串都是参数示例，非硬编码

## 架构设计

### 1. 全局大模型配置获取器 (LLMConfigManager)
```python
config = LLMConfigManager.get_config("openai_gpt4")
# 返回: {"provider": "openai", "model": "gpt-4", "api_key": "...", ...}
```

### 2. 全局大模型调用器 (LLMCaller)
```python
response = LLMCaller.call(
    messages=[{"role": "user", "content": "写一段小说"}],
    model_name="openai_gpt4",
    memory=memory_obj,  # 可选
    temperature=0.8     # 可选
)
```

### 3. 业务组件
- **NovelGenerator** - 小说生成 (集成智能记忆管理)
- **StateManager** - 状态管理
- **MemoryManager** - 智能记忆管理 (分片存储+索引+压缩)

## 支持的大模型

### 配置列表
- `deepseek_chat` - DeepSeek-V3-0324 (默认模型)
- `deepseek_reasoner` - DeepSeek-R1-0528  
- `dsf5` - Gemini-2.5-Pro-Preview (稳定版)
- `openai_gpt4` - OpenAI GPT-4
- `openai_gpt35` - OpenAI GPT-3.5-turbo
- `anthropic_claude` - Anthropic Claude-3-Sonnet
- `google_gemini` - Google Gemini Pro

### 🚨 模型详细配置 (严禁修改此部分 - 用户固定配置) 🚨
```python
# DeepSeek模型配置
"deepseek_chat": {
    "provider": "openai",
    "model": "deepseek-chat",
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "base_url": "https://api.deepseek.com/v1",
    "temperature": 0.7
}

"deepseek_reasoner": {
    "provider": "openai", 
    "model": "deepseek-reasoner",
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "base_url": "https://api.deepseek.com/v1",
    "temperature": 0.7
}

# DSF5模型配置
"dsf5": {
    "provider": "openai",
    "model": "[稳定]gemini-2.5-pro-preview-06-05-c",
    "api_key": os.getenv("DSF5_API_KEY"),
    "base_url": "https://api.sikong.shop/v1", 
    "temperature": 0.7
}
```

### 环境变量
```env
DEEPSEEK_API_KEY=your_deepseek_key
DSF5_API_KEY=your_dsf5_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

## 使用方法

### 1. 基本小说生成
```python
from main import NovelGenerator

# 初始化生成器 (默认分片大小100)
generator = NovelGenerator(chunk_size=100)

# 读取模版提示词
writer_role = read_template("001_writer_role.txt")
writing_rules = read_template("001_writing_rules.txt")
system_prompt = writer_role + "\n\n" + writing_rules

# 定义章节计划 (包含章节纲要和剧情设定)
chapter_plan = {
    "chapter_index": 1,
    "title": "开始",
    "main_plot": "主角开始修炼之路",
    "chapter_outline": [
        "发现修炼天赋",
        "获得第一本功法", 
        "遇到神秘危险"
    ],
    "target_word_count": 2500,
    "mood": "紧张刺激"
}

# 生成章节 (带记忆管理)
content = generator.generate_chapter(
    chapter_plan=chapter_plan,
    model_name="deepseek_chat",
    system_prompt=system_prompt,      # 传入拼接好的模版提示词
    use_memory=True,                  # 启用历史记录
    recent_count=20,                  # 加载最近20条消息
    use_compression=False,            # False=读取原始消息，True=读取压缩摘要
    use_state=True,
    use_world_bible=True,
    use_previous_chapters=True,       # 启用前面章节内容读取
    previous_chapters_count=2         # 读取前面2章的内容
)
```

### 2. 智能交互调用（命令行使用）
```python
# 基本交互调用（用于命令行脚本）
response = generator.chat(
    user_input="请继续写下一段",
    model_name="deepseek_chat",
    system_prompt="你是写作助手",
    session_id="novel_project_1",
    use_memory=True,              # 启用记忆
    recent_count=20,              # 加载最近20条消息
    use_compression=False,        # 是否压缩历史记录
    compression_model="deepseek_chat",  # 压缩使用的模型
    save_conversation=True        # 是否保存交互记录
)

# 带压缩的长期交互
response = generator.chat(
    user_input="回顾一下前面的剧情发展",
    session_id="long_project",
    recent_count=50,              # 加载更多历史
    use_compression=True,         # 启用压缩以节省token
    compression_model="deepseek_chat"
)
```

### 3. 状态更新
```python
# 读取状态更新模版
update_rules = read_template("001_update_state_rules.txt")

# 更新章节状态
new_state = generator.update_state(
    chapter_content="生成的章节内容",
    current_state=current_state,
    model_name="openai_gpt35",
    system_prompt=update_rules  # 传入模版提示词
)
```

### 4. 记忆管理功能

#### 按范围加载记忆
```python
# 加载指定范围的消息
messages = generator.load_memory_by_range(
    session_id="novel_project_1",
    start_msg=1,                  # 起始消息编号
    end_msg=50,                   # 结束消息编号
    use_compression=True,         # 是否压缩
    compression_model="deepseek_chat"
)
```

#### 压缩记忆分片
```python
# 压缩单个分片
success = generator.compress_memory_chunk(
    session_id="novel_project_1",
    chunk_index=1,                # 分片索引
    model_name="deepseek_chat",   # 压缩模型
    compression_prompt="自定义压缩提示词"  # 可选
)

# 批量压缩分片
results = generator.batch_compress_memory(
    session_id="novel_project_1",
    chunk_indices=[1, 2, 3],      # 要压缩的分片列表
    model_name="deepseek_chat"
)
```

#### 获取记忆统计
```python
stats = generator.get_memory_stats("novel_project_1")
# 返回: {"total_messages": 150, "total_chunks": 2, "compressed_chunks": 1, ...}
```

### 5. 直接调用LLM
```python
from main import LLMCaller

# 简单调用
response = LLMCaller.call(
    messages=[
        {"role": "system", "content": "你是小说家"},
        {"role": "user", "content": "写一段对话"}
    ],
    model_name="google_gemini"
)

# 带记忆调用
response = LLMCaller.call(
    messages=[{"role": "user", "content": "继续故事"}],
    model_name="openai_gpt4",
    memory=memory_object
)
```

## 参数说明

**重要说明**：以下所有参数示例中的字符串（如"你是小说家"、"请继续写作"等）都是**参数示例**，不是硬编码。实际使用时请传入你需要的具体内容。

### NovelGenerator() 初始化参数
- `chunk_size` (int) - 分片大小（消息数量），默认100

### generate_chapter() 参数详解
- `chapter_plan` (dict) - 章节计划，必需。包含章节纲要、剧情设定等结构化数据
- `model_name` (str) - 模型名称，默认"deepseek_chat"
- `system_prompt` (str) - **系统提示词，默认空。这是传入模版提示词的入口**
  - 调用前需读取模版文件：`writer_role.txt + writing_rules.txt`
  - 示例：`system_prompt = read_template("001_writer_role.txt") + "\n\n" + read_template("001_writing_rules.txt")`
- `use_memory` (bool) - 是否加载历史记录，默认False
- `session_id` (str) - 会话ID，默认"default"
- `use_state` (bool) - 是否加载角色状态JSON，默认True
- `use_world_bible` (bool) - 是否加载世界设定JSON，默认True
- `recent_count` (int) - 加载最近N条消息，默认20
- `use_compression` (bool) - **历史记录压缩控制，默认False**
  - `False`: 从 `chunks/{session_id}_chunk_xxx.json` 读取原始消息
  - `True`: 从 `summaries/{session_id}_summary_xxx.json` 读取压缩摘要
- `compression_model` (str) - 压缩时使用的模型，默认"deepseek_chat"
- `use_previous_chapters` (bool) - **是否读取前面章节内容，默认False**
  - 从xiaoshuo目录读取前面已保存的章节文件内容
  - 确保生成内容与最新的章节文件保持一致，解决记忆与文件不同步问题
- `previous_chapters_count` (int) - 读取前面章节的数量，默认1（范围1-10）

### update_state() 参数详解
- `chapter_content` (str) - 章节内容，必需。用于分析状态变化的小说文本
- `current_state` (ChapterState) - 当前状态对象，必需
- `model_name` (str) - 模型名称，默认"deepseek_chat"
- `system_prompt` (str) - **状态更新提示词，默认已内置完整规则**
  - 调用前可读取模版文件：`update_state_rules.txt`
  - 示例：`system_prompt = read_template("001_update_state_rules.txt")`
  - 如果不传入，使用内置的状态更新规则

### chat() 参数详解
- `user_input` (str) - 用户输入，必需
- `model_name` (str) - 模型名称，默认"deepseek_chat"
- `system_prompt` (str) - 系统提示词，默认空
- `session_id` (str) - 会话ID，默认"default"
- `use_memory` (bool) - 是否加载历史记录，默认True
- `recent_count` (int) - 加载最近N条消息，默认20
- `use_compression` (bool) - **历史记录压缩控制，默认False**
  - `False`: 从原始消息文件读取
  - `True`: 从压缩摘要文件读取
- `compression_model` (str) - 压缩时使用的模型，默认"deepseek_chat"
- `save_conversation` (bool) - 是否保存交互记录到记忆，默认True

### LLMCaller.call() 参数
- `messages` (List[Dict]) - 消息列表，必需
- `model_name` (str) - 模型名称，默认"deepseek_chat"
- `memory` (Optional) - 记忆对象，默认None
- `temperature` (Optional[float]) - 温度参数，默认None

### 记忆管理专用参数
- `load_memory_by_range()` - 按范围加载：`start_msg`, `end_msg`, `use_compression`, `compression_model`
- `compress_memory_chunk()` - 压缩分片：`chunk_index`, `model_name`, `compression_prompt`
- `batch_compress_memory()` - 批量压缩：`chunk_indices`, `model_name`
- `get_memory_stats()` - 获取统计：仅需`session_id`

## 文件结构
```
langchain/
├── main.py                # 主程序（集成智能记忆管理）
├── main_backup.py         # 原版本备份
├── enhanced_memory_example.py  # 记忆管理功能示例
├── data/                  # 数据存储
│   ├── chapter_XXX_state.json  # 章节状态
│   └── world_bible_XX.json     # 世界设定
├── memory/               # 智能记忆管理
│   ├── chunks/           # 分片存储
│   │   ├── session_chunk_001.json
│   │   └── session_chunk_002.json
│   ├── summaries/        # 压缩摘要
│   │   └── session_summary_001.json
│   └── session_index.json  # 会话索引
├── xiaoshuo/             # 生成的小说
├── versions/             # 版本管理
├── modules/              # 旧模块（可选择保留）
└── prompts/              # 提示词文件（可选）
```

## 扩展开发

### 添加新的大模型
在 `LLMConfigManager.get_config()` 中添加配置：
```python
"new_model": {
    "provider": "custom",
    "model": "model-name",
    "api_key": os.getenv("CUSTOM_API_KEY"),
    "base_url": "https://api.custom.com",
    "temperature": 0.7
}
```

在 `LLMCaller.call()` 中添加对应的provider处理逻辑。

### 自定义业务逻辑
继承或组合 `NovelGenerator` 类：
```python
class CustomGenerator(NovelGenerator):
    def custom_generate(self, custom_params):
        # 自定义生成逻辑
        return self.generate_chapter(
            chapter_plan=custom_params,
            model_name="custom_model",
            system_prompt="自定义提示词"
        )
```

## 优势特点

1. **零硬编码** - 所有提示词和参数通过接口传入
2. **插件架构** - 大模型配置和调用完全解耦
3. **参数化控制** - 每个功能都可通过参数精确控制
4. **高度复用** - 全局LLM调用器可被所有业务组件使用
5. **易于扩展** - 添加新模型或功能只需修改配置
6. **智能记忆管理** - 分片存储+压缩，支持大规模对话历史
7. **统一接口** - 单一记忆管理接口，功能强大而简洁
8. **简洁明了** - 核心代码保持清晰，功能模块化

## 历史记录读取机制详解

### 压缩控制参数的具体行为
当使用 `generate_chapter()` 或 `chat()` 方法时：

**use_compression=False (默认)**：
- 读取路径：`memory/chunks/{session_id}_chunk_xxx.json`
- 内容：原始完整的对话消息
- 适用场景：短期对话，需要完整上下文

**use_compression=True**：
- 读取路径：`memory/summaries/{session_id}_summary_xxx.json`
- 内容：LLM压缩后的摘要文本
- 适用场景：长期项目，节省token消耗

### 文件路径对应关系
```
memory/
├── chunks/                           # 原始消息存储
│   ├── novel_project_1_chunk_001.json    # 第1-100条消息
│   └── novel_project_1_chunk_002.json    # 第101-200条消息
├── summaries/                        # 压缩摘要存储  
│   └── novel_project_1_summary_001.json  # 第1片的压缩摘要
└── novel_project_1_index.json       # 索引文件
```

### 调用示例对比
```python
# 读取原始消息 (完整上下文)
response = generator.chat(
    user_input="继续写作",
    use_compression=False,  # 从chunks/目录读取
    recent_count=20
)

# 读取压缩摘要 (节省token)
response = generator.chat(
    user_input="继续写作", 
    use_compression=True,   # 从summaries/目录读取
    recent_count=20
)
```

## 智能记忆管理系统

### 核心组件
- **MemoryChunkManager** - 分片存储管理器，处理消息分片和索引
- **MemoryCompressor** - 独立压缩模块，使用LLM压缩历史记录
- **MemoryIndexManager** - 索引管理器，维护分片信息和元数据
- **MemoryManager** - 智能记忆管理器，整合上述功能

### 工作原理
1. **分片存储** - 按设定大小将消息分片存储（默认100条/片）
2. **索引管理** - 维护分片索引，支持快速定位和范围查询
3. **智能压缩** - 可选择性压缩历史分片，节省存储空间
4. **灵活加载** - 支持按范围、最近N条等多种加载方式

### 文件结构
```
memory/
├── chunks/                    # 分片存储目录
│   ├── {session_id}_chunk_001.json
│   └── {session_id}_chunk_002.json
├── summaries/                 # 压缩摘要目录
│   └── {session_id}_summary_001.json
└── {session_id}_index.json   # 会话索引文件
```

### 使用场景
- **短期对话** - 默认模式，自动管理记忆
- **长期项目** - 启用压缩，支持数千条消息
- **批量处理** - 支持批量压缩和范围查询
- **灵活配置** - 可调节分片大小和压缩策略

## 迁移指南

从旧版本迁移：
1. 备份现有数据文件（data/, memory/等）
2. 使用新的 `NovelGenerator` 替代 `NovelGenerationTask`
3. 将硬编码的提示词改为参数传入
4. 使用 `LLMCaller.call()` 替代直接的LLM调用
5. 所有记忆功能已自动升级为智能管理

新架构保持了数据格式兼容性，现有的状态文件和记忆文件可直接使用。

## ⚠️ 重要警告

### 模型配置保护
以下三个模型配置为用户固定设置，**严禁在任何代码修改中变更**：

1. **deepseek_chat** (默认模型)
   - API Key: `DEEPSEEK_API_KEY`
   - Base URL: `https://api.deepseek.com/v1`
   - Model: `deepseek-chat`

2. **deepseek_reasoner**
   - API Key: `DEEPSEEK_API_KEY` 
   - Base URL: `https://api.deepseek.com/v1`
   - Model: `deepseek-reasoner`

3. **dsf5**
   - API Key: `DSF5_API_KEY`
   - Base URL: `https://api.sikong.shop/v1`
   - Model: `[稳定]gemini-2.5-pro-preview-06-05-c`

这些配置已在代码中标记保护，任何修改都会导致用户设置丢失。