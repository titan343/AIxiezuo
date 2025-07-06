#!/usr/bin/env python3
"""
测试Web界面功能
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def main():
    print("🧪 测试Web界面...")
    
    # 确保在正确的目录中
    script_dir = Path(__file__).parent
    web_server_path = script_dir / "web_server.py"
    
    if not web_server_path.exists():
        print("❌ 错误: 找不到 web_server.py 文件")
        return
    
    try:
        # 启动Web服务器
        print("🚀 启动Web服务器...")
        process = subprocess.Popen(
            [sys.executable, str(web_server_path)],
            cwd=str(script_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        time.sleep(3)
        
        # 检查服务器是否正在运行
        if process.poll() is None:
            print("✅ Web服务器已启动")
            print("🌐 打开浏览器访问 http://localhost:5000")
            webbrowser.open("http://localhost:5000")
            
            # 等待用户操作
            input("请在浏览器中测试功能，完成后按回车键停止服务器...")
            
        else:
            stdout, stderr = process.communicate()
            print(f"❌ 服务器启动失败")
            print(f"输出: {stdout}")
            print(f"错误: {stderr}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        # 确保终止进程
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
                print("🛑 服务器已停止")
            except:
                process.kill()
                print("🛑 服务器已强制停止")

if __name__ == "__main__":
    main()