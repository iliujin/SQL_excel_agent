# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - Streamlit前端界面
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, Optional
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from tools.excel_tools import excel_tool
from tools.db_tools import db_tool
from agents.analysis_agent import analysis_agent, direct_agent


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="SQL + Excel 智能数据分析 Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化会话状态 ====================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "excel_files" not in st.session_state:
    st.session_state.excel_files = {}

if "db_connected" not in st.session_state:
    st.session_state.db_connected = False

if "db_tables" not in st.session_state:
    st.session_state.db_tables = []

if "current_data" not in st.session_state:
    st.session_state.current_data = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("📊 智能数据分析")
        st.markdown("---")

        # 数据源选择
        st.subheader("数据源")

        tab1, tab2 = st.tabs(["Excel", "数据库"])

        with tab1:
            # Excel文件上传
            uploaded_file = st.file_uploader(
                "上传Excel文件",
                type=['xlsx', 'xls'],
                key="excel_upload"
            )

            if uploaded_file:
                # 保存文件
                file_path = f"{settings.DATA_DIR}/{uploaded_file.name}"
                os.makedirs(settings.DATA_DIR, exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 选择工作表
                if st.button("加载文件", key="load_excel"):
                    with st.spinner("加载中..."):
                        result = excel_tool.load_excel(file_path)

                        if result.get("success"):
                            file_key = result.get("file_key")
                            st.session_state.excel_files[file_key] = {
                                "path": file_path,
                                "name": uploaded_file.name
                            }
                            st.success(f"✅ 加载成功: {uploaded_file.name}")
                            st.json(result.get("schema"))
                        else:
                            st.error(f"❌ {result.get('error')}")

            # 已加载的文件
            if st.session_state.excel_files:
                st.markdown("**已加载的文件:**")
                for file_key, info in st.session_state.excel_files.items():
                    st.caption(f"📄 {info['name']}")

        with tab2:
            # 数据库连接
            if not st.session_state.db_connected:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("连接数据库", key="connect_db"):
                        with st.spinner("连接中..."):
                            result = db_tool.connect()

                            if result.get("success"):
                                st.session_state.db_connected = True
                                st.session_state.db_tables = db_tool.list_tables()
                                st.success("✅ 数据库连接成功")
                                st.json({
                                    "database": result.get("database"),
                                    "host": result.get("host")
                                })
                            else:
                                st.error(f"❌ {result.get('error')}")
                with col2:
                    if st.button("断开", key="disconnect_db"):
                        db_tool.disconnect()
                        st.session_state.db_connected = False
                        st.session_state.db_tables = []
                        st.info("已断开连接")
            else:
                st.success("✅ 已连接")
                st.caption(f"数据库: {settings.DB_NAME}")

                # 表列表
                if st.button("刷新表列表", key="refresh_tables"):
                    st.session_state.db_tables = db_tool.list_tables()

                if st.session_state.db_tables:
                    st.markdown("**可用的表:**")
                    selected_table = st.selectbox(
                        "选择表查看结构",
                        st.session_state.db_tables,
                        key="table_select"
                    )

                    if selected_table:
                        schema = db_tool.get_table_schema(selected_table)
                        if schema:
                            with st.expander("表结构"):
                                for col in schema.columns:
                                    st.caption(f"• {col.name}: {col.data_type.value}")

        st.markdown("---")
        st.caption("Powered by LangChain + LangGraph")


# ==================== 主界面 ====================
def render_main():
    """渲染主界面"""
    st.title("💬 智能数据分析对话")
    st.markdown("用自然语言提问，AI将帮你分析数据")

    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                if "data" in message:
                    # 显示数据表格
                    st.dataframe(pd.DataFrame(message["data"]))
                if "chart" in message:
                    # 显示图表
                    st.plotly_chart(message["chart"], use_container_width=True)
                if "text" in message:
                    st.markdown(message["text"])
            else:
                st.markdown(message["content"])

    # 输入框
    if prompt := st.chat_input("输入你的问题..."):
        # 添加用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # 处理分析
        with st.chat_message("assistant"):
            with st.spinner("分析中..."):
                response = process_query(prompt)

                # 显示响应
                if response.get("data"):
                    df = pd.DataFrame(response["data"])
                    st.dataframe(df, use_container_width=True)

                    # 添加统计信息
                    with st.expander("📊 统计信息"):
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            st.write(df[numeric_cols].describe())

                if response.get("text"):
                    st.markdown(response["text"])

                if response.get("error"):
                    st.error(response["error"])

                # 添加助手消息
                st.session_state.messages.append({
                    "role": "assistant",
                    **response
                })


# ==================== 查询处理 ====================
def process_query(prompt: str) -> Dict[str, Any]:
    """处理用户查询"""
    # 构建上下文
    context = {
        "excel_files": list(st.session_state.excel_files.keys()),
        "database_tables": st.session_state.db_tables if st.session_state.db_connected else []
    }

    try:
        # 使用Agent分析
        result = analysis_agent.analyze(prompt, context)

        if result.get("success"):
            query_result = result.get("query_result")

            if query_result and query_result.success and query_result.data:
                return {
                    "data": query_result.data,
                    "text": result.get("response"),
                    "row_count": query_result.row_count
                }
            else:
                return {
                    "text": result.get("response", "分析完成")
                }
        else:
            return {
                "error": result.get("error", "分析失败")
            }

    except Exception as e:
        # 回退到简单模式
        return handle_simple_query(prompt)


def handle_simple_query(prompt: str) -> Dict[str, Any]:
    """处理简单查询（不使用Agent）"""
    prompt_lower = prompt.lower()

    # Excel查询
    if st.session_state.excel_files:
        file_key = list(st.session_state.excel_files.keys())[0]

        # 简单的关键词匹配
        if "分析" in prompt or "统计" in prompt:
            analysis = excel_tool.analyze_excel(file_key)
            return {"text": f"📊 分析结果:\n\n{json.dumps(analysis, ensure_ascii=False, indent=2)}"}

        elif "数据" in prompt or "显示" in prompt or "查询" in prompt:
            result = excel_tool.query_excel(file_key, limit=50)
            if result.success:
                return {
                    "data": result.data,
                    "text": f"✅ 查询成功，返回 {result.row_count} 行",
                    "row_count": result.row_count
                }

    # 数据库查询
    if st.session_state.db_connected and ("sql" in prompt_lower or "数据库" in prompt):
        # 尝试Text-to-SQL
        if st.session_state.db_tables:
            table_name = st.session_state.db_tables[0]
            schema = db_tool.get_table_schema(table_name)

            if schema:
                result = direct_agent.text_to_sql(prompt, schema.to_dict())

                if result.get("success"):
                    sql = result.get("sql")
                    query_result = db_tool.execute_query(sql)

                    if query_result.success:
                        return {
                            "data": query_result.data,
                            "text": f"✅ SQL: `{sql}`",
                            "row_count": query_result.row_count
                        }
                    else:
                        return {"error": query_result.error}

    return {
        "text": "我理解你的问题，但需要更多信息。请确保已加载数据源。"
    }


# ==================== 启动应用 ====================
def main():
    """主函数"""
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
