# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - 数据模型
"""
from typing import List, Dict, Any, Optional, Union, Annotated, TypedDict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import operator


class DataSourceType(str, Enum):
    """数据源类型"""
    EXCEL = "excel"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class DataType(str, Enum):
    """数据类型"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UNKNOWN = "unknown"


class QueryType(str, Enum):
    """查询类型"""
    SELECT = "select"
    AGGREGATE = "aggregate"
    FILTER = "filter"
    GROUP = "group"
    SORT = "sort"
    JOIN = "join"
    TREND = "trend"
    TOP_N = "top_n"


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: DataType
    nullable: bool = True
    sample_values: List[Any] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type.value,
            "nullable": self.nullable,
            "sample_values": self.sample_values[:5],
            "description": self.description
        }


@dataclass
class TableSchema:
    """表结构"""
    name: str
    source_type: DataSourceType
    columns: List[ColumnInfo]
    row_count: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "row_count": self.row_count,
            "columns": [col.to_dict() for col in self.columns],
            "description": self.description
        }


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time: float = 0.0
    sql: str = ""
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "row_count": self.row_count,
            "execution_time": self.execution_time,
            "sql": self.sql,
            "message": self.message,
            "error": self.error,
            "preview": self.data[:10] if self.data else []
        }


@dataclass
class AnalysisRequest:
    """分析请求"""
    query: str
    source: Optional[str] = None  # 数据源名称
    query_type: Optional[QueryType] = None
    limit: int = 100
    use_cache: bool = True


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: str  # bar, line, pie, scatter
    x_column: str
    y_columns: List[str]
    title: str = ""
    group_by: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


class AgentState(TypedDict):
    """Agent状态 - LangGraph 兼容"""
    messages: Annotated[List[Dict[str, Any]], operator.add]
    current_query: str
    detected_intent: Optional[str]
    generated_sql: str
    query_result: Optional[QueryResult]
    error_count: int
    data_sources: Dict[str, TableSchema]
