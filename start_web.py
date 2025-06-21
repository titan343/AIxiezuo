#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说生成系统 - Web服务启动脚本
"""

import os
import sys
import subprocess
import json

def check_dependencies():
    """检查依赖包"""
    required_packages = ['flask', 'flask-cors']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 请运行以下命令安装:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def init_templates():
    """初始化模版目录"""
    templates_dir = "./templates"
    prompts_dir = "./prompts"
    
    os.makedirs(templates_dir, exist_ok=True)
    
    # 检查是否有现有的模版索引
    index_file = os.path.join(templates_dir, "template_index.json")
    if os.path.exists(index_file):
        print("✅ 模版索引文件已存在")
        return
    
    # 创建默认模版索引
    default_index = {
        "version": "1.0",
        "description": "小说生成系统提示词模板索引",
        "last_updated": "2024-01-15",
        "templates": {},
        "naming_convention": {
            "pattern": "{ID}_{type}.txt",
            "types": [
                "writer_role",
                "writing_rules", 
                "update_state_rules"
            ],
            "description": "ID为3位数字，type为功能类型"
        },
        "usage_guide": {
            "step1": "根据ID从索引中获取模板信息",
            "step2": "读取对应的三个提示词文件",
            "step3": "组合提示词内容传递给AI",
            "example_id": "001"
        }
    }
    
    # 如果存在prompts目录，创建001默认模版
    if os.path.exists(prompts_dir):
        print("📝 从prompts目录创建默认模版...")
        
        # 复制文件到templates目录
        prompts_files = {
            "writer_role.txt": "001_writer_role.txt",
            "writing_rules.txt": "001_writing_rules.txt", 
            "update_state_rules.txt": "001_update_state_rules.txt"
        }
        
        template_created = True
        for src_file, dst_file in prompts_files.items():
            src_path = os.path.join(prompts_dir, src_file)
            dst_path = os.path.join(templates_dir, dst_file)
            
            if os.path.exists(src_path):
                try:
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(dst_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"   ✅ {src_file} -> {dst_file}")
                except Exception as e:
                    print(f"   ❌ 复制失败 {src_file}: {e}")
                    template_created = False
            else:
                print(f"   ⚠️  源文件不存在: {src_file}")
                template_created = False
        
        if template_created:
            # 添加默认模版到索引
            default_index["templates"]["001"] = {
                "id": "001",
                "name": "默认小说模板",
                "category": "通用",
                "description": "从prompts目录自动创建的默认模板",
                "author": "系统默认",
                "created_date": "2024-01-15",
                "files": {
                    "writer_role": "001_writer_role.txt",
                    "writing_rules": "001_writing_rules.txt",
                    "update_state_rules": "001_update_state_rules.txt"
                },
                "features": [
                    "通用写作",
                    "基础规则",
                    "状态管理"
                ],
                "word_count_range": {
                    "min": 2200,
                    "max": 3000
                }
            }
    
    # 保存索引文件
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(default_index, f, indent=2, ensure_ascii=False)
    
    print("✅ 模版索引文件已创建")

def check_environment():
    """检查环境配置"""
    env_file = ".env"
    if not os.path.exists(env_file):
        print("⚠️  .env文件不存在，请确保已配置API密钥")
        print("   需要配置的环境变量:")
        print("   - DEEPSEEK_API_KEY")
        print("   - DSF5_API_KEY (可选)")
        print("   - OPENAI_API_KEY (可选)")
        return False
    
    print("✅ 环境配置文件存在")
    return True

def main():
    """主函数"""
    print("🎭 小说生成系统 - Web服务启动")
    print("=" * 50)
    
    # 检查依赖
    print("🔍 检查依赖包...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ 依赖包检查通过")
    
    # 检查环境
    print("\n🔍 检查环境配置...")
    env_ok = check_environment()
    
    # 初始化模版
    print("\n📝 初始化模版目录...")
    init_templates()
    
    # 启动服务器
    print("\n🚀 启动Web服务器...")
    if not env_ok:
        print("⚠️  环境配置可能不完整，但仍将启动服务器")
    
    print("🌐 访问地址: http://localhost:5001")
    print("📖 功能说明:")
    print("   - 模版管理: 创建、编辑、预览提示词模版")
    print("   - 小说生成: 基于模版和参数生成小说章节")
    print("   - 助手对话: 简单的AI对话功能")
    print("=" * 50)
    
    try:
        # 导入并启动web服务器
        from web_server import app
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,  # 生产模式
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 