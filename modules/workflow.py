#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心工作流模块 - 整合所有模块提供统一的接口
"""

from typing import Optional, Dict, Any, List
from langchain.chains import ConversationChain
from langchain_core.language_models.chat_models import BaseChatModel

from .llm_module import llm_module, LLMConfig
from .memory_module import memory_module, MemoryType
from .setting_module import setting_module, ChapterState
from .prompt_module import prompt_module, PromptType


class NovelWorkflow:
    """小说创作工作流 - 模块化架构的核心控制器"""
    
    def __init__(self):
        self.conversation_chain: Optional[ConversationChain] = None
        self._is_initialized = False
    
    def initialize(self, 
                  model_key: str,
                  memory_type: MemoryType = MemoryType.NONE,
                  session_id: Optional[str] = None,
                  prompt_type: PromptType = PromptType.NONE,
                  use_setting: bool = False,
                  chapter_index: Optional[int] = None) -> bool:
        """初始化工作流"""
        
        print("=== 初始化AI小说工作流 ===")
        
        # 1. 初始化大模型
        if not llm_module.switch_model(model_key):
            print("❌ 大模型初始化失败")
            return False
        print(f"✓ 大模型: {llm_module.get_current_config().name}")
        
        # 2. 初始化记忆模块（可选）
        if memory_type != MemoryType.NONE:
            if not session_id:
                session_id = "default_session"
            if not memory_module.enable_memory(memory_type, session_id):
                print("❌ 记忆模块初始化失败")
                return False
            print(f"✓ 记忆: {memory_type.value} (会话: {session_id})")
        else:
            memory_module.disable_memory()
            print("✓ 记忆: 已禁用")
        
        # 3. 初始化设定模块（可选）
        if use_setting and chapter_index is not None:
            if not setting_module.load_chapter_setting(chapter_index):
                print("❌ 设定模块初始化失败")
                return False
            print(f"✓ 设定: 第{chapter_index}章")
        else:
            print("✓ 设定: 未启用")
        
        # 4. 初始化提示词模块（可选）
        if not prompt_module.enable_prompt(prompt_type, use_setting):
            print("❌ 提示词模块初始化失败")
            return False
        print(f"✓ 提示词: {prompt_type.value}")
        
        # 5. 创建对话链
        self._create_conversation_chain()
        
        self._is_initialized = True
        print("=== 工作流初始化完成 ===")
        return True
    
    def _create_conversation_chain(self):
        """创建对话链"""
        llm = llm_module.get_current_model()
        
        if prompt_module.is_enabled():
            # 使用提示词模式
            prompt_template = prompt_module.get_prompt()
            if memory_module.is_enabled():
                # 带记忆的提示词链
                self.conversation_chain = ConversationChain(
                    llm=llm,
                    prompt=prompt_template,
                    memory=memory_module.get_memory(),
                    verbose=False
                )
            else:
                # 无记忆的提示词链
                from langchain.chains import LLMChain
                self.conversation_chain = LLMChain(
                    llm=llm,
                    prompt=prompt_template,
                    verbose=False
                )
        else:
            # 普通对话模式
            if memory_module.is_enabled():
                # 带记忆的普通对话
                self.conversation_chain = ConversationChain(
                    llm=llm,
                    memory=memory_module.get_memory(),
                    verbose=False
                )
            else:
                # 无记忆的普通对话
                self.conversation_chain = ConversationChain(
                    llm=llm,
                    verbose=False
                )
    
    def process_conversation(self, user_input: str, session_id: str = None) -> str:
        """处理对话（Web服务器使用）"""
        if session_id and memory_module.is_enabled():
            # 如果指定了session_id且记忆已启用，切换到对应会话
            current_session = memory_module.current_session_id
            if current_session != session_id:
                # 需要切换会话
                memory_type = memory_module.current_memory_type
                memory_module.enable_memory(memory_type, session_id)
                # 重新创建对话链
                self._create_conversation_chain()
        
        return self.chat(user_input)
    
    def chat(self, user_input: str) -> str:
        """进行对话"""
        if not self._is_initialized:
            return "错误：工作流未初始化，请先调用 initialize() 方法"
        
        try:
            if memory_module.is_enabled():
                # 带记忆的对话
                response = self.conversation_chain.predict(input=user_input)
            else:
                # 无记忆的对话
                if prompt_module.is_enabled():
                    # 有提示词但无记忆
                    response = self.conversation_chain.run(input=user_input)
                else:
                    # 无提示词无记忆，直接调用LLM
                    response = llm_module.get_current_model().invoke(user_input).content
            
            return response
            
        except Exception as e:
            return f"对话出错: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "initialized": self._is_initialized,
            "llm": {
                "ready": llm_module.is_ready(),
                "config": llm_module.get_current_config().__dict__ if llm_module.get_current_config() else None
            },
            "memory": memory_module.get_current_status(),
            "setting": {
                "loaded": setting_module.is_loaded(),
                "chapter_index": setting_module.current_chapter_index
            },
            "prompt": prompt_module.get_current_status()
        }
    
    def list_available_models(self) -> Dict[str, LLMConfig]:
        """列出可用的模型"""
        return llm_module.list_available_models()
    
    def switch_model(self, model_key: str) -> bool:
        """切换模型"""
        success = llm_module.switch_model(model_key)
        if success and self._is_initialized:
            # 重新创建对话链
            self._create_conversation_chain()
        return success
    
    def switch_memory(self, memory_type: MemoryType, session_id: str = None) -> bool:
        """切换记忆模式"""
        if memory_type == MemoryType.NONE:
            memory_module.disable_memory()
        else:
            if not session_id:
                session_id = memory_module.current_session_id or "default_session"
            if not memory_module.enable_memory(memory_type, session_id):
                return False
        
        if self._is_initialized:
            self._create_conversation_chain()
        return True
    
    def switch_prompt(self, prompt_type: PromptType, use_setting: bool = False) -> bool:
        """切换提示词模式"""
        success = prompt_module.enable_prompt(prompt_type, use_setting)
        if success and self._is_initialized:
            self._create_conversation_chain()
        return success
    
    def load_chapter(self, chapter_index: int) -> bool:
        """加载章节设定"""
        success = setting_module.load_chapter_setting(chapter_index)
        if success and prompt_module.use_setting and self._is_initialized:
            # 如果提示词启用了设定集成，重新创建对话链
            self._create_conversation_chain()
        return success
    
    def list_sessions(self) -> List[str]:
        """列出可用的会话"""
        return memory_module.list_sessions()
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话记忆"""
        return memory_module.clear_session(session_id)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        return memory_module.get_session_info(session_id)
    
    def list_chapters(self) -> List[int]:
        """列出可用的章节"""
        return setting_module.list_available_chapters()
    
    def get_setting_summary(self) -> str:
        """获取设定摘要"""
        return setting_module.get_setting_summary()
    
    def save_chapter_state(self, chapter_state: ChapterState) -> bool:
        """保存章节状态"""
        return setting_module.save_chapter_state(chapter_state)
    
    def create_new_chapter(self, chapter_index: int, base_on_previous: bool = True) -> Optional[ChapterState]:
        """创建新章节状态"""
        return setting_module.create_new_chapter_state(chapter_index, base_on_previous)


# 全局工作流实例
workflow = NovelWorkflow() 