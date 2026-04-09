# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - 配置管理
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置"""

    # API配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-d5ba0eb534ec411cb5ec388f87fbd78c")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen-plus")
    MODEL_TEMPERATURE: float = 0.1

    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")

    # 应用配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8501"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # 文件路径
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")

    # 分析配置
    MAX_QUERY_ROWS: int = 10000
    QUERY_TIMEOUT: int = 30
    ENABLE_CACHE: bool = True

    def __init__(self):
        """确保输出目录存在"""
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"


settings = Settings()
