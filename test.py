# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - 测试文件
"""
import sys
import os
import io

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from tools.excel_tools import excel_tool
from tools.db_tools import db_tool
from utils.text2sql import text2sql
from agents.analysis_agent import analysis_agent, direct_agent
from models.schemas import TableSchema, ColumnInfo, DataType, DataSourceType


def create_test_excel():
    """创建测试Excel文件"""
    os.makedirs("data", exist_ok=True)

    data = {
        "产品名称": [
            "SK-II神仙水", "兰蔻小黑瓶", "雅诗兰黛", "海蓝之谜",
            "iPhone 15", "iPad Pro", "MacBook Pro", "AirPods"
        ],
        "品类": ["美妆", "美妆", "美妆", "美妆", "电子", "电子", "电子", "电子"],
        "价格": [1540, 780, 890, 2300, 5999, 7999, 12999, 1299],
        "库存": [50, 120, 80, 30, 100, 50, 20, 200],
        "销售额": [77000, 93600, 71200, 69000, 299950, 399950, 259980, 129900]
    }

    df = pd.DataFrame(data)
    filepath = "data/test_sales.xlsx"
    df.to_excel(filepath, index=False)
    print(f"✅ 测试Excel文件已创建: {filepath}")
    return filepath


def test_excel_tool():
    """测试Excel工具"""
    print("\n" + "="*50)
    print("测试1: Excel工具")
    print("="*50)

    # 创建测试文件
    filepath = create_test_excel()

    # 加载文件
    result = excel_tool.load_excel(filepath)
    print(f"\n加载结果: {result.get('success')}")
    print(f"文件键: {result.get('file_key')}")
    print(f"行数: {result.get('row_count')}")
    print(f"列: {result.get('columns')}")

    # 查询数据
    if result.get('success'):
        file_key = result.get('file_key')
        query_result = excel_tool.query_excel(file_key, limit=5)
        print(f"\n查询成功: {query_result.success}")
        print(f"返回行数: {query_result.row_count}")

    # 分析数据
    if result.get('success'):
        file_key = result.get('file_key')
        analysis = excel_tool.analyze_excel(file_key)
        print(f"\n数据统计:")
        print(f"- 总行数: {analysis.get('basic_info', {}).get('row_count')}")
        print(f"- 重复行: {analysis.get('duplicate_rows')}")
        if analysis.get('numeric_stats'):
            print(f"- 数值统计: {list(analysis.get('numeric_stats', {}).keys())}")


def test_text2sql():
    """测试Text-to-SQL"""
    print("\n" + "="*50)
    print("测试2: Text-to-SQL")
    print("="*50)

    # 创建模拟表结构
    schema = TableSchema(
        name="sales",
        source_type=DataSourceType.MYSQL,
        columns=[
            ColumnInfo(name="产品名称", data_type=DataType.STRING),
            ColumnInfo(name="品类", data_type=DataType.STRING),
            ColumnInfo(name="价格", data_type=DataType.INTEGER),
            ColumnInfo(name="库存", data_type=DataType.INTEGER),
            ColumnInfo(name="销售额", data_type=DataType.INTEGER)
        ],
        row_count=100
    )

    # 测试查询解析
    queries = [
        "显示销售额最高的前5个产品",
        "按品类统计总销售额",
        "查询价格大于1000的产品",
        "统计各品类的平均价格"
    ]

    for query in queries:
        print(f"\n查询: {query}")
        parsed = text2sql.parse_query(query, schema)
        print(f"意图: {parsed.get('intent')}")
        print(f"分组: {parsed.get('group_by')}")
        print(f"聚合: {parsed.get('aggregations')}")
        print(f"过滤: {parsed.get('filters')}")

        # 生成SQL
        sql = text2sql.generate_sql(parsed, schema)
        print(f"SQL: {sql}")


def test_agent():
    """测试Agent"""
    print("\n" + "="*50)
    print("测试3: Agent分析")
    print("="*50)

    # 创建测试数据
    filepath = create_test_excel()
    result = excel_tool.load_excel(filepath)

    if result.get('success'):
        context = {
            "excel_files": [result.get('file_key')],
            "schemas": {
                result.get('file_key'): result.get('schema')
            }
        }

        # 测试简单查询
        test_queries = [
            "显示所有数据",
            "统计各品类的销售额",
            "分析价格分布"
        ]

        for query in test_queries:
            print(f"\n查询: {query}")
            response = analysis_agent.analyze(query, context)
            print(f"成功: {response.get('success')}")
            if response.get('query_result'):
                qr = response.get('query_result')
                print(f"返回行数: {qr.row_count if qr else 0}")


def main():
    """运行所有测试"""
    print("="*50)
    print("SQL + Excel 智能数据分析 Agent - 测试")
    print("="*50)

    try:
        test_excel_tool()
        test_text2sql()
        test_agent()

        print("\n" + "="*50)
        print("✅ 所有测试完成")
        print("="*50)
        print("\n启动Streamlit应用:")
        print("  python run.py")
        print("  或")
        print("  streamlit run ui/app.py")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
