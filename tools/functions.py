# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - Function Calling 工具定义
"""
from typing import Dict, Any
import pandas as pd

from tools.excel_tools import excel_tool
from tools.db_tools import db_tool


# ==================== Excel 工具 ====================

def load_excel_file(file_path: str, sheet_name: str = "") -> Dict[str, Any]:
    """
    加载Excel文件

    Args:
        file_path: Excel文件路径
        sheet_name: 工作表名称（可选，默认加载第一个）

    Returns:
        加载结果，包含schema信息
    """
    return excel_tool.load_excel(file_path, sheet_name or None)


def query_excel_data(
    file_key: str,
    filters: Dict[str, Any] = None,
    columns: list = None,
    limit: int = 100,
    sort_by: str = "",
    sort_desc: bool = False
) -> Dict[str, Any]:
    """
    查询Excel数据

    Args:
        file_key: 文件键名（load_excel_file返回的file_key）
        filters: 过滤条件，格式: {"列名": 值} 或 {"列名": {"op": ">", "value": 数值}}
        columns: 要返回的列名列表
        limit: 限制返回行数
        sort_by: 排序字段
        sort_desc: 是否降序排序

    Returns:
        查询结果数据
    """
    result = excel_tool.query_excel(
        file_key=file_key,
        filters=filters,
        columns=columns,
        limit=limit,
        sort_by=sort_by or None,
        sort_desc=sort_desc
    )
    return result.to_dict()


def analyze_excel_data(file_key: str) -> Dict[str, Any]:
    """
    分析Excel数据

    Args:
        file_key: 文件键名

    Returns:
        数据分析结果，包含统计信息、空值检测、重复值检测
    """
    return excel_tool.analyze_excel(file_key)


def list_excel_files() -> Dict[str, Any]:
    """
    列出已加载的Excel文件

    Returns:
        文件列表
    """
    files = excel_tool.list_loaded_files()
    return {
        "files": files,
        "count": len(files)
    }


def get_excel_schema(file_key: str) -> Dict[str, Any]:
    """
    获取Excel表结构

    Args:
        file_key: 文件键名

    Returns:
        表结构信息
    """
    schema = excel_tool.get_schema(file_key)
    if schema:
        return schema.to_dict()
    return {"error": "文件未找到"}


# ==================== 数据库工具 ====================

def connect_database() -> Dict[str, Any]:
    """
    连接MySQL数据库

    Returns:
        连接结果
    """
    return db_tool.connect()


def list_database_tables() -> Dict[str, Any]:
    """
    列出数据库所有表

    Returns:
        表名列表
    """
    tables = db_tool.list_tables()
    return {
        "tables": tables,
        "count": len(tables)
    }


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    获取数据库表结构

    Args:
        table_name: 表名

    Returns:
        表结构信息，包含列名、数据类型等
    """
    schema = db_tool.get_table_schema(table_name)
    if schema:
        return schema.to_dict()
    return {"error": "表不存在"}


def execute_sql_query(sql: str, limit: int = 1000) -> Dict[str, Any]:
    """
    执行SQL查询

    Args:
        sql: SQL查询语句（只支持SELECT）
        limit: 限制返回行数

    Returns:
        查询结果数据
    """
    result = db_tool.execute_query(sql, limit)
    return result.to_dict()


def get_database_info() -> Dict[str, Any]:
    """
    获取数据库信息

    Returns:
        数据库名、主机、表数量等信息
    """
    return db_tool.get_database_info()


# ==================== 统计分析工具 ====================

def calculate_statistics(
    data: list,
    columns: list = None
) -> Dict[str, Any]:
    """
    计算统计数据

    Args:
        data: 数据列表
        columns: 要统计的列名

    Returns:
        统计结果（均值、中位数、标准差等）
    """
    if not data:
        return {"error": "数据为空"}

    df = pd.DataFrame(data)

    if columns:
        available_cols = [c for c in columns if c in df.columns]
        if available_cols:
            df = df[available_cols]

    stats = {}
    for col in df.select_dtypes(include=['number']).columns:
        series = df[col].dropna()
        stats[col] = {
            "count": len(series),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "q25": float(series.quantile(0.25)),
            "q75": float(series.quantile(0.75))
        }

    return stats


def aggregate_data(
    data: list,
    group_by: str,
    aggregations: Dict[str, str]
) -> Dict[str, Any]:
    """
    数据分组聚合

    Args:
        data: 数据列表
        group_by: 分组字段
        aggregations: 聚合配置，如: {"销售额": "sum", "数量": "avg"}

    Returns:
        聚合结果
    """
    if not data:
        return {"error": "数据为空"}

    df = pd.DataFrame(data)

    agg_mapping = {
        "sum": "sum",
        "avg": "mean",
        "mean": "mean",
        "count": "count",
        "max": "max",
        "min": "min",
        "median": "median"
    }

    agg_dict = {}
    for col, func in aggregations.items():
        if col in df.columns:
            pandas_func = agg_mapping.get(func.lower(), "mean")
            if col not in agg_dict:
                agg_dict[col] = []
            agg_dict[col].append(pandas_func)

    if group_by in df.columns and agg_dict:
        result = df.groupby(group_by).agg(agg_dict).reset_index()

        # 展平列名
        new_columns = [group_by]
        for col, funcs in agg_dict.items():
            for func in funcs:
                new_columns.append(f"{col}_{func}")
        result.columns = new_columns

        return result.to_dict(orient="records")

    return {"error": "分组或聚合失败"}


# ==================== 工具定义（供LLM调用）====================

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "load_excel_file",
            "description": "加载Excel文件，支持多Sheet读取",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel文件的完整路径"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "工作表名称（可选，默认加载第一个）"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_excel_data",
            "description": "查询Excel数据，支持过滤、排序、限制行数",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_key": {
                        "type": "string",
                        "description": "文件键名（load_excel_file返回）"
                    },
                    "filters": {
                        "type": "object",
                        "description": "过滤条件，如: {'价格': {'op': '>', 'value': 100}}"
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要返回的列名列表"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "限制返回行数"
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序字段"
                    },
                    "sort_desc": {
                        "type": "boolean",
                        "description": "是否降序"
                    }
                },
                "required": ["file_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_excel_data",
            "description": "分析Excel数据，返回统计信息、空值检测、重复值检测",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_key": {
                        "type": "string",
                        "description": "文件键名"
                    }
                },
                "required": ["file_key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "connect_database",
            "description": "连接MySQL数据库",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_database_tables",
            "description": "列出数据库所有表",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_schema",
            "description": "获取数据库表结构，包含列名、数据类型",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "执行SQL查询语句（只支持SELECT）",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL查询语句"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "限制返回行数"
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_statistics",
            "description": "计算数据的统计信息（均值、中位数、标准差等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "description": "数据列表"
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要统计的列名"
                    }
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_data",
            "description": "数据分组聚合（按字段分组后计算sum/avg/count等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "description": "数据列表"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组字段"
                    },
                    "aggregations": {
                        "type": "object",
                        "description": "聚合配置，如: {'销售额': 'sum', '数量': 'avg'}"
                    }
                },
                "required": ["data", "group_by", "aggregations"]
            }
        }
    }
]

# 工具映射
TOOLS_MAP = {
    "load_excel_file": load_excel_file,
    "query_excel_data": query_excel_data,
    "analyze_excel_data": analyze_excel_data,
    "connect_database": connect_database,
    "list_database_tables": list_database_tables,
    "get_table_schema": get_table_schema,
    "execute_sql_query": execute_sql_query,
    "calculate_statistics": calculate_statistics,
    "aggregate_data": aggregate_data,
}
