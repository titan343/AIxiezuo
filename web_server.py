#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说生成系统 - Web服务器
提供API接口对接前端，实现模版管理和小说生成功能
"""

import os
import json
import time
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from main import NovelGenerator, LLMCaller

app = Flask(__name__)
CORS(app)

# 全局配置
if getattr(sys, 'frozen', False):
    WEB_DIR = os.path.join(os.path.dirname(sys.executable), 'web')
else:
    WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
TEMPLATES_DIR = "./templates"
XIAOSHUO_DIR = "./xiaoshuo"

# 确保目录存在
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(XIAOSHUO_DIR, exist_ok=True)

# 全局实例
generator = NovelGenerator()

def load_template_index():
    """加载模版索引文件"""
    index_file = os.path.join(TEMPLATES_DIR, "template_index.json")
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "templates": {}}

def save_template_index(index_data):
    """保存模版索引文件"""
    index_file = os.path.join(TEMPLATES_DIR, "template_index.json")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

# ===== 静态文件服务 =====
@app.route('/')
def index():
    """主页"""
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory(WEB_DIR, filename)

# ===== API接口 =====
@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "API服务正常"})

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """获取模版列表"""
    try:
        index_data = load_template_index()
        return jsonify(index_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates', methods=['POST'])
def save_template():
    """保存模版"""
    try:
        data = request.json
        
        # 验证必需字段
        required_fields = ['id', 'name', 'files', 'contents']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必需字段: {field}"}), 400
        
        template_id = data['id']
        
        # 加载现有索引
        index_data = load_template_index()
        
        # 保存提示词文件
        for file_type, content in data['contents'].items():
            filename = data['files'][file_type]
            file_path = os.path.join(TEMPLATES_DIR, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 更新索引
        template_info = {
            "id": template_id,
            "name": data['name'],
            "category": data.get('category', ''),
            "description": data.get('description', ''),
            "author": "用户创建",
            "created_date": time.strftime("%Y-%m-%d"),
            "files": data['files'],
            "word_count_range": data.get('word_count_range', {"min": 2000, "max": 3000})
        }
        
        index_data['templates'][template_id] = template_info
        index_data['last_updated'] = time.strftime("%Y-%m-%d")
        
        # 保存索引
        save_template_index(index_data)
        
        return jsonify({"message": "模版保存成功", "template_id": template_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/template-file/<filename>')
def get_template_file(filename):
    """获取模版文件内容"""
    try:
        file_path = os.path.join(TEMPLATES_DIR, filename)
        if not os.path.exists(file_path):
            # 如果模版文件不存在，尝试从prompts目录读取默认文件
            prompts_path = os.path.join("./prompts", filename.split('_', 1)[-1])
            if os.path.exists(prompts_path):
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return "", 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_novel():
    """生成小说"""
    try:
        data = request.json
        
        # 获取参数
        template_id = data.get("template_id")
        chapter_outline = data.get("chapter_outline")  # 改为章节细纲
        model_name = data.get("model_name", "deepseek_chat")
        update_model_name = data.get("update_model_name")
        use_state = data.get("use_state", True)
        use_world_bible = data.get("use_world_bible", True)
        update_state = data.get("update_state", False)
        session_id = data.get("session_id", "default")
        novel_id = data.get("novel_id")
        use_previous_chapters = data.get("use_previous_chapters", False)
        previous_chapters_count = data.get("previous_chapters_count", 1)
        
        if not template_id:
            return jsonify({"error": "缺少模版ID"}), 400
        
        if not chapter_outline:
            return jsonify({"error": "缺少章节细纲"}), 400
        
        # 加载模版
        index_data = load_template_index()
        if template_id not in index_data['templates']:
            return jsonify({"error": f"模版不存在: {template_id}"}), 404
        
        template = index_data['templates'][template_id]
        
        # 读取模版文件内容
        writer_role_file = os.path.join(TEMPLATES_DIR, template['files']['writer_role'])
        writing_rules_file = os.path.join(TEMPLATES_DIR, template['files']['writing_rules'])
        
        writer_role = ""
        writing_rules = ""
        
        if os.path.exists(writer_role_file):
            with open(writer_role_file, 'r', encoding='utf-8') as f:
                writer_role = f.read()
        
        if os.path.exists(writing_rules_file):
            with open(writing_rules_file, 'r', encoding='utf-8') as f:
                writing_rules = f.read()
        
        # 构建系统提示
        system_prompt = f"{writer_role}\n\n{writing_rules}".strip()
        
        # 生成内容
        content = generator.generate_chapter(
            chapter_outline=chapter_outline,  # 使用章节细纲
            model_name=model_name,
            system_prompt=system_prompt,
            session_id=session_id,
            use_state=use_state,
            use_world_bible=use_world_bible,
            update_state=update_state,
            update_model_name=update_model_name,
            novel_id=novel_id,
            use_previous_chapters=use_previous_chapters,
            previous_chapters_count=previous_chapters_count
        )
        
        return jsonify({
            "content": content,
            "template_used": template.get('name', template_id),
            "novel_id": novel_id,
            "word_count": len(content),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        print(f"生成错误: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/novels', methods=['GET'])
def get_novels():
    """获取所有小说列表"""
    try:
        novels = generator.state_manager.list_novels()
        return jsonify({"novels": novels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/novels/<novel_id>/states', methods=['GET'])
def get_novel_states(novel_id):
    """获取指定小说的状态文件列表"""
    try:
        states = generator.state_manager.list_novel_states(novel_id)
        # 提取文件信息
        state_info = []
        for state_file in states:
            filename = os.path.basename(state_file)
            # 提取章节编号
            parts = filename.split('_')
            if len(parts) >= 3:
                chapter_index = int(parts[2])
                state_info.append({
                    "file": filename,
                    "chapter_index": chapter_index,
                    "path": state_file
                })
        
        # 按章节编号排序
        state_info.sort(key=lambda x: x["chapter_index"])
        
        return jsonify({
            "novel_id": novel_id,
            "states": state_info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/novels/<novel_id>/latest-state', methods=['GET'])
def get_latest_state(novel_id):
    """获取指定小说的最新状态"""
    try:
        state = generator.state_manager.load_latest_state(novel_id)
        if state:
            return jsonify({
                "novel_id": novel_id,
                "state": state.model_dump(),
                "found": True
            })
        else:
            return jsonify({
                "novel_id": novel_id,
                "state": None,
                "found": False
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-result', methods=['POST'])
def save_result():
    """保存生成结果"""
    try:
        data = request.json
        
        if 'content' not in data:
            return jsonify({"error": "缺少内容"}), 400
        
        content = data['content']
        novel_id = data.get('novel_id')  # 获取小说ID
        
        # 生成文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if novel_id:
            filename = f"{novel_id}_novel_{timestamp}.txt"
        else:
            filename = f"novel_{timestamp}.txt"
        
        file_path = os.path.join(XIAOSHUO_DIR, filename)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            "message": "保存成功",
            "filename": filename,
            "file_path": file_path,
            "novel_id": novel_id,
            "word_count": len(content)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/novels/<novel_id>/info', methods=['GET'])
def get_novel_info(novel_id):
    """获取指定小说的完整信息"""
    try:
        import glob
        import re
        
        # 1. 获取状态信息
        state = generator.state_manager.load_latest_state(novel_id)
        state_info = {
            "found": state is not None,
            "latest_chapter": state.chapter_index if state else 0,
            "protagonist": state.protagonist.name if state else "未知",
            "level": state.protagonist.level if state else "未知",
            "plot_summary": state.current_plot_summary if state else ""
        }
        
        # 2. 检查章节文件
        chapter_files = glob.glob(os.path.join(XIAOSHUO_DIR, f"{novel_id}_chapter_*.txt"))
        chapter_numbers = []
        for file_path in chapter_files:
            filename = os.path.basename(file_path)
            # 提取章节编号: novel_id_chapter_XXX.txt
            match = re.search(r'_chapter_(\d+)\.txt$', filename)
            if match:
                chapter_numbers.append(int(match.group(1)))
        
        chapter_numbers.sort()
        chapter_info = {
            "total_chapters": len(chapter_numbers),
            "chapter_list": chapter_numbers,
            "latest_chapter_file": max(chapter_numbers) if chapter_numbers else 0
        }
        
        # 3. 获取记忆统计
        try:
            memory_stats = generator.get_memory_stats(novel_id)
            memory_info = {
                "total_messages": memory_stats.get("total_messages", 0),
                "total_chunks": memory_stats.get("total_chunks", 0),
                "compressed_chunks": memory_stats.get("compressed_chunks", 0)
            }
        except:
            memory_info = {
                "total_messages": 0,
                "total_chunks": 0,
                "compressed_chunks": 0
            }
        
        # 4. 检查世界设定文件
        world_bible = generator.state_manager.load_world_bible(novel_id)
        world_info = {
            "has_world_bible": bool(world_bible),
            "world_setting": world_bible.get("setting", "") if world_bible else ""
        }
        
        # 5. 检查版本文件
        version_files = glob.glob(os.path.join("./versions", f"{novel_id}_chapter_*_versions.json"))
        version_info = {
            "has_versions": len(version_files) > 0,
            "version_chapters": len(version_files)
        }
        
        return jsonify({
            "novel_id": novel_id,
            "state": state_info,
            "chapters": chapter_info,
            "memory": memory_info,
            "world": world_info,
            "versions": version_info,
            "summary": {
                "state_chapter": state_info["latest_chapter"],
                "file_chapter": chapter_info["latest_chapter_file"],
                "sync_status": "同步" if state_info["latest_chapter"] == chapter_info["latest_chapter_file"] else "不同步"
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/read-outline', methods=['POST'])
def read_outline():
    """读取章节细纲"""
    try:
        data = request.json
        novel_id = data.get('novel_id')
        chapter_index = data.get('chapter_index')
        
        if not novel_id or not chapter_index:
            return jsonify({"error": "缺少必需参数"}), 400
        
        # 构建细纲文件路径
        outline_dir = os.path.join("xiaoshuo", "zhangjiexigang", str(novel_id))
        outline_file = os.path.join(outline_dir, f"{chapter_index}.txt")
        
        # 检查文件是否存在
        if not os.path.exists(outline_file):
            return jsonify({
                "error": f"细纲文件不存在: {outline_file}",
                "outline": None
            }), 404
        
        # 读取细纲文件
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_content = f.read().strip()
        
        if not outline_content:
            return jsonify({
                "error": "细纲文件为空",
                "outline": None
            }), 400
        
        return jsonify({
            "outline": outline_content,
            "file_path": outline_file,
            "chapter_index": chapter_index,
            "novel_id": novel_id
        })
        
    except Exception as e:
        print(f"读取细纲失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/save-chapter", methods=["POST"])
def save_chapter():
    """保存章节到文件"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        novel_id = data.get('novel_id', '')
        chapter_index = data.get('chapter_index', 1)
        auto_save = data.get('auto_save', False)
        
        if not content:
            return jsonify({"error": "章节内容不能为空"}), 400
        
        # 确保xiaoshuo目录存在
        os.makedirs("./xiaoshuo", exist_ok=True)
        
        # 生成文件名
        if novel_id:
            filename = f"{novel_id}_chapter_{chapter_index:03d}.txt"
        else:
            filename = f"chapter_{chapter_index:03d}.txt"
        
        file_path = f"./xiaoshuo/{filename}"
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "word_count": len(content),
            "auto_save": auto_save
        })
        
    except Exception as e:
        print(f"保存章节失败: {e}")
        return jsonify({"error": f"保存章节失败: {str(e)}"}), 500

@app.route("/api/update-state", methods=["POST"])
def update_state():
    """手动更新角色设定"""
    try:
        data = request.get_json()
        novel_id = data.get('novel_id')
        chapter_index = data.get('chapter_index')
        model_name = data.get('model_name')
        force_update = data.get('force_update', False)
        
        if not novel_id:
            return jsonify({"error": "缺少小说ID"}), 400
        
        if not chapter_index:
            return jsonify({"error": "缺少章节编号"}), 400
        
        # 读取章节内容
        chapter_filename = f"{novel_id}_chapter_{chapter_index:03d}.txt"
        chapter_path = os.path.join("./xiaoshuo", chapter_filename)
        
        if not os.path.exists(chapter_path):
            return jsonify({"error": f"章节文件不存在: {chapter_filename}"}), 404
        
        with open(chapter_path, 'r', encoding='utf-8') as f:
            chapter_content = f.read()
        
        # 加载当前状态
        current_state = generator.state_manager.load_latest_state(novel_id)
        if not current_state:
            return jsonify({"error": "找不到当前角色状态"}), 404
        
        # 使用生成器直接更新状态
        updated_state = generator.update_state(
            chapter_content=chapter_content,
            current_state=current_state,
            model_name=model_name or generator.model_name,
            novel_id=novel_id
        )
        
        return jsonify({
            "success": True,
            "novel_id": novel_id,
            "chapter_index": chapter_index,
            "summary": f"基于第{chapter_index}章内容更新了角色设定",
            "updated_fields": ["protagonist", "characters", "current_plot_summary"],
            "model_used": model_name or generator.model_name
        })
        
    except Exception as e:
        print(f"手动更新状态失败: {e}")
        return jsonify({"error": f"状态更新失败: {str(e)}"}), 500

# ===== 设定管理API =====
@app.route("/api/settings/<novel_id>", methods=["GET"])
def get_settings_list(novel_id):
    """获取指定小说的设定文件列表"""
    try:
        import os
        import re
        
        data_path = "./data"
        if not os.path.exists(data_path):
            return jsonify({
                "character_versions": [],
                "world_versions": []
            })
        
        character_versions = []
        world_versions = []
        
        # 扫描data目录中的文件
        for filename in os.listdir(data_path):
            # 匹配人物设定文件: {novel_id}_chapter_{version}_state.json
            character_match = re.match(rf'{re.escape(novel_id)}_chapter_(\d+)_state\.json', filename)
            if character_match:
                version = int(character_match.group(1))
                character_versions.append({
                    "version": version,
                    "filename": filename
                })
            
            # 匹配世界设定文件: {novel_id}_world_bible_{version}.json
            world_match = re.match(rf'{re.escape(novel_id)}_world_bible_(\d+)\.json', filename)
            if world_match:
                version = int(world_match.group(1))
                world_versions.append({
                    "version": version,
                    "filename": filename
                })
        
        # 按版本号排序
        character_versions.sort(key=lambda x: x['version'])
        world_versions.sort(key=lambda x: x['version'])
        
        return jsonify({
            "character_versions": character_versions,
            "world_versions": world_versions
        })
        
    except Exception as e:
        print(f"获取设定列表失败: {e}")
        return jsonify({"error": f"获取设定列表失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/character/<version>", methods=["GET"])
def get_character_settings(novel_id, version):
    """获取指定版本的人物设定"""
    try:
        import os
        import json
        
        # 构建文件路径
        filename = f"{novel_id}_chapter_{version}_state.json"
        file_path = os.path.join("./data", filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "人物设定文件不存在"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        return jsonify({
            "content": content,
            "filename": filename,
            "version": version
        })
        
    except Exception as e:
        print(f"获取人物设定失败: {e}")
        return jsonify({"error": f"获取人物设定失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/world/<version>", methods=["GET"])
def get_world_settings(novel_id, version):
    """获取指定版本的世界设定"""
    try:
        import os
        import json
        
        # 构建文件路径
        filename = f"{novel_id}_world_bible_{version}.json"
        file_path = os.path.join("./data", filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "世界设定文件不存在"}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        return jsonify({
            "content": content,
            "filename": filename,
            "version": version
        })
        
    except Exception as e:
        print(f"获取世界设定失败: {e}")
        return jsonify({"error": f"获取世界设定失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/character/<version>", methods=["PUT"])
def save_character_settings(novel_id, version):
    """保存人物设定"""
    try:
        import os
        import json
        
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "设定内容不能为空"}), 400
        
        # 确保data目录存在
        os.makedirs("./data", exist_ok=True)
        
        # 构建文件路径
        filename = f"{novel_id}_chapter_{version}_state.json"
        file_path = os.path.join("./data", filename)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "version": version
        })
        
    except Exception as e:
        print(f"保存人物设定失败: {e}")
        return jsonify({"error": f"保存人物设定失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/world/<version>", methods=["PUT"])
def save_world_settings(novel_id, version):
    """保存世界设定"""
    try:
        import os
        import json
        
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "设定内容不能为空"}), 400
        
        # 确保data目录存在
        os.makedirs("./data", exist_ok=True)
        
        # 构建文件路径
        filename = f"{novel_id}_world_bible_{version}.json"
        file_path = os.path.join("./data", filename)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "version": version
        })
        
    except Exception as e:
        print(f"保存世界设定失败: {e}")
        return jsonify({"error": f"保存世界设定失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/character/new", methods=["POST"])
def create_new_character_version(novel_id):
    """创建新的人物设定版本"""
    try:
        import os
        import json
        import re
        
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "设定内容不能为空"}), 400
        
        # 扫描现有版本，找到最大版本号
        data_path = "./data"
        max_version = -1
        
        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                match = re.match(rf'{re.escape(novel_id)}_chapter_(\d+)_state\.json', filename)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)
        
        # 新版本号
        new_version = max_version + 1
        new_version_str = str(new_version).zfill(3)
        
        # 确保data目录存在
        os.makedirs(data_path, exist_ok=True)
        
        # 构建新文件路径
        filename = f"{novel_id}_chapter_{new_version_str}_state.json"
        file_path = os.path.join(data_path, filename)
        
        # 保存新版本
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "new_version": new_version_str,
            "filename": filename
        })
        
    except Exception as e:
        print(f"创建新人物设定版本失败: {e}")
        return jsonify({"error": f"创建新版本失败: {str(e)}"}), 500

@app.route("/api/settings/<novel_id>/world/new", methods=["POST"])
def create_new_world_version(novel_id):
    """创建新的世界设定版本"""
    try:
        import os
        import json
        import re
        
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "设定内容不能为空"}), 400
        
        # 扫描现有版本，找到最大版本号
        data_path = "./data"
        max_version = -1
        
        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                match = re.match(rf'{re.escape(novel_id)}_world_bible_(\d+)\.json', filename)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)
        
        # 新版本号
        new_version = max_version + 1
        new_version_str = str(new_version).zfill(2)
        
        # 确保data目录存在
        os.makedirs(data_path, exist_ok=True)
        
        # 构建新文件路径
        filename = f"{novel_id}_world_bible_{new_version_str}.json"
        file_path = os.path.join(data_path, filename)
        
        # 保存新版本
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "new_version": new_version_str,
            "filename": filename
        })
        
    except Exception as e:
        print(f"创建新世界设定版本失败: {e}")
        return jsonify({"error": f"创建新版本失败: {str(e)}"}), 500

# ===== 错误处理 =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "接口不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500

# ===== 启动服务器 =====
if __name__ == '__main__':
    print("🎭 小说生成系统 Web服务器启动中...")
    print(f"📁 模版目录: {os.path.abspath(TEMPLATES_DIR)}")
    print(f"🌐 Web目录: {os.path.abspath(WEB_DIR)}")
    print(f"📚 小说输出目录: {os.path.abspath(XIAOSHUO_DIR)}")
    print("🚀 服务器地址: http://localhost:5000")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    ) 