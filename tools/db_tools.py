# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - 数据库工具
"""
import time
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from models.schemas import TableSchema, ColumnInfo, DataSourceType, DataType, QueryResult
from config.settings import settings


class DatabaseTool:
    """数据库处理工具"""

    def __init__(self):
        self.engine: Optional[Engine] = None
        self.schema_cache: Dict[str, TableSchema] = {}

    def connect(self) -> Dict[str, Any]:
        """连接数据库"""
        try:
            if self.engine is None:
                self.engine = create_engine(
                    settings.database_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=3600
                )

            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return {
                "success": True,
                "message": "数据库连接成功",
                "database": settings.DB_NAME,
                "host": settings.DB_HOST
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"连接失败: {str(e)}"
            }

    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def list_tables(self) -> List[str]:
        """列出所有表"""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            print(f"获取表列表失败: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Optional[TableSchema]:
        """
        获取表结构

        Args:
            table_name: 表名

        Returns:
            表结构
        """
        # 检查缓存
        if table_name in self.schema_cache:
            return self.schema_cache[table_name]

        try:
            inspector = inspect(self.engine)

            # 获取列信息
            columns = []
            for column in inspector.get_columns(table_name):
                col_info = ColumnInfo(
                    name=column['name'],
                    data_type=self._map_sql_type(column['type']),
                    nullable=column.get('nullable', True),
                    description=column.get('comment', '')
                )
                columns.append(col_info)

            # 获取行数
            row_count = 0
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                    row_count = result.scalar()
            except:
                pass

            schema = TableSchema(
                name=table_name,
                source_type=DataSourceType.MYSQL,
                columns=columns,
                row_count=row_count,
                description=f"MySQL表 {table_name}"
            )

            # 缓存
            self.schema_cache[table_name] = schema
            return schema

        except Exception as e:
            print(f"获取表结构失败: {e}")
            return None

    def _map_sql_type(self, sql_type) -> DataType:
        """映射SQL类型到DataType"""
        type_str = str(sql_type).lower()

        if 'int' in type_str:
            return DataType.INTEGER
        elif 'float' in type_str or 'double' in type_str or 'decimal' in type_str:
            return DataType.FLOAT
        elif 'char' in type_str or 'text' in type_str:
            return DataType.STRING
        elif 'bool' in type_str:
            return DataType.BOOLEAN
        elif 'date' in type_str:
            return DataType.DATETIME
        else:
            return DataType.UNKNOWN

    def execute_query(
        self,
        sql: str,
        limit: int = 1000
    ) -> QueryResult:
        """
        执行SQL查询

        Args:
            sql: SQL语句
            limit: 限制行数

        Returns:
            查询结果
        """
        start = time.time()

        try:
            # 安全检查
            sql_upper = sql.upper().strip()
            dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
            if any(kw in sql_upper for kw in dangerous_keywords):
                return QueryResult(
                    success=False,
                    message="不安全的SQL语句",
                    error="Dangerous SQL detected",
                    sql=sql
                )

            # 添加LIMIT
            if 'LIMIT' not in sql_upper:
                sql = f"{sql} LIMIT {limit}"

            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                columns = list(result.keys())

                data = [dict(zip(columns, row)) for row in rows]

            execution_time = time.time() - start

            return QueryResult(
                success=True,
                data=data,
                row_count=len(data),
                execution_time=execution_time,
                sql=sql,
                message=f"查询成功，返回 {len(data)} 行"
            )

        except Exception as e:
            return QueryResult(
                success=False,
                message="查询执行失败",
                error=str(e),
                sql=sql,
                execution_time=time.time() - start
            )

    def validate_sql(self, sql: str, schema: TableSchema) -> Dict[str, Any]:
        """
        验证SQL语句

        Args:
            sql: SQL语句
            schema: 表结构

        Returns:
            验证结果
        """
        try:
            column_names = {col.name for col in schema.columns}
            table_name = schema.name

            # 基本语法检查
            if not sql.strip():
                return {"valid": False, "error": "SQL为空"}

            sql_upper = sql.upper()

            # 检查表名
            if table_name.upper() not in sql_upper:
                return {"valid": False, "error": f"未找到表名 {table_name}"}

            # 检查列名
            # 提取SELECT后的列名
            if 'SELECT' in sql_upper:
                select_part = sql_upper.split('FROM')[0].replace('SELECT', '').strip()
                if select_part != '*':
                    for col in select_part.split(','):
                        col = col.strip()
                        if col and col not in column_names and not any(
                            kw in col for kw in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'DISTINCT']
                        ):
                            return {"valid": False, "error": f"未知列: {col}"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()

            return {
                "database": settings.DB_NAME,
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "table_count": len(tables),
                "tables": tables
            }

        except Exception as e:
            return {"error": str(e)}


# 全局实例
db_tool = DatabaseTool()
