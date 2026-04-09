# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - Excel工具
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import traceback

from models.schemas import TableSchema, ColumnInfo, DataSourceType, DataType, QueryResult
from config.settings import settings


class ExcelTool:
    """Excel处理工具"""

    def __init__(self):
        self.loaded_files: Dict[str, pd.DataFrame] = {}
        self.file_schemas: Dict[str, TableSchema] = {}

    def load_excel(
        self,
        file_path: str,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载Excel文件

        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称（默认第一个）

        Returns:
            加载结果
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            # 读取Excel
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names

            if sheet_name is None:
                sheet_name = sheet_names[0]
            elif sheet_name not in sheet_names:
                return {
                    "success": False,
                    "error": f"工作表 '{sheet_name}' 不存在，可用的工作表: {sheet_names}"
                }

            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # 存储数据
            file_key = f"{path.name}_{sheet_name}"
            self.loaded_files[file_key] = df

            # 分析结构
            schema = self._analyze_schema(df, path.name, sheet_name)
            self.file_schemas[file_key] = schema

            return {
                "success": True,
                "file_key": file_key,
                "schema": schema.to_dict(),
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns.tolist())
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"加载失败: {str(e)}"
            }

    def _analyze_schema(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_name: str
    ) -> TableSchema:
        """分析表结构"""
        columns = []

        for col_name in df.columns:
            series = df[col_name]
            data_type = self._detect_data_type(series)
            nullable = series.isna().any()
            sample_values = series.dropna().head(5).tolist()

            columns.append(ColumnInfo(
                name=str(col_name),
                data_type=data_type,
                nullable=nullable,
                sample_values=sample_values,
                description=f"{data_type.value}类型，{'可空' if nullable else '非空'}"
            ))

        return TableSchema(
            name=f"{filename}_{sheet_name}",
            source_type=DataSourceType.EXCEL,
            columns=columns,
            row_count=len(df),
            description=f"Excel文件 {filename} 的工作表 {sheet_name}"
        )

    def _detect_data_type(self, series: pd.Series) -> DataType:
        """检测数据类型"""
        # 尝试转换为数值
        try:
            pd.to_numeric(series, errors='raise')
            if series.dtype in ['int64', 'int32']:
                return DataType.INTEGER
            return DataType.FLOAT
        except:
            pass

        # 尝试转换为日期
        try:
            pd.to_datetime(series, errors='raise')
            return DataType.DATETIME
        except:
            pass

        # 检测布尔类型
        if series.dtype == 'bool':
            return DataType.BOOLEAN

        # 默认字符串
        return DataType.STRING

    def query_excel(
        self,
        file_key: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> QueryResult:
        """
        查询Excel数据

        Args:
            file_key: 文件键名
            filters: 过滤条件
            columns: 指定列
            limit: 限制行数
            sort_by: 排序字段
            sort_desc: 是否降序

        Returns:
            查询结果
        """
        import time
        start = time.time()

        try:
            if file_key not in self.loaded_files:
                return QueryResult(
                    success=False,
                    message=f"文件未加载: {file_key}",
                    error="File not loaded"
                )

            df = self.loaded_files[file_key].copy()

            # 应用过滤
            if filters:
                for col, value in filters.items():
                    if col in df.columns:
                        if isinstance(value, dict):
                            # 支持比较操作
                            op = value.get("op", "==")
                            val = value.get("value")
                            if op == ">":
                                df = df[df[col] > val]
                            elif op == "<":
                                df = df[df[col] < val]
                            elif op == ">=":
                                df = df[df[col] >= val]
                            elif op == "<=":
                                df = df[df[col] <= val]
                            elif op == "!=":
                                df = df[df[col] != val]
                            elif op == "contains":
                                df = df[df[col].astype(str).str.contains(val, na=False)]
                            else:
                                df = df[df[col] == val]
                        else:
                            df = df[df[col] == value]

            # 选择列
            if columns:
                available_cols = [c for c in columns if c in df.columns]
                if available_cols:
                    df = df[available_cols]

            # 排序
            if sort_by and sort_by in df.columns:
                df = df.sort_values(sort_by, ascending=not sort_desc)

            # 限制
            if limit:
                df = df.head(limit)

            execution_time = time.time() - start

            return QueryResult(
                success=True,
                data=df.to_dict(orient="records"),
                row_count=len(df),
                execution_time=execution_time,
                sql=f"Query Excel {file_key}",
                message=f"查询成功，返回 {len(df)} 行"
            )

        except Exception as e:
            return QueryResult(
                success=False,
                message="查询失败",
                error=str(e),
                execution_time=time.time() - start
            )

    def analyze_excel(self, file_key: str) -> Dict[str, Any]:
        """
        分析Excel数据

        Args:
            file_key: 文件键名

        Returns:
            分析结果
        """
        try:
            if file_key not in self.loaded_files:
                return {"error": "文件未加载"}

            df = self.loaded_files[file_key]

            analysis = {
                "basic_info": {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns.tolist()),
                    "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
                },
                "data_types": df.dtypes.astype(str).to_dict(),
                "null_counts": df.isna().sum().to_dict(),
                "duplicate_rows": int(df.duplicated().sum()),
                "numeric_stats": {}
            }

            # 数值统计
            for col in df.select_dtypes(include=['number']).columns:
                analysis["numeric_stats"][col] = {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "median": float(df[col].median())
                }

            return analysis

        except Exception as e:
            return {"error": str(e)}

    def get_schema(self, file_key: str) -> Optional[TableSchema]:
        """获取表结构"""
        return self.file_schemas.get(file_key)

    def list_loaded_files(self) -> List[str]:
        """列出已加载的文件"""
        return list(self.loaded_files.keys())


# 全局实例
excel_tool = ExcelTool()
