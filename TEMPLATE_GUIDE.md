 # 小说生成系统 - 模版系统说明文档

## 1. 模版目录结构

```
templates/
├── template_index.json          # 模版索引文件
├── 001_writer_role.txt         # 001模版-角色定义
├── 001_writing_rules.txt       # 001模版-写作规则  
├── 001_update_state_rules.txt  # 001模版-状态更新规则
├── 002_writer_role.txt         # 002模版-角色定义
├── 002_writing_rules.txt       # 002模版-写作规则
└── 002_update_state_rules.txt  # 002模版-状态更新规则

prompts/                         # 原始提示词目录（向后兼容）
├── writer_role.txt             # 默认角色定义
├── writing_rules.txt           # 默认写作规则
└── update_state_rules.txt      # 默认状态更新规则
```

## 2. 文件命名规范

### 模版文件命名
- **格式**: `{ID}_{type}.txt`
- **ID**: 3位数字（001, 002, 003...）
- **类型**: 
  - `writer_role`: 角色定义文件
  - `writing_rules`: 写作规则文件
  - `update_state_rules`: 状态更新规则文件

### 索引文件结构
```json
{
  "templates": {
    "001": {
      "id": "001",
      "name": "经典爽文小说模板",
      "category": "爽文",
      "files": {
        "writer_role": "001_writer_role.txt",
        "writing_rules": "001_writing_rules.txt", 
        "update_state_rules": "001_update_state_rules.txt"
      },
      "word_count_range": {"min": 2200, "max": 3000}
    }
  }
}
```

## 3. 提示词文件功能说明

### writer_role.txt - 角色定义文件
**作用**: 定义AI的身份、专业能力、写作风格
**内容建议**:
```
身份定位: 你是一位资深网络小说作家
专业能力: 擅长XX类型，精通人物塑造
写作风格: 文笔老辣，节奏紧凑
字数要求: 每章2200-3000字
```

### writing_rules.txt - 写作规则文件  
**作用**: 定义具体执行规则、约束条件、输出格式
**内容建议**:
```
内容约束: 严格遵守设定，保持人物一致性
结构要求: 开头钩子，中间冲突，结尾悬念
输出格式: 直接输出正文，无解释文字
禁止事项: 不能降智，不能OOC，不能违背逻辑
```

### update_state_rules.txt - 状态更新规则
**作用**: 指导AI如何更新角色状态JSON
**内容建议**:
```
分析章节内容，提取状态变化
更新数值与描述，添加新条目
修改剧情总结，严格遵守JSON格式
```

## 4. 模版调用流程

### 代码调用示例
```python
# 1. 读取模版索引
with open('templates/template_index.json') as f:
    template_index = json.load(f)

# 2. 获取指定模版信息
template_info = template_index['templates']['001']

# 3. 读取提示词文件
writer_role = read_file(f"templates/{template_info['files']['writer_role']}")
writing_rules = read_file(f"templates/{template_info['files']['writing_rules']}")

# 4. 拼接系统提示词
system_prompt = f"{writer_role}\n\n{writing_rules}"

# 5. 调用生成方法
generator.generate_chapter(
    chapter_plan=chapter_plan,
    system_prompt=system_prompt,
    model_name="deepseek_chat"
)
```

### 最终提交给LLM的内容结构
```
System Message:
[writer_role内容] + [writing_rules内容]

User Message:  
章节计划: {chapter_plan}
当前状态: {character_state_json}
世界设定: {world_bible_json}
```

## 5. 提示词工程最佳实践

### 分离原则
- **writer_role**: 稳定的身份定义，很少修改
- **writing_rules**: 灵活的行为规则，可频繁调优

### 模块化设计
- 同一角色 + 不同规则 = 不同风格
- 不同角色 + 同一规则 = 保持规范

### 版本管理
- 为不同类型小说创建专门模版
- 通过ID区分，便于A/B测试和效果对比

## 6. 使用建议

### 初期设置
1. 复制`prompts/`目录内容到`templates/001_*.txt`
2. 根据需要调整和优化提示词内容
3. 更新`template_index.json`索引信息

### 扩展新模版
1. 创建新ID的三个文件（如002_*.txt）
2. 在索引文件中添加新模版信息
3. 测试和验证模版效果

### 维护优化
1. 保持角色定义稳定，主要调整规则文件
2. 收集生成效果反馈，持续优化提示词
3. 为特殊场景创建专门的规则变体

---

**注意**: 该模版系统与`main.py`中的纯参数化设计保持分离，调用层负责读取模版文件并组合提示词内容。