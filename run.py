# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - 启动脚本
"""
import sys
import os

# 确保在正确的目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit.web.cli as stcli


def main():
    """启动Streamlit应用"""
    sys.argv = [
        "streamlit",
        "run",
        "ui/app.py",
        f"--server.port={os.getenv('PORT', 8501)}",
        f"--server.address={os.getenv('HOST', '0.0.0.0')}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]

    stcli.main()


if __name__ == "__main__":
    main()
