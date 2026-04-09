# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - Text-to-SQL模块
"""
from typing import Dict, Any, List, Optional
import json
import re

from models.schemas import TableSchema, ColumnInfo, QueryType
from config.settings import settings


class Text2SQLGenerator:
    """Text-to-SQL生成器"""

    def __init__(self):
        self.intent_patterns = {
            QueryType.SELECT: ["显示", "查看", "列出", "查询", "获取"],
            QueryType.AGGREGATE: ["总数", "总和", "平均", "最大", "最小", "汇总", "统计"],
            QueryType.FILTER: ["大于", "小于", "等于", "包含", "是", "不是"],
            QueryType.GROUP: ["按", "分组", "每个", "各", "各个"],
            QueryType.SORT: ["排序", "最高", "最低", "前", "后", "升序", "降序"],
            QueryType.TOP_N: ["前.*个", "top", "最多", "最少"],
            QueryType.TREND: ["趋势", "变化", "增长", "下降"]
        }

        self.agg_keywords = {
            "总数": "COUNT",
            "总和": "SUM",
            "平均": "AVG",
            "最大": "MAX",
            "最小": "MIN",
            "数量": "COUNT",
            "个数": "COUNT"
        }

    def parse_query(
        self,
        natural_query: str,
        schema: TableSchema
    ) -> Dict[str, Any]:
        """
        解析自然语言查询

        Args:
            natural_query: 自然语言查询
            schema: 表结构

        Returns:
            解析结果
        """
        result = {
            "query": natural_query,
            "intent": None,
            "columns": [],
            "filters": [],
            "group_by": None,
            "aggregations": [],
            "order_by": None,
            "order_desc": False,
            "limit": None
        }

        query_lower = natural_query.lower()

        # 1. 识别意图
        result["intent"] = self._detect_intent(query_lower)

        # 2. 提取列名
        result["columns"] = self._extract_columns(natural_query, schema)

        # 3. 提取聚合
        result["aggregations"] = self._extract_aggregations(natural_query, schema)

        # 4. 提取过滤条件
        result["filters"] = self._extract_filters(natural_query, schema)

        # 5. 提取分组
        result["group_by"] = self._extract_group_by(natural_query, schema)

        # 6. 提取排序
        result["order_by"], result["order_desc"] = self._extract_order(natural_query, schema)

        # 7. 提取限制
        result["limit"] = self._extract_limit(natural_query)

        return result

    def _detect_intent(self, query: str) -> QueryType:
        """检测查询意图"""
        scores = {}

        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for kw in keywords if kw in query)
            if score > 0:
                scores[intent] = score

        if scores:
            return max(scores.keys(), key=lambda k: scores[k])

        return QueryType.SELECT

    def _extract_columns(
        self,
        query: str,
        schema: TableSchema
    ) -> List[str]:
        """提取列名"""
        columns = []
        column_names = {col.name.lower(): col.name for col in schema.columns}

        # 直接匹配
        for col_name in column_names.values():
            if col_name in query:
                columns.append(col_name)

        # 别名匹配（中文转拼音等可扩展）
        return list(set(columns)) if columns else []

    def _extract_aggregations(
        self,
        query: str,
        schema: TableSchema
    ) -> List[Dict[str, str]]:
        """提取聚合函数"""
        aggregations = []

        for keyword, func in self.agg_keywords.items():
            if keyword in query:
                # 尝试找到对应的列
                for col in schema.columns:
                    if col.name in query or col.data_type.value in ["integer", "float"]:
                        aggregations.append({
                            "column": col.name,
                            "function": func
                        })
                        break

        return aggregations

    def _extract_filters(
        self,
        query: str,
        schema: TableSchema
    ) -> List[Dict[str, Any]]:
        """提取过滤条件"""
        filters = []

        # 数值比较: 大于、小于、等于
        patterns = [
            (r'(\w+)\s*[大于>]+\s*(\d+\.?\d*)', '>'),
            (r'(\w+)\s*[小于<]+\s*(\d+\.?\d*)', '<'),
            (r'(\w+)\s*[等于=]+\s*(\d+\.?\d*|[^\s,，。]+)', '='),
        ]

        for pattern, op in patterns:
            matches = re.finditer(pattern, query)
            for match in matches:
                col = match.group(1)
                val = match.group(2)

                # 匹配列名
                matched_col = self._match_column(col, schema)
                if matched_col:
                    filters.append({
                        "column": matched_col,
                        "operator": op,
                        "value": val
                    })

        return filters

    def _extract_group_by(
        self,
        query: str,
        schema: TableSchema
    ) -> Optional[str]:
        """提取分组字段"""
        patterns = [
            r'按(\w+)分组',
            r'按(\w+)[统计计算]',
            r'每个(\w+)',
            r'各(\w+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                col = match.group(1)
                return self._match_column(col, schema)

        return None

    def _extract_order(
        self,
        query: str,
        schema: TableSchema
    ) -> tuple:
        """提取排序"""
        order_desc = False
        order_col = None

        # 检测方向
        if any(kw in query for kw in ["降序", "从高到低", "最高", "最大"]):
            order_desc = True
        elif any(kw in query for kw in ["升序", "从低到高", "最低", "最小"]):
            order_desc = False

        # 检测列
        for col in schema.columns:
            if col.name in query:
                order_col = col.name
                break

        return order_col, order_desc

    def _extract_limit(self, query: str) -> Optional[int]:
        """提取限制数量"""
        patterns = [
            r'前(\d+)[个名条]',
            r'top\s*(\d+)',
            r'限制.*?(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return int(match.group(1))

        return None

    def _match_column(self, name: str, schema: TableSchema) -> Optional[str]:
        """匹配列名"""
        # 精确匹配
        for col in schema.columns:
            if col.name == name:
                return col.name

        # 模糊匹配
        name_lower = name.lower()
        for col in schema.columns:
            if name_lower in col.name.lower() or col.name.lower() in name_lower:
                return col.name

        return None

    def generate_sql(
        self,
        parsed_query: Dict[str, Any],
        schema: TableSchema
    ) -> str:
        """
        生成SQL语句

        Args:
            parsed_query: 解析后的查询
            schema: 表结构

        Returns:
            SQL语句
        """
        intent = parsed_query.get("intent", QueryType.SELECT)
        columns = parsed_query.get("columns", [])
        filters = parsed_query.get("filters", [])
        group_by = parsed_query.get("group_by")
        aggregations = parsed_query.get("aggregations", [])
        order_by = parsed_query.get("order_by")
        order_desc = parsed_query.get("order_desc", False)
        limit = parsed_query.get("limit")

        # SELECT部分
        if aggregations:
            select_parts = []
            for agg in aggregations:
                select_parts.append(f"{agg['function']}({agg['column']})")
            if group_by:
                select_parts.insert(0, f"`{group_by}`")
            select_clause = ", ".join(select_parts)
        elif columns:
            select_clause = ", ".join([f"`{c}`" for c in columns])
        else:
            select_clause = "*"

        sql = f"SELECT {select_clause} FROM `{schema.name}`"

        # WHERE部分
        if filters:
            where_parts = []
            for f in filters:
                col = f["column"]
                op = f["operator"]
                val = f["value"]
                where_parts.append(f"`{col}` {op} '{val}'")
            sql += " WHERE " + " AND ".join(where_parts)

        # GROUP BY
        if group_by:
            sql += f" GROUP BY `{group_by}`"

        # ORDER BY
        if order_by:
            direction = "DESC" if order_desc else "ASC"
            sql += f" ORDER BY `{order_by}` {direction}"

        # LIMIT
        if limit:
            sql += f" LIMIT {limit}"

        return sql

    def validate_and_fix(
        self,
        sql: str,
        schema: TableSchema
    ) -> Dict[str, Any]:
        """
        验证并尝试修复SQL

        Args:
            sql: SQL语句
            schema: 表结构

        Returns:
            验证结果
        """
        try:
            # 基本语法检查
            if not sql.strip():
                return {"valid": False, "error": "SQL为空"}

            sql_upper = sql.upper()

            # 检查表名
            if schema.name.upper() not in sql_upper:
                return {
                    "valid": False,
                    "error": f"表名 '{schema.name}' 不在SQL中",
                    "suggestion": f"请在SQL中包含表名 {schema.name}"
                }

            # 检查危险操作
            dangerous = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
            for kw in dangerous:
                if kw in sql_upper:
                    return {
                        "valid": False,
                        "error": f"不安全的操作: {kw}"
                    }

            # 检查列名
            column_names = {col.name.lower(): col.name for col in schema.columns}
            invalid_cols = []

            # 简单提取SELECT后的列
            if "SELECT" in sql_upper:
                select_part = sql_upper.split("FROM")[0].replace("SELECT", "").strip()
                if select_part != "*":
                    for col in select_part.split(","):
                        col = col.strip().strip("`").strip()
                        if col and not any(
                            agg in col for agg in ["COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT"]
                        ):
                            if col.lower() not in column_names:
                                invalid_cols.append(col)

            if invalid_cols:
                return {
                    "valid": False,
                    "error": f"未知列: {', '.join(invalid_cols)}",
                    "available_columns": list(column_names.values())
                }

            return {"valid": True, "sql": sql}

        except Exception as e:
            return {
                "valid": False,
                "error": f"验证失败: {str(e)}"
            }


# 全局实例
text2sql = Text2SQLGenerator()
