#!/usr/bin/env python3
"""
PPT AI 应用启动脚本
"""

import uvicorn
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """主入口函数"""
    config = {
        "app": "src.main:app",
        "host": "0.0.0.0",
        "port": 8001,
        "reload": False,
        "log_level": "info",
        "access_log": True
    }

    print("=" * 60)
    print("PPT AI - 智能PPT生成器")
    print("=" * 60)
    print(f"服务器地址: http://localhost:{config['port']}")
    print(f"Web界面: http://localhost:{config['port']}")
    print("=" * 60)
    print("\n按 Ctrl+C 停止服务器\n")

    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
