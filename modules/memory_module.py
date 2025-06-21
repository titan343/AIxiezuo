#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆力模块 - 支持可选的多种记忆策略
"""

import os
import json
import glob
from typing import Optional, List, Dict, Any
from enum import Enum
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory


class MemoryType(Enum):
    """记忆类型枚举"""
    NONE = "none"                    # 无记忆
    BUFFER = "buffer"               # 缓冲记忆
    SUMMARY_BUFFER = "summary_buffer"  # 摘要缓冲记忆


class MemoryModule:
    """记忆力模块 - 插件式记忆管理"""
    
    def __init__(self, memory_path: str = "./memory"):
        self.memory_path = memory_path
        self.memory_type = MemoryType.NONE
        self.current_memory: Optional[ConversationBufferMemory] = None
        self.current_session_id: Optional[str] = None
        self.config = {
            "max_token_limit": 2000,
            "return_messages": True
        }
        os.makedirs(self.memory_path, exist_ok=True)
    
    def enable_memory(self, memory_type: MemoryType, session_id: str, **kwargs) -> bool:
        """启用指定类型的记忆"""
        try:
            self.memory_type = memory_type
            self.current_session_id = session_id
            
            # 更新配置
            self.config.update(kwargs)
            
            if memory_type == MemoryType.NONE:
                self.current_memory = None
                print("已禁用记忆功能")
                return True
            
            # 创建历史记录文件路径
            history_file_path = os.path.join(self.memory_path, f"{session_id}_history.json")
            chat_history = FileChatMessageHistory(file_path=history_file_path)
            
            if memory_type == MemoryType.BUFFER:
                self.current_memory = ConversationBufferMemory(
                    memory_key="history",
                    chat_memory=chat_history,
                    return_messages=self.config["return_messages"]
                )
                print(f"已启用缓冲记忆，会话: {session_id}")
            
            elif memory_type == MemoryType.SUMMARY_BUFFER:
                # 需要LLM来生成摘要
                from modules.llm_module import llm_module
                if not llm_module.is_ready():
                    print("摘要记忆需要先加载LLM模型")
                    return False
                
                self.current_memory = ConversationSummaryBufferMemory(
                    llm=llm_module.get_current_model(),
                    memory_key="history",
                    chat_memory=chat_history,
                    max_token_limit=self.config["max_token_limit"],
                    return_messages=self.config["return_messages"]
                )
                print(f"已启用摘要缓冲记忆，会话: {session_id}，token限制: {self.config['max_token_limit']}")
            
            return True
            
        except Exception as e:
            print(f"启用记忆失败: {e}")
            return False
    
    def disable_memory(self):
        """禁用记忆功能"""
        self.memory_type = MemoryType.NONE
        self.current_memory = None
        self.current_session_id = None
        print("已禁用记忆功能")
    
    def get_memory(self) -> Optional[ConversationBufferMemory]:
        """获取当前记忆对象"""
        return self.current_memory
    
    def is_enabled(self) -> bool:
        """检查记忆是否已启用"""
        return self.memory_type != MemoryType.NONE and self.current_memory is not None
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """获取记忆变量（用于传递给链）"""
        if not self.is_enabled():
            return {}
        return self.current_memory.load_memory_variables({})
    
    def list_sessions(self) -> List[str]:
        """列出所有可用的会话"""
        history_files = glob.glob(os.path.join(self.memory_path, "*_history.json"))
        sessions = []
        for file_path in history_files:
            filename = os.path.basename(file_path)
            session_id = filename.replace("_history.json", "")
            sessions.append(session_id)
        return sessions
    
    def clear_session(self, session_id: str) -> bool:
        """清除指定会话的记忆"""
        history_file_path = os.path.join(self.memory_path, f"{session_id}_history.json")
        try:
            if os.path.exists(history_file_path):
                os.remove(history_file_path)
                print(f"已清除会话记忆: {session_id}")
                return True
            else:
                print(f"会话不存在: {session_id}")
                return False
        except Exception as e:
            print(f"清除会话失败: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        history_file_path = os.path.join(self.memory_path, f"{session_id}_history.json")
        if not os.path.exists(history_file_path):
            return {"session_id": session_id, "exists": False}
        
        try:
            with open(history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                message_count = len(data.get("messages", []))
            
            file_stats = os.stat(history_file_path)
            
            return {
                "session_id": session_id,
                "exists": True,
                "message_count": message_count,
                "last_modified": file_stats.st_mtime,
                "file_size": file_stats.st_size,
                "memory_type": self.memory_type.value if session_id == self.current_session_id else "unknown"
            }
        except Exception as e:
            return {"session_id": session_id, "exists": True, "error": str(e)}
    
    def search_memory(self, session_id: str, query: str) -> List[Dict[str, Any]]:
        """在指定会话的记忆中搜索内容"""
        history_file_path = os.path.join(self.memory_path, f"{session_id}_history.json")
        if not os.path.exists(history_file_path):
            return []
        
        try:
            with open(history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                messages = data.get("messages", [])
            
            results = []
            for i, message in enumerate(messages):
                content = message.get("data", {}).get("content", "")
                if query.lower() in content.lower():
                    results.append({
                        "index": i,
                        "type": message.get("type", "unknown"),
                        "content": content[:200] + "..." if len(content) > 200 else content,
                        "full_content": content
                    })
            
            return results
        except Exception as e:
            print(f"搜索记忆时出错: {e}")
            return []
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前记忆状态"""
        return {
            "enabled": self.is_enabled(),
            "memory_type": self.memory_type.value,
            "session_id": self.current_session_id,
            "config": self.config.copy()
        }


# 全局实例
memory_module = MemoryModule() 