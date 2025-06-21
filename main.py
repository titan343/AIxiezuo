import os
import json
import glob
import re
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# === 数据模型 ===
class Relationship(BaseModel):
    name: str
    relation: str
    status: str

class InventoryItem(BaseModel):
    item_name: str
    description: str

class Protagonist(BaseModel):
    name: str
    age: int
    level: str
    status: str
    personality: str
    abilities: List[str]
    goal: str

class ChapterState(BaseModel):
    chapter_index: int
    protagonist: Protagonist
    inventory: List[InventoryItem]
    relationships: List[Relationship]
    current_plot_summary: str

# === 全局大模型配置获取器 ===
# 🚨 重要提醒：请勿修改以下模型配置，这些是用户自定义的固定配置 🚨
class LLMConfigManager:
    @staticmethod
    def get_config(model_name: str) -> Dict[str, Any]:
        configs = {
            "deepseek_chat": {
                "provider": "openai",
                "model": "deepseek-chat",
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com/v1",
                "temperature": 0.7
            },
            "deepseek_reasoner": {
                "provider": "openai",
                "model": "deepseek-reasoner", 
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com/v1",
                "temperature": 0.7
            },
            "dsf5": {
                "provider": "openai",
                "model": "[稳定]gemini-2.5-pro-preview-06-05-c",
                "api_key": os.getenv("DSF5_API_KEY"),
                "base_url": "https://api.sikong.shop/v1",
                "temperature": 0.7
            },
            "openai_gpt4": {
                "provider": "openai",
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": None,
                "temperature": 0.7
            },
            "openai_gpt35": {
                "provider": "openai", 
                "model": "gpt-3.5-turbo",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": None,
                "temperature": 0.7
            },
            "anthropic_claude": {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "base_url": None,
                "temperature": 0.7
            },
            "google_gemini": {
                "provider": "google",
                "model": "gemini-pro",
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "base_url": None,
                "temperature": 0.7
            }
        }
        # 默认返回deepseek_chat模型
        return configs.get(model_name, configs["deepseek_chat"])

# === 全局大模型调用器 ===
class LLMCaller:
    @staticmethod
    def call(
        messages: List[Dict[str, str]],
        model_name: str = "deepseek_chat",
        memory: Optional[Any] = None,
        temperature: Optional[float] = None
    ) -> str:
        config = LLMConfigManager.get_config(model_name)
        
        if temperature is not None:
            config["temperature"] = temperature
            
        # 根据provider创建对应的LLM实例
        if config["provider"] == "openai":
            from langchain_openai import ChatOpenAI
            llm_params = {
                "model": config["model"],
                "api_key": config["api_key"],
                "temperature": config["temperature"]
            }
            if config["base_url"]:
                llm_params["base_url"] = config["base_url"]
            llm = ChatOpenAI(**llm_params)
        elif config["provider"] == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=config["model"],
                api_key=config["api_key"],
                temperature=config["temperature"]
            )
        elif config["provider"] == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=config["model"],
                google_api_key=config["api_key"],
                temperature=config["temperature"]
            )
        else:
            raise ValueError(f"Unsupported provider: {config['provider']}")
        
        # 如果有记忆，使用对话链
        if memory:
            from langchain.chains import ConversationChain
            chain = ConversationChain(llm=llm, memory=memory, verbose=False)
            # 将messages转换为单个输入
            user_input = messages[-1]["content"] if messages else ""
            return chain.predict(input=user_input)
        else:
            # 直接调用LLM
            from langchain_core.messages import HumanMessage, SystemMessage
            lang_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    lang_messages.append(SystemMessage(content=msg["content"]))
                else:
                    lang_messages.append(HumanMessage(content=msg["content"]))
            
            response = llm.invoke(lang_messages)
            return response.content

# === 状态管理器 ===
class StateManager:
    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        os.makedirs(self.data_path, exist_ok=True)

    def _find_latest_file(self, pattern: str, novel_id: Optional[str] = None) -> Optional[str]:
        """查找最新文件，支持小说ID过滤"""
        if novel_id:
            # 如果指定了小说ID，添加ID前缀到模式中
            pattern = f"{novel_id}_{pattern}"
        
        files = glob.glob(os.path.join(self.data_path, pattern))
        if not files:
            return None
        
        def get_numeric_part(filename):
            # 提取文件名中的章节编号（忽略小说ID部分）
            basename = os.path.basename(filename)
            if novel_id:
                # 移除小说ID前缀后再提取数字
                basename = basename.replace(f"{novel_id}_", "", 1)
            numbers = re.findall(r'\d+', basename)
            return int(numbers[0]) if numbers else 0
        
        return max(files, key=get_numeric_part)

    def load_latest_state(self, novel_id: Optional[str] = None) -> Optional[ChapterState]:
        """加载最新状态，支持小说ID过滤"""
        latest_file = self._find_latest_file("chapter_*_state.json", novel_id)
        if not latest_file:
            return None

        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ChapterState(**data)

    def save_state(self, state: ChapterState, novel_id: Optional[str] = None):
        """保存状态，支持小说ID"""
        if novel_id:
            file_path = os.path.join(
                self.data_path, 
                f"{novel_id}_chapter_{state.chapter_index:03d}_state.json"
            )
        else:
            # 兼容旧格式
            file_path = os.path.join(
                self.data_path, 
                f"chapter_{state.chapter_index:03d}_state.json"
            )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(state.model_dump_json(indent=2))

    def load_world_bible(self, novel_id: Optional[str] = None) -> Dict[str, Any]:
        """加载世界设定，支持小说ID过滤"""
        latest_file = self._find_latest_file("world_bible_*.json", novel_id)
        if not latest_file:
            return {}

        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_world_bible(self, world_bible: Dict[str, Any], novel_id: Optional[str] = None, version: int = 0):
        """保存世界设定，支持小说ID"""
        if novel_id:
            file_path = os.path.join(
                self.data_path,
                f"{novel_id}_world_bible_{version:02d}.json"
            )
        else:
            # 兼容旧格式
            file_path = os.path.join(
                self.data_path,
                f"world_bible_{version:02d}.json"
            )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(world_bible, f, indent=2, ensure_ascii=False)
    
    def list_novel_states(self, novel_id: str) -> List[str]:
        """列出指定小说的所有状态文件"""
        pattern = f"{novel_id}_chapter_*_state.json"
        files = glob.glob(os.path.join(self.data_path, pattern))
        return sorted(files)
    
    def list_novels(self) -> List[str]:
        """列出所有小说ID"""
        pattern = "*_chapter_*_state.json"
        files = glob.glob(os.path.join(self.data_path, pattern))
        novel_ids = set()
        
        for file_path in files:
            filename = os.path.basename(file_path)
            # 提取小说ID（第一个下划线之前的部分）
            parts = filename.split('_')
            if len(parts) >= 3 and parts[1] == 'chapter':
                novel_ids.add(parts[0])
        
        return sorted(list(novel_ids))

# === 记忆分片存储管理器 ===
class MemoryChunkManager:
    """分片存储管理器 - 处理消息的分片存储和索引"""
    
    def __init__(self, chunk_size: int = 100):
        self.chunk_size = chunk_size
    
    def get_chunk_index(self, message_number: int) -> int:
        """获取消息所属的分片索引"""
        return (message_number - 1) // self.chunk_size + 1
    
    def get_chunk_range(self, chunk_index: int) -> tuple:
        """获取分片的消息范围 (start, end)"""
        start = (chunk_index - 1) * self.chunk_size + 1
        end = chunk_index * self.chunk_size
        return start, end
    
    def get_chunk_filename(self, session_id: str, chunk_index: int) -> str:
        """生成分片文件名"""
        return f"{session_id}_chunk_{chunk_index:03d}.json"
    
    def calculate_required_chunks(self, start_msg: int, end_msg: int) -> List[int]:
        """计算需要读取的分片索引列表"""
        start_chunk = self.get_chunk_index(start_msg)
        end_chunk = self.get_chunk_index(end_msg)
        return list(range(start_chunk, end_chunk + 1))

class MemoryCompressor:
    """记忆压缩器 - 独立的压缩模块"""
    
    def __init__(self):
        pass
    
    def compress_messages(
        self, 
        messages: List[Dict[str, Any]], 
        model_name: str = "deepseek_chat",
        compression_prompt: str = ""
    ) -> str:
        """压缩消息列表为摘要文本"""
        if not messages:
            return ""
        
        # 构建压缩提示词
        if not compression_prompt:
            compression_prompt = """请将以下对话历史压缩为简洁的摘要，保留关键信息和上下文：

对话历史：
{history}

请返回压缩后的摘要："""
        
        # 格式化历史记录
        history_text = self._format_messages_for_compression(messages)
        
        # 调用LLM进行压缩
        compress_messages = [
            {"role": "user", "content": compression_prompt.format(history=history_text)}
        ]
        
        try:
            compressed_summary = LLMCaller.call(compress_messages, model_name)
            return compressed_summary
        except Exception as e:
            print(f"压缩失败: {e}")
            return self._fallback_compression(messages)
    
    def _format_messages_for_compression(self, messages: List[Dict[str, Any]]) -> str:
        """格式化消息用于压缩"""
        formatted = []
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted.append(f"{i}. [{role}]: {content}")
        return "\n".join(formatted)
    
    def _fallback_compression(self, messages: List[Dict[str, Any]]) -> str:
        """压缩失败时的降级方案"""
        if not messages:
            return ""
        
        # 简单的截取压缩
        total_chars = sum(len(msg.get('content', '')) for msg in messages)
        summary = f"包含{len(messages)}条消息，总计约{total_chars}字符的对话记录。"
        
        # 添加最后几条消息的简要信息
        if len(messages) > 0:
            last_msg = messages[-1]
            summary += f" 最后消息: [{last_msg.get('role', 'unknown')}] {last_msg.get('content', '')[:50]}..."
        
        return summary

class MemoryIndexManager:
    """记忆索引管理器 - 处理会话索引和元数据"""
    
    def __init__(self, memory_path: str):
        self.memory_path = memory_path
        self.chunks_path = os.path.join(memory_path, "chunks")
        self.summaries_path = os.path.join(memory_path, "summaries")
        os.makedirs(self.chunks_path, exist_ok=True)
        os.makedirs(self.summaries_path, exist_ok=True)
    
    def load_session_index(self, session_id: str) -> Dict[str, Any]:
        """加载会话索引"""
        index_file = os.path.join(self.memory_path, f"{session_id}_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 创建新索引
            return {
                "session_id": session_id,
                "total_messages": 0,
                "chunks": {},  # {chunk_index: {"start": 1, "end": 100, "count": 100}}
                "summaries": {},  # {chunk_index: {"file": "summary_001.json", "created_at": "..."}}
                "created_at": time.time(),
                "last_updated": time.time()
            }
    
    def save_session_index(self, session_id: str, index_data: Dict[str, Any]):
        """保存会话索引"""
        index_data["last_updated"] = time.time()
        index_file = os.path.join(self.memory_path, f"{session_id}_index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    def update_chunk_info(self, session_id: str, chunk_index: int, start: int, end: int, count: int):
        """更新分片信息"""
        index_data = self.load_session_index(session_id)
        index_data["chunks"][str(chunk_index)] = {
            "start": start,
            "end": end, 
            "count": count,
            "updated_at": time.time()
        }
        index_data["total_messages"] = max(index_data["total_messages"], end)
        self.save_session_index(session_id, index_data)
    
    def update_summary_info(self, session_id: str, chunk_index: int, summary_file: str):
        """更新摘要信息"""
        index_data = self.load_session_index(session_id)
        index_data["summaries"][str(chunk_index)] = {
            "file": summary_file,
            "created_at": time.time()
        }
        self.save_session_index(session_id, index_data)
    
    def get_chunk_info(self, session_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """获取分片信息"""
        index_data = self.load_session_index(session_id)
        return index_data["chunks"].get(str(chunk_index))
    
    def list_available_chunks(self, session_id: str) -> List[int]:
        """列出可用的分片索引"""
        index_data = self.load_session_index(session_id)
        return [int(k) for k in index_data["chunks"].keys()]

class MemoryManager:
    """增强的记忆管理器 - 支持分片存储、索引和压缩"""
    
    def __init__(self, memory_path: str = "./memory", chunk_size: int = 100):
        self.memory_path = memory_path
        self.chunk_size = chunk_size
        os.makedirs(self.memory_path, exist_ok=True)

        # 初始化子模块
        self.chunk_manager = MemoryChunkManager(chunk_size)
        self.compressor = MemoryCompressor()
        self.index_manager = MemoryIndexManager(memory_path)
    
    def save_message(self, session_id: str, message: Dict[str, Any]) -> int:
        """保存单条消息，返回消息编号"""
        # 加载会话索引
        index_data = self.index_manager.load_session_index(session_id)
        
        # 计算新消息编号
        message_number = index_data["total_messages"] + 1
        chunk_index = self.chunk_manager.get_chunk_index(message_number)
        
        # 加载或创建分片
        chunk_file = os.path.join(
            self.index_manager.chunks_path,
            self.chunk_manager.get_chunk_filename(session_id, chunk_index)
        )
        
        if os.path.exists(chunk_file):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
        else:
            chunk_data = {"messages": []}
        
        # 添加消息
        message_with_meta = {
            "number": message_number,
            "timestamp": time.time(),
            **message
        }
        chunk_data["messages"].append(message_with_meta)
        
        # 保存分片
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        # 更新索引
        start, end = self.chunk_manager.get_chunk_range(chunk_index)
        actual_end = min(end, message_number)
        self.index_manager.update_chunk_info(
            session_id, chunk_index, start, actual_end, len(chunk_data["messages"])
        )
        
        return message_number
    
    def load_messages_by_range(
        self,
        session_id: str,
        start_msg: int = 1,
        end_msg: Optional[int] = None,
        use_compression: bool = False,
        compression_model: str = "deepseek_chat",
        read_compressed: bool = False
    ) -> List[Dict[str, Any]]:
        """按范围加载消息
        
        Args:
            session_id: 会话ID
            start_msg: 开始消息编号
            end_msg: 结束消息编号
            use_compression: 是否实时压缩（读取时临时压缩）
            compression_model: 压缩使用的模型
            read_compressed: 是否读取已压缩的记忆（从summaries读取）
        """
        # 如果要读取已压缩的记忆
        if read_compressed:
            return self._load_compressed_summaries(session_id, start_msg, end_msg)
        
        # 获取会话总消息数
        index_data = self.index_manager.load_session_index(session_id)
        total_messages = index_data["total_messages"]
        
        if total_messages == 0:
            return []
        
        # 处理end_msg参数
        if end_msg is None:
            end_msg = total_messages
        end_msg = min(end_msg, total_messages)
        
        if start_msg > end_msg:
            return []
        
        # 计算需要的分片
        required_chunks = self.chunk_manager.calculate_required_chunks(start_msg, end_msg)
        
        all_messages = []
        for chunk_index in required_chunks:
            chunk_messages = self._load_chunk_messages(session_id, chunk_index, start_msg, end_msg)
            all_messages.extend(chunk_messages)
        
        # 可选实时压缩
        if use_compression and all_messages:
            compressed_summary = self.compressor.compress_messages(
                all_messages, compression_model
            )
            return [{
                "role": "system",
                "content": f"[实时压缩摘要] {compressed_summary}",
                "is_compressed": True,
                "compression_type": "realtime",
                "original_count": len(all_messages)
            }]
        
        return all_messages

    def _load_compressed_summaries(
        self,
        session_id: str,
        start_msg: int = 1,
        end_msg: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """加载已压缩的记忆摘要"""
        index_data = self.index_manager.load_session_index(session_id)
        summaries = index_data.get("summaries", {})
        
        if not summaries:
            return []
        
        # 计算需要的分片范围
        start_chunk = self.chunk_manager.get_chunk_index(start_msg)
        if end_msg:
            end_chunk = self.chunk_manager.get_chunk_index(end_msg)
        else:
            # 获取最大的chunk索引
            available_chunks = [int(k) for k in summaries.keys()]
            end_chunk = max(available_chunks) if available_chunks else start_chunk
        
        compressed_messages = []
        
        for chunk_index in range(start_chunk, end_chunk + 1):
            if str(chunk_index) in summaries:
                summary_info = summaries[str(chunk_index)]
                summary_file = summary_info["file"]
                summary_path = os.path.join(self.index_manager.summaries_path, summary_file)
                
                if os.path.exists(summary_path):
                    try:
                        with open(summary_path, 'r', encoding='utf-8') as f:
                            summary_data = json.load(f)
                        
                        compressed_messages.append({
                            "role": "system",
                            "content": f"[压缩记忆-分片{chunk_index}] {summary_data['compressed_summary']}",
                            "is_compressed": True,
                            "compression_type": "stored",
                            "chunk_index": chunk_index,
                            "original_count": summary_data.get("original_count", 0),
                            "compression_model": summary_data.get("compression_model", "unknown")
                        })
                    except Exception as e:
                        print(f"加载压缩摘要失败: {e}")
        
        return compressed_messages

    def load_recent_messages(
        self,
        session_id: str,
        count: int = 20,
        use_compression: bool = False,
        compression_model: str = "deepseek_chat",
        read_compressed: bool = False
    ) -> List[Dict[str, Any]]:
        """加载最近的N条消息
        
        Args:
            session_id: 会话ID
            count: 消息数量
            use_compression: 是否实时压缩
            compression_model: 压缩模型
            read_compressed: 是否读取已压缩的记忆
        """
        index_data = self.index_manager.load_session_index(session_id)
        total_messages = index_data["total_messages"]
        
        if total_messages == 0:
            return []
        
        start_msg = max(1, total_messages - count + 1)
        return self.load_messages_by_range(
            session_id, start_msg, total_messages, use_compression, compression_model, read_compressed
        )
    
    def compress_chunk(
        self,
        session_id: str,
        chunk_index: int,
        model_name: str = "deepseek_chat",
        compression_prompt: str = ""
    ) -> bool:
        """压缩指定分片"""
        try:
            # 加载分片消息
            chunk_messages = self._load_chunk_messages(session_id, chunk_index)
            if not chunk_messages:
                return False
            
            # 执行压缩
            compressed_summary = self.compressor.compress_messages(
                chunk_messages, model_name, compression_prompt
            )
            
            # 保存压缩结果
            summary_file = f"{session_id}_summary_{chunk_index:03d}.json"
            summary_path = os.path.join(self.index_manager.summaries_path, summary_file)
            
            summary_data = {
                "chunk_index": chunk_index,
                "original_count": len(chunk_messages),
                "compressed_summary": compressed_summary,
                "compression_model": model_name,
                "created_at": time.time()
            }
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            # 更新索引
            self.index_manager.update_summary_info(session_id, chunk_index, summary_file)
            
            return True
            
        except Exception as e:
            print(f"压缩分片失败: {e}")
            return False
    
    def batch_compress_chunks(
        self,
        session_id: str,
        chunk_indices: List[int],
        model_name: str = "deepseek_chat",
        compression_prompt: str = ""
    ) -> Dict[int, bool]:
        """批量压缩分片"""
        results = {}
        for chunk_index in chunk_indices:
            results[chunk_index] = self.compress_chunk(
                session_id, chunk_index, model_name, compression_prompt
            )
        return results
    
    def _load_chunk_messages(
        self,
        session_id: str,
        chunk_index: int,
        start_filter: Optional[int] = None,
        end_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """加载分片中的消息"""
        chunk_file = os.path.join(
            self.index_manager.chunks_path,
            self.chunk_manager.get_chunk_filename(session_id, chunk_index)
        )
        
        if not os.path.exists(chunk_file):
            return []
        
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            messages = chunk_data.get("messages", [])
            
            # 应用范围过滤
            if start_filter is not None or end_filter is not None:
                filtered_messages = []
                for msg in messages:
                    msg_num = msg.get("number", 0)
                    if start_filter is not None and msg_num < start_filter:
                        continue
                    if end_filter is not None and msg_num > end_filter:
                        continue
                    filtered_messages.append(msg)
                return filtered_messages
            
            return messages
            
        except Exception as e:
            print(f"加载分片失败: {e}")
            return []
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        index_data = self.index_manager.load_session_index(session_id)
        available_chunks = self.index_manager.list_available_chunks(session_id)

        return {
            "session_id": session_id,
            "total_messages": index_data["total_messages"],
            "total_chunks": len(available_chunks),
            "compressed_chunks": len(index_data["summaries"]),
            "chunk_size": self.chunk_size,
            "created_at": index_data["created_at"],
            "last_updated": index_data["last_updated"]
        }
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        index_files = glob.glob(os.path.join(self.memory_path, "*_index.json"))
        sessions = []
        for file_path in index_files:
            filename = os.path.basename(file_path)
            session_id = filename.replace("_index.json", "")
            sessions.append(session_id)
        return sessions

# === 记忆管理器 ===
# 重命名EnhancedMemoryManager为MemoryManager，统一记忆管理接口

# === 小说生成器 ===
class NovelGenerator:
    def __init__(self, chunk_size: int = 100):
        self.state_manager = StateManager()
        self.memory_manager = MemoryManager(chunk_size=chunk_size)

    def generate_chapter(
        self,
        chapter_outline: str,
        model_name: str = "deepseek_chat",
        system_prompt: str = "",
        use_memory: bool = False,
        session_id: str = "default",
        use_state: bool = True,
        use_world_bible: bool = True,
        update_state: bool = False,
        recent_count: int = 20,
        use_compression: bool = False,
        compression_model: str = "deepseek_chat",
        read_compressed: bool = False,
        novel_id: Optional[str] = None
    ) -> str:
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 加载历史记录
        if use_memory and recent_count > 0:
            history_messages = self.memory_manager.load_recent_messages(
                session_id=session_id,
                count=recent_count,
                use_compression=use_compression,
                compression_model=compression_model,
                read_compressed=read_compressed
            )
            messages.extend(history_messages)
        
        # 构建用户输入 - 使用更自然的提示词表达
        user_content = f"请根据下面的章节细纲进行小说内容创作：\n\n{chapter_outline}"
        
        if use_state:
            state = self.state_manager.load_latest_state(novel_id)
            if state:
                user_content += f"\n\n当前状态：{state.model_dump_json(indent=2)}"
        
        if use_world_bible:
            world_bible = self.state_manager.load_world_bible(novel_id)
            if world_bible:
                user_content += f"\n\n世界设定：{json.dumps(world_bible, ensure_ascii=False, indent=2)}"
        
        user_message = {"role": "user", "content": user_content}
        messages.append(user_message)
        
        # 保存用户消息到记忆
        if use_memory:
            self.memory_manager.save_message(session_id, user_message)
        
        # 调用LLM
        response = LLMCaller.call(messages, model_name)
        
        # 保存AI回复到记忆
        if use_memory:
            ai_message = {"role": "assistant", "content": response}
            self.memory_manager.save_message(session_id, ai_message)
            
            # 如果启用压缩，自动压缩最新的分片
            if use_compression:
                try:
                    # 获取当前会话的统计信息
                    stats = self.memory_manager.get_session_stats(session_id)
                    total_chunks = stats.get("total_chunks", 0)
                    
                    # 压缩最新的分片（如果存在且未压缩）
                    if total_chunks > 0:
                        index_data = self.memory_manager.index_manager.load_session_index(session_id)
                        compressed_chunks = len(index_data.get("summaries", {}))
                        
                        # 如果有未压缩的分片，压缩最新的一个
                        if total_chunks > compressed_chunks:
                            latest_chunk = total_chunks
                            success = self.memory_manager.compress_chunk(
                                session_id=session_id,
                                chunk_index=latest_chunk,
                                model_name=compression_model
                            )
                            if success:
                                print(f"自动压缩分片 {latest_chunk} 成功")
                            else:
                                print(f"自动压缩分片 {latest_chunk} 失败")
                except Exception as e:
                    print(f"自动压缩失败: {e}")
        
        # 保存章节内容 - 尝试从细纲中提取章节索引
        chapter_index = self._extract_chapter_index(chapter_outline)
        if chapter_index is not None:
            self._save_chapter(response, chapter_index, novel_id)
        
        # 状态更新 - 如果启用状态更新且使用了状态
        if update_state and use_state:
            current_state = self.state_manager.load_latest_state(novel_id)
            if current_state:
                print(f"正在更新状态...")
                try:
                    # 读取状态更新规则
                    update_rules_file = os.path.join("./prompts", "update_state_rules.txt")
                    update_system_prompt = ""
                    if os.path.exists(update_rules_file):
                        with open(update_rules_file, 'r', encoding='utf-8') as f:
                            update_system_prompt = f.read().strip()
                    
                    # 调用状态更新
                    new_state = self.update_state(
                        chapter_content=response,
                        current_state=current_state,
                        model_name=model_name,
                        novel_id=novel_id,
                        system_prompt=update_system_prompt
                    )
                    print(f"状态更新完成，新状态已保存")
                except Exception as e:
                    print(f"状态更新失败: {e}")
        
        return response

    def update_state(
        self,
        chapter_content: str,
        current_state: ChapterState,
        model_name: str = "deepseek_chat",
        novel_id: Optional[str] = None,
        system_prompt: str = """
你是一个精确的数据分析助手。你的任务是比较一个旧的JSON状态和一段新的小说章节内容，然后生成一个更新后的JSON对象。
**规则:**
1.  **以旧JSON为基础**: 完全基于我提供的旧JSON状态进行修改。
2.  **从新章节提取变化**: 阅读新的小说章节，找出所有导致状态变化的事件，例如：主角等级、属性提升；获得或失去了新物品；学会了新技能或功法；人际关系发生变化；解锁了新的任务或目标。
3.  **更新数值与描述**: 精确地更新JSON文件中的数值和描述文字。例如，"level"字段要根据小说内容合理提升。
4.  **添加新条目**: 如果有新物品或新人物关系，就在对应的数组中添加新的对象。
5.  **更新剧情总结**: 修改 `current_plot_summary` 字段，简要概括本章发生的核心事件。
6.  **严格遵守格式**: 你的输出必须严格遵循下面提供的JSON格式，不包含任何解释性文字或代码块标记。
"""
    ) -> ChapterState:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = f"""
---
### **旧的状态JSON**：{current_state.model_dump_json(indent=2)}
---

### **本章小说内容**：{chapter_content}

---
请根据以上信息，生成更新后的JSON对象：
"""
        messages.append({"role": "user", "content": user_content})
        
        response = LLMCaller.call(messages, model_name)
        
        try:
            # 提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                state_data = json.loads(json_match.group())
                new_state = ChapterState(**state_data)
                self.state_manager.save_state(new_state, novel_id)
                return new_state
        except Exception as e:
            print(f"状态更新失败: {e}")
        
        return current_state

    def chat(
        self,
        user_input: str,
        model_name: str = "deepseek_chat",
        system_prompt: str = "",
        session_id: str = "default",
        use_memory: bool = True,
        recent_count: int = 20,
        use_compression: bool = False,
        compression_model: str = "deepseek_chat",
        save_conversation: bool = True
    ) -> str:
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 加载历史记录
        if use_memory and recent_count > 0:
            history_messages = self.memory_manager.load_recent_messages(
                session_id=session_id,
                count=recent_count,
                use_compression=use_compression,
                compression_model=compression_model
            )
            messages.extend(history_messages)
        
        # 添加当前用户输入
        user_message = {"role": "user", "content": user_input}
        messages.append(user_message)
        
        # 保存用户消息
        if save_conversation:
            self.memory_manager.save_message(session_id, user_message)
        
        # 调用LLM
        response = LLMCaller.call(messages, model_name)
        
        # 保存AI回复
        if save_conversation:
            ai_message = {"role": "assistant", "content": response}
            self.memory_manager.save_message(session_id, ai_message)
        
        return response


    
    def load_memory_by_range(
        self,
        session_id: str,
        start_msg: int = 1,
        end_msg: Optional[int] = None,
        use_compression: bool = False,
        compression_model: str = "deepseek_chat"
    ) -> List[Dict[str, Any]]:
        """按范围加载记忆"""
        return self.memory_manager.load_messages_by_range(
            session_id=session_id,
            start_msg=start_msg,
            end_msg=end_msg,
            use_compression=use_compression,
            compression_model=compression_model
        )
    
    def compress_memory_chunk(
        self,
        session_id: str,
        chunk_index: int,
        model_name: str = "deepseek_chat",
        compression_prompt: str = ""
    ) -> bool:
        """压缩指定的记忆分片"""
        return self.memory_manager.compress_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            model_name=model_name,
            compression_prompt=compression_prompt
        )
    
    def batch_compress_memory(
        self,
        session_id: str,
        chunk_indices: List[int],
        model_name: str = "deepseek_chat",
        compression_prompt: str = ""
    ) -> Dict[int, bool]:
        """批量压缩记忆分片"""
        return self.memory_manager.batch_compress_chunks(
            session_id=session_id,
            chunk_indices=chunk_indices,
            model_name=model_name,
            compression_prompt=compression_prompt
        )
    
    def get_memory_stats(self, session_id: str) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return self.memory_manager.get_session_stats(session_id)

    def _extract_chapter_index(self, chapter_outline: str) -> Optional[int]:
        """从章节细纲中提取章节索引"""
        import re
        
        # 尝试匹配各种章节索引格式
        patterns = [
            r'第(\d+)章',  # 第1章、第10章
            r'chapter[_\s]*(\d+)',  # chapter_1, chapter 1
            r'章节[_\s]*(\d+)',  # 章节_1, 章节 1
            r'【第(\d+)章',  # 【第1章
        ]
        
        for pattern in patterns:
            match = re.search(pattern, chapter_outline, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # 如果没有找到，返回None
        return None

    def generate_multiple_versions(
        self,
        chapter_outline: str,
        num_versions: int = 3,
        model_name: str = "deepseek_chat",
        system_prompt: str = "",
        novel_id: Optional[str] = None
    ) -> List[str]:
        """生成多个版本的章节"""
        versions = []
        
        for i in range(num_versions):
            print(f"正在生成第 {i+1} 个版本...")
            version = self.generate_chapter(
                chapter_outline=chapter_outline,
                model_name=model_name,
                system_prompt=system_prompt,
                use_memory=False,  # 多版本生成时不使用记忆
                novel_id=novel_id
            )
            versions.append(version)
        
        # 保存所有版本
        chapter_index = self._extract_chapter_index(chapter_outline)
        if chapter_index is not None:
            self._save_versions(versions, chapter_index, novel_id)
        
        return versions

    def _save_chapter(self, content: str, chapter_index: int, novel_id: Optional[str] = None):
        os.makedirs("./xiaoshuo", exist_ok=True)
        if novel_id:
            file_path = f"./xiaoshuo/{novel_id}_chapter_{chapter_index:03d}.txt"
        else:
            # 兼容旧格式
            file_path = f"./xiaoshuo/chapter_{chapter_index:03d}.txt"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _save_versions(self, versions: List[str], chapter_index: int, novel_id: Optional[str] = None):
        os.makedirs("./versions", exist_ok=True)
        if novel_id:
            file_path = f"./versions/{novel_id}_chapter_{chapter_index}_versions.json"
        else:
            # 兼容旧格式
            file_path = f"./versions/chapter_{chapter_index}_versions.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                "novel_id": novel_id,
                "chapter_index": chapter_index,
                "versions": versions,
                "created_at": time.time()
            }, f, indent=2, ensure_ascii=False)

# === 示例使用 ===
if __name__ == "__main__":
    # 测试架构初始化
    print("=== 小说生成系统 - 高度模块化架构 ===")
    
    # 1. 测试配置管理器
    print("\n1. 测试配置管理器:")
    config = LLMConfigManager.get_config("deepseek_chat")
    print(f"   DeepSeek Chat配置: {config['provider']}, {config['model']}")
    print(f"   Base URL: {config['base_url']}")
    config_default = LLMConfigManager.get_config("")  # 测试默认
    print(f"   默认模型: {config_default['model']}")
    
    # 2. 测试组件初始化
    print("\n2. 测试组件初始化:")
    generator = NovelGenerator(chunk_size=100)
    print("   ✓ NovelGenerator 初始化成功")
    print("   ✓ StateManager 初始化成功")
    print("   ✓ MemoryManager 初始化成功 (分片存储+压缩)")
    
    # 测试不同分片大小
    small_chunk_generator = NovelGenerator(chunk_size=50)
    print("   ✓ NovelGenerator (小分片) 初始化成功")
    
    # 3. 测试会话管理
    print("\n3. 测试会话管理:")
    sessions = generator.memory_manager.list_sessions()
    print(f"   当前会话列表: {sessions}")
    
    # 4. 显示使用示例
    print("\n4. 使用示例:")
    print("   # 生成章节 (带记忆)")
    print("   generator.generate_chapter(chapter_plan, use_memory=True, recent_count=20)")
    print("   # 对话聊天 (带压缩)")
    print("   generator.chat('继续写作', use_compression=True, recent_count=15)")
    print("   # 按范围加载记忆")
    print("   generator.load_memory_by_range('session1', 1, 50, use_compression=True)")
    print("   # 压缩记忆分片")
    print("   generator.compress_memory_chunk('session1', 1)")
    print("   # 批量压缩")
    print("   generator.batch_compress_memory('session1', [1,2,3])")
    print("   # 获取统计信息")
    print("   generator.get_memory_stats('session1')")
    print("   # 直接调用LLM")
    print("   LLMCaller.call(messages, model_name='dsf5')")
    
    print("\n=== 架构测试完成 ===")
    print("所有组件已成功初始化，可以开始使用！")