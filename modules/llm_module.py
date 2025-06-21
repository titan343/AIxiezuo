#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型模块 - 全局统一配置，通过模型名灵活调用
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

# 全局模型配置 - 一次配置，全局使用
GLOBAL_MODEL_CONFIGS = {
    "deepseek": {
        "name": "DeepSeek Chat",
        "provider": "deepseek", 
        "model_name": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "api_base_url": "https://api.deepseek.com/v1",
        "max_tokens": 4000,
        "temperature": 0.7,
        "description": "DeepSeek对话模型，适合创意写作（默认模型）"
    },
    "gpt-4": {
        "name": "GPT-4",
        "provider": "openai",
        "model_name": "gpt-4", 
        "api_key_env": "OPENAI_API_KEY",
        "api_base_url": None,
        "max_tokens": 4000,
        "temperature": 0.7,
        "description": "OpenAI GPT-4，综合能力强"
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key_env": "OPENAI_API_KEY", 
        "api_base_url": None,
        "max_tokens": 4000,
        "temperature": 0.7,
        "description": "OpenAI GPT-3.5，速度快成本低"
    },
    "claude-3-sonnet": {
        "name": "Claude-3 Sonnet",
        "provider": "anthropic",
        "model_name": "claude-3-sonnet-20240229",
        "api_key_env": "ANTHROPIC_API_KEY",
        "api_base_url": None,
        "max_tokens": 4000,
        "temperature": 0.7,
        "description": "Anthropic Claude-3，理解能力强"
    },
    "gemini-pro": {
        "name": "Gemini Pro", 
        "provider": "google",
        "model_name": "gemini-pro",
        "api_key_env": "GOOGLE_API_KEY",
        "api_base_url": None,
        "max_tokens": 4000,
        "temperature": 0.7,
        "description": "Google Gemini Pro，多模态支持"
    }
}

# 默认模型名
DEFAULT_MODEL_NAME = "deepseek"

@dataclass
class LLMConfig:
    """大模型配置"""
    name: str
    provider: str
    model_name: str
    api_key_env: str
    api_base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    description: str = ""


class LLMModule:
    """大模型模块 - 全局配置管理"""
    
    def __init__(self):
        self.current_llm: Optional[BaseChatModel] = None
        self.current_config: Optional[LLMConfig] = None
        self.current_model_name: Optional[str] = None
    
    def get_model_config(self, model_name: str = None) -> Optional[LLMConfig]:
        """从全局配置获取模型配置"""
        if not model_name:
            model_name = DEFAULT_MODEL_NAME
        
        if model_name not in GLOBAL_MODEL_CONFIGS:
            print(f"模型 {model_name} 不存在，使用默认模型 {DEFAULT_MODEL_NAME}")
            model_name = DEFAULT_MODEL_NAME
        
        config_dict = GLOBAL_MODEL_CONFIGS[model_name]
        return LLMConfig(**config_dict)
    
    def list_available_models(self) -> Dict[str, LLMConfig]:
        """列出所有可用的模型（API密钥已设置）"""
        available = {}
        for model_name, config_dict in GLOBAL_MODEL_CONFIGS.items():
            config = LLMConfig(**config_dict)
            if self._is_available(config):
                available[model_name] = config
        return available
    
    def _is_available(self, config: LLMConfig) -> bool:
        """检查模型是否可用"""
        api_key = os.getenv(config.api_key_env)
        return api_key is not None and api_key.strip() != ""
    
    def switch_model(self, model_name: str = None) -> bool:
        """切换到指定模型"""
        if not model_name:
            model_name = DEFAULT_MODEL_NAME
        
        config = self.get_model_config(model_name)
        if not config:
            return False
        
        if not self._is_available(config):
            print(f"模型 {config.name} 不可用，请检查API密钥环境变量 {config.api_key_env}")
            return False
        
        try:
            self.current_llm = self._create_llm(config)
            self.current_config = config
            self.current_model_name = model_name
            print(f"已切换到模型: {config.name}")
            return True
        except Exception as e:
            print(f"切换模型失败: {e}")
            return False
    
    def _create_llm(self, config: LLMConfig) -> BaseChatModel:
        """根据配置创建LLM实例"""
        api_key = os.getenv(config.api_key_env)
        
        if config.provider == "openai" or config.provider == "deepseek":
            kwargs = {
                "model": config.model_name,
                "api_key": api_key,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }
            if config.api_base_url:
                kwargs["base_url"] = config.api_base_url
            return ChatOpenAI(**kwargs)
        
        elif config.provider == "anthropic":
            return ChatAnthropic(
                model=config.model_name,
                api_key=api_key,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
        
        elif config.provider == "google":
            return ChatGoogleGenerativeAI(
                model=config.model_name,
                google_api_key=api_key,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
        
        else:
            raise ValueError(f"不支持的提供商: {config.provider}")
    
    def get_current_model(self) -> Optional[BaseChatModel]:
        """获取当前模型"""
        return self.current_llm
    
    def get_current_config(self) -> Optional[LLMConfig]:
        """获取当前模型配置"""
        return self.current_config
    
    def get_current_model_name(self) -> str:
        """获取当前模型名"""
        return self.current_model_name or DEFAULT_MODEL_NAME
    
    def is_ready(self) -> bool:
        """检查模块是否已准备就绪"""
        return self.current_llm is not None
    
    def ensure_model_ready(self, model_name: str = None) -> bool:
        """确保模型已准备就绪，如果没有则自动初始化"""
        if not model_name:
            model_name = DEFAULT_MODEL_NAME
        
        if self.is_ready() and self.current_model_name == model_name:
            return True
        
        return self.switch_model(model_name)


# 全局实例
llm_module = LLMModule() 