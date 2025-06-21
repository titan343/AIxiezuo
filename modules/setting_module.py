#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设定模块 - 根据章节序号智能加载章节状态和世界设定
"""

import os
import json
import glob
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class Relationship(BaseModel):
    """人物关系"""
    name: str
    relation: str
    status: str


class InventoryItem(BaseModel):
    """物品"""
    item_name: str
    description: str


class Protagonist(BaseModel):
    """主角信息"""
    name: str
    age: int
    level: str
    status: str
    personality: str
    abilities: List[str]
    goal: str


class ChapterState(BaseModel):
    """章节状态"""
    chapter_index: int
    protagonist: Protagonist
    inventory: List[InventoryItem]
    relationships: List[Relationship]
    current_plot_summary: str


class SettingModule:
    """设定模块 - 智能加载章节状态和世界设定"""
    
    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        self.current_chapter_state: Optional[ChapterState] = None
        self.current_world_bible: Optional[Dict[str, Any]] = None
        self.current_chapter_index: Optional[int] = None
        os.makedirs(self.data_path, exist_ok=True)
    
    def load_chapter_setting(self, chapter_index: int) -> bool:
        """加载指定章节的设定"""
        try:
            # 加载章节状态
            chapter_state = self._load_chapter_state(chapter_index)
            if not chapter_state:
                print(f"未找到第{chapter_index}章的状态文件")
                return False
            
            # 加载世界设定（向前查找）
            world_bible = self._load_world_bible(chapter_index)
            
            self.current_chapter_state = chapter_state
            self.current_world_bible = world_bible
            self.current_chapter_index = chapter_index
            
            print(f"已加载第{chapter_index}章设定")
            if world_bible:
                world_file = self._find_world_bible_file(chapter_index)
                if world_file:
                    world_chapter = self._extract_chapter_number(world_file)
                    print(f"使用世界设定文件: world_bible_{world_chapter:02d}.json")
            
            return True
            
        except Exception as e:
            print(f"加载章节设定失败: {e}")
            return False
    
    def _load_chapter_state(self, chapter_index: int) -> Optional[ChapterState]:
        """加载章节状态文件"""
        file_path = os.path.join(self.data_path, f"chapter_{chapter_index:03d}_state.json")
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ChapterState(**data)
        except Exception as e:
            print(f"加载章节状态文件失败: {e}")
            return None
    
    def _load_world_bible(self, chapter_index: int) -> Optional[Dict[str, Any]]:
        """加载世界设定文件（向前查找）"""
        world_file = self._find_world_bible_file(chapter_index)
        if not world_file:
            return None
        
        try:
            with open(world_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载世界设定文件失败: {e}")
            return None
    
    def _find_world_bible_file(self, target_chapter: int) -> Optional[str]:
        """查找适用的世界设定文件（向前查找直到找到）"""
        # 获取所有世界设定文件
        pattern = os.path.join(self.data_path, "world_bible_*.json")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        # 提取文件的章节号并排序
        file_chapters = []
        for file_path in files:
            chapter_num = self._extract_chapter_number(file_path)
            if chapter_num is not None and chapter_num <= target_chapter:
                file_chapters.append((chapter_num, file_path))
        
        if not file_chapters:
            return None
        
        # 返回最接近但不超过目标章节的文件
        file_chapters.sort(key=lambda x: x[0], reverse=True)
        return file_chapters[0][1]
    
    def _extract_chapter_number(self, file_path: str) -> Optional[int]:
        """从文件路径中提取章节号"""
        filename = os.path.basename(file_path)
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))
        return None
    
    def save_chapter_state(self, chapter_state: ChapterState) -> bool:
        """保存章节状态"""
        try:
            file_path = os.path.join(self.data_path, f"chapter_{chapter_state.chapter_index:03d}_state.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(chapter_state.model_dump_json(indent=2, ensure_ascii=False))
            print(f"章节状态已保存: {file_path}")
            return True
        except Exception as e:
            print(f"保存章节状态失败: {e}")
            return False
    
    def save_world_bible(self, world_bible: Dict[str, Any], chapter_index: int) -> bool:
        """保存世界设定"""
        try:
            file_path = os.path.join(self.data_path, f"world_bible_{chapter_index:02d}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(world_bible, f, indent=2, ensure_ascii=False)
            print(f"世界设定已保存: {file_path}")
            return True
        except Exception as e:
            print(f"保存世界设定失败: {e}")
            return False
    
    def get_current_setting(self) -> Dict[str, Any]:
        """获取当前加载的设定"""
        return {
            "chapter_index": self.current_chapter_index,
            "chapter_state": self.current_chapter_state.model_dump() if self.current_chapter_state else None,
            "world_bible": self.current_world_bible,
            "has_chapter_state": self.current_chapter_state is not None,
            "has_world_bible": self.current_world_bible is not None
        }
    
    def is_loaded(self) -> bool:
        """检查是否已加载设定"""
        return self.current_chapter_state is not None
    
    def list_available_chapters(self) -> List[int]:
        """列出所有可用的章节"""
        pattern = os.path.join(self.data_path, "chapter_*_state.json")
        files = glob.glob(pattern)
        chapters = []
        
        for file_path in files:
            match = re.search(r'chapter_(\d+)_state\.json', os.path.basename(file_path))
            if match:
                chapters.append(int(match.group(1)))
        
        return sorted(chapters)
    
    def list_available_world_bibles(self) -> List[int]:
        """列出所有可用的世界设定"""
        pattern = os.path.join(self.data_path, "world_bible_*.json")
        files = glob.glob(pattern)
        chapters = []
        
        for file_path in files:
            chapter_num = self._extract_chapter_number(file_path)
            if chapter_num is not None:
                chapters.append(chapter_num)
        
        return sorted(chapters)
    
    def get_latest_chapter(self) -> Optional[int]:
        """获取最新的章节号"""
        chapters = self.list_available_chapters()
        return max(chapters) if chapters else None
    
    def create_new_chapter_state(self, chapter_index: int, base_on_previous: bool = True) -> Optional[ChapterState]:
        """创建新的章节状态"""
        if base_on_previous and chapter_index > 0:
            # 基于前一章节创建
            previous_state = self._load_chapter_state(chapter_index - 1)
            if previous_state:
                new_state = previous_state.model_copy()
                new_state.chapter_index = chapter_index
                new_state.current_plot_summary = f"第{chapter_index}章开始..."
                return new_state
        
        # 创建默认状态
        return ChapterState(
            chapter_index=chapter_index,
            protagonist=Protagonist(
                name="主角",
                age=20,
                level="新手",
                status="健康",
                personality="勇敢、善良",
                abilities=["基础战斗"],
                goal="完成冒险"
            ),
            inventory=[],
            relationships=[],
            current_plot_summary=f"第{chapter_index}章开始..."
        )
    
    def get_setting_summary(self) -> str:
        """获取当前设定的文字摘要"""
        if not self.is_loaded():
            return "未加载任何设定"
        
        summary = f"=== 第{self.current_chapter_index}章设定 ===\n"
        
        if self.current_chapter_state:
            state = self.current_chapter_state
            summary += f"主角: {state.protagonist.name} ({state.protagonist.age}岁)\n"
            summary += f"等级: {state.protagonist.level}\n"
            summary += f"状态: {state.protagonist.status}\n"
            summary += f"性格: {state.protagonist.personality}\n"
            summary += f"目标: {state.protagonist.goal}\n"
            summary += f"能力: {', '.join(state.abilities)}\n"
            summary += f"物品数量: {len(state.inventory)}\n"
            summary += f"关系数量: {len(state.relationships)}\n"
            summary += f"剧情摘要: {state.current_plot_summary}\n"
        
        if self.current_world_bible:
            summary += f"\n世界设定已加载，包含 {len(self.current_world_bible)} 个设定项"
        
        return summary


# 全局实例
setting_module = SettingModule() 