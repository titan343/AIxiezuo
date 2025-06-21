#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词工程模块 - 支持可选的提示词模板和设定集成
"""

import os
from typing import Optional, Dict, Any, List
from enum import Enum
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder


class PromptType(Enum):
    """提示词类型枚举"""
    NONE = "none"                    # 无提示词（普通对话）
    SIMPLE = "simple"               # 简单提示词
    NOVEL_WRITING = "novel_writing"  # 小说写作提示词
    CHAT_ASSISTANT = "chat_assistant"  # 聊天助手提示词


class PromptModule:
    """提示词工程模块 - 插件式提示词管理"""
    
    def __init__(self, prompts_path: str = "./prompts"):
        self.prompts_path = prompts_path
        self.prompt_type = PromptType.NONE
        self.current_prompt: Optional[ChatPromptTemplate] = None
        self.prompt_components = {}
        self.use_setting = False
        os.makedirs(self.prompts_path, exist_ok=True)
        self._load_prompt_components()
    
    def _load_prompt_components(self):
        """加载提示词组件"""
        try:
            # 加载写作规则
            writing_rules_file = os.path.join(self.prompts_path, "writing_rules.txt")
            if os.path.exists(writing_rules_file):
                with open(writing_rules_file, 'r', encoding='utf-8') as f:
                    self.prompt_components['writing_rules'] = f.read().strip()
            
            # 加载角色设定
            writer_role_file = os.path.join(self.prompts_path, "writer_role.txt")
            if os.path.exists(writer_role_file):
                with open(writer_role_file, 'r', encoding='utf-8') as f:
                    self.prompt_components['writer_role'] = f.read().strip()
            
            # 加载状态更新规则
            update_rules_file = os.path.join(self.prompts_path, "update_state_rules.txt")
            if os.path.exists(update_rules_file):
                with open(update_rules_file, 'r', encoding='utf-8') as f:
                    self.prompt_components['update_state_rules'] = f.read().strip()
            
        except Exception as e:
            print(f"加载提示词组件失败: {e}")
    
    def enable_prompt(self, prompt_type: PromptType, use_setting: bool = False, **kwargs) -> bool:
        """启用指定类型的提示词"""
        try:
            self.prompt_type = prompt_type
            self.use_setting = use_setting
            
            if prompt_type == PromptType.NONE:
                self.current_prompt = None
                print("已禁用提示词，使用普通对话模式")
                return True
            
            elif prompt_type == PromptType.SIMPLE:
                self.current_prompt = self._create_simple_prompt(**kwargs)
                print("已启用简单提示词")
            
            elif prompt_type == PromptType.NOVEL_WRITING:
                self.current_prompt = self._create_novel_writing_prompt()
                print("已启用小说写作提示词")
            
            elif prompt_type == PromptType.CHAT_ASSISTANT:
                self.current_prompt = self._create_chat_assistant_prompt()
                print("已启用聊天助手提示词")
            
            if use_setting:
                print("已启用设定集成")
            
            return True
            
        except Exception as e:
            print(f"启用提示词失败: {e}")
            return False
    
    def _create_simple_prompt(self, system_message: str = "你是一个有用的AI助手。") -> ChatPromptTemplate:
        """创建简单提示词"""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
    
    def _create_novel_writing_prompt(self) -> ChatPromptTemplate:
        """创建小说写作提示词"""
        writer_role = self.prompt_components.get('writer_role', "你是一位专业的小说作家。")
        writing_rules = self.prompt_components.get('writing_rules', "请遵循良好的写作规范。")
        
        system_template = f"""
{writer_role}

{writing_rules}

请根据以下对话历史和当前输入进行创作。
"""
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template.strip()),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
    
    def _create_chat_assistant_prompt(self) -> ChatPromptTemplate:
        """创建聊天助手提示词"""
        system_template = """
你是一个专业的AI写作助手，专门帮助用户进行小说创作。

你的能力包括：
1. 小说情节构思和发展建议
2. 人物设定和性格分析
3. 世界观建设和设定完善
4. 写作技巧指导
5. 剧情逻辑检查

请根据对话历史和用户的需求提供专业的写作建议。
"""
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template.strip()),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
    
    def disable_prompt(self):
        """禁用提示词"""
        self.prompt_type = PromptType.NONE
        self.current_prompt = None
        self.use_setting = False
        print("已禁用提示词功能")
    
    def get_prompt(self) -> Optional[ChatPromptTemplate]:
        """获取当前提示词模板"""
        return self.current_prompt
    
    def is_enabled(self) -> bool:
        """检查提示词是否已启用"""
        return self.prompt_type != PromptType.NONE and self.current_prompt is not None
    
    def format_prompt(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """格式化提示词输入"""
        if not self.is_enabled():
            # 无提示词模式，直接返回用户输入
            return {"input": input_text}
        
        prompt_vars = {"input": input_text}
        
        # 如果启用了设定集成，添加设定信息
        if self.use_setting:
            context = self._build_context()
            prompt_vars["context"] = context
        else:
            prompt_vars["context"] = ""
        
        # 添加其他参数
        prompt_vars.update(kwargs)
        
        return prompt_vars
    
    def _build_context(self) -> str:
        """构建上下文信息（包含设定）"""
        context_parts = []
        
        # 从设定模块获取信息
        try:
            from modules.setting_module import setting_module
            if setting_module.is_loaded():
                setting_summary = setting_module.get_setting_summary()
                context_parts.append("=== 当前设定 ===")
                context_parts.append(setting_summary)
        except ImportError:
            pass
        
        # 从记忆模块获取信息
        try:
            from modules.memory_module import memory_module
            if memory_module.is_enabled():
                memory_vars = memory_module.get_memory_variables()
                if memory_vars and "history" in memory_vars:
                    context_parts.append("=== 对话历史 ===")
                    # 这里可以添加历史摘要逻辑
        except ImportError:
            pass
        
        return "\n\n".join(context_parts) if context_parts else "无额外上下文信息。"
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前提示词状态"""
        return {
            "enabled": self.is_enabled(),
            "prompt_type": self.prompt_type.value,
            "use_setting": self.use_setting,
            "available_components": list(self.prompt_components.keys())
        }
    
    def list_available_prompts(self) -> List[str]:
        """列出可用的提示词类型"""
        return [prompt_type.value for prompt_type in PromptType]
    
    def reload_components(self):
        """重新加载提示词组件"""
        self.prompt_components.clear()
        self._load_prompt_components()
        
        # 如果当前有启用的提示词，重新创建
        if self.is_enabled():
            current_type = self.prompt_type
            use_setting = self.use_setting
            self.enable_prompt(current_type, use_setting)
        
        print("提示词组件已重新加载")
    
    def create_custom_prompt(self, system_message: str, use_setting: bool = False) -> bool:
        """创建自定义提示词"""
        try:
            self.prompt_type = PromptType.SIMPLE
            self.use_setting = use_setting
            
            if use_setting:
                template = f"{system_message}\n\n{{context}}\n\n用户输入: {{input}}"
            else:
                template = f"{system_message}\n\n用户输入: {{input}}"
            
            self.current_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(template)
            ])
            
            print("已创建自定义提示词")
            return True
            
        except Exception as e:
            print(f"创建自定义提示词失败: {e}")
            return False


# 全局实例
prompt_module = PromptModule() 