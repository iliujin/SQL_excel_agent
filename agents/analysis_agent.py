# -*- coding: utf-8 -*-
"""
SQL + Excel 智能数据分析 Agent - LangGraph Agent核心
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import json
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from models.schemas import AgentState, QueryResult
from tools.functions import TOOLS_DEFINITION, TOOLS_MAP
from config.settings import settings
from utils.text2sql import text2sql


# 将函数转换为 LangChain 工具对象
def create_langchain_tools():
    """创建 LangChain 工具对象列表"""
    tools = []
    for tool_def in TOOLS_DEFINITION:
        func = tool_def["function"]
        func_name = func["name"]
        func_obj = TOOLS_MAP.get(func_name)

        if func_obj:
            tool = StructuredTool.from_function(
                func=func_obj,
                name=func_name,
                description=func["description"]
            )
            tools.append(tool)

    return tools


class AnalysisAgent:
    """数据分析Agent核心"""

    def __init__(self):
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=settings.MODEL_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

        # 创建 LangChain 工具
        self.langchain_tools = create_langchain_tools()

        # 绑定工具
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)

        # 构建状态图
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建Agent状态图"""

        # 定义节点
        def call_model(state: AgentState) -> Dict[str, Any]:
            """调用LLM"""
            messages = state["messages"]
            # 将 LangChain 消息转换为兼容格式
            lc_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        lc_messages.append(SystemMessage(content=content))
                    elif role == "user":
                        lc_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        lc_messages.append(AIMessage(content=content))
                    else:
                        lc_messages.append(msg)
                else:
                    lc_messages.append(msg)

            response = self.llm_with_tools.invoke(lc_messages)
            return {"messages": [response]}

        def should_continue(state: AgentState) -> str:
            """决定是否继续"""
            messages = state["messages"]
            last_message = messages[-1] if messages else None

            # 检查最后一条消息是否是 AIMessage 且有 tool_calls
            if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END

        # 创建图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.langchain_tools))

        # 设置入口
        workflow.set_entry_point("agent")

        # 添加边
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行分析

        Args:
            query: 用户查询
            context: 上下文信息（已加载的文件、数据库表等）

        Returns:
            分析结果
        """
        # 构建系统消息
        system_prompt = self._build_system_prompt(context or {})

        # 构建消息列表（转换为字典格式）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # 初始化状态 - TypedDict 用字典初始化
        initial_state: AgentState = {
            "messages": messages,
            "current_query": query,
            "detected_intent": None,
            "generated_sql": "",
            "query_result": None,
            "error_count": 0,
            "data_sources": {}
        }

        # 执行图
        try:
            result = self.graph.invoke(initial_state)

            # 提取最终结果
            final_response = self._extract_final_response(result)

            return {
                "success": True,
                "response": final_response,
                "query_result": result.get("query_result"),
                "steps": len(result["messages"])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"分析过程出错: {str(e)}"
            }

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """构建系统提示词"""
        prompt = """你是一个智能数据分析助手，可以帮助用户分析Excel文件和数据库数据。

你可以使用以下工具：
1. load_excel_file - 加载Excel文件
2. query_excel_data - 查询Excel数据
3. analyze_excel_data - 分析Excel数据
4. connect_database - 连接MySQL数据库
5. list_database_tables - 列出数据库表
6. get_table_schema - 获取表结构
7. execute_sql_query - 执行SQL查询
8. calculate_statistics - 计算统计数据
9. aggregate_data - 数据分组聚合

工作流程：
1. 理解用户的分析需求
2. 确定需要使用的数据源（Excel或数据库）
3. 如果是Excel，先加载文件，再进行分析
4. 如果是数据库，先连接，查看表结构，再执行查询
5. 对结果进行统计分析和可视化建议

注意事项：
- SQL查询只支持SELECT语句，不允许修改数据
- 如果数据量大，建议使用LIMIT限制返回行数
- 对数值数据进行分析时，说明统计意义
- 发现异常或模式时，主动指出

"""

        # 添加上下文信息
        if context:
            if "excel_files" in context and context["excel_files"]:
                prompt += f"\n已加载的Excel文件: {', '.join(context['excel_files'])}\n"

            if "database_tables" in context and context["database_tables"]:
                prompt += f"\n可用的数据库表: {', '.join(context['database_tables'])}\n"

            if "schemas" in context:
                prompt += "\n数据结构:\n"
                for name, schema in context["schemas"].items():
                    prompt += f"- {name}: {', '.join([col['name'] for col in schema.get('columns', [])])}\n"

        return prompt

    def _extract_final_response(self, result: Dict[str, Any]) -> str:
        """提取最终响应"""
        messages = result.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                return msg.content

        # 如果没有找到文本响应，尝试提取工具结果
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(data, dict) and "data" in data:
                        return f"查询完成，返回 {data.get('row_count', 0)} 行数据"
                except:
                    pass

        return "分析完成"

    def stream_analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        流式执行分析（用于实时反馈）

        Args:
            query: 用户查询
            context: 上下文信息

        Yields:
            中间步骤和结果
        """
        system_prompt = self._build_system_prompt(context or {})

        # 构建消息列表（转换为字典格式）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # 初始化状态 - TypedDict 用字典初始化
        initial_state: AgentState = {
            "messages": messages,
            "current_query": query,
            "detected_intent": None,
            "generated_sql": "",
            "query_result": None,
            "error_count": 0,
            "data_sources": {}
        }

        # 流式执行
        for event in self.graph.stream(initial_state):
            yield event


class DirectAnalysisAgent:
    """直接分析Agent（不使用LangGraph，用于简单场景）"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    def text_to_sql(
        self,
        query: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Text-to-SQL转换

        Args:
            query: 自然语言查询
            schema: 表结构信息

        Returns:
            SQL和解析结果
        """
        # 构建提示词
        columns_desc = "\n".join([
            f"- {col['name']}: {col.get('data_type', 'unknown')}"
            for col in schema.get("columns", [])
        ])

        prompt = f"""你是SQL专家。请将以下自然语言查询转换为SQL语句。

表名: {schema.get('name', 'table')}
列信息:
{columns_desc}

用户查询: {query}

请只返回SQL语句，不要包含任何解释。"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            sql = response.content.strip()

            # 清理可能的markdown标记
            sql = sql.replace("```sql", "").replace("```", "").strip()

            # 验证SQL
            from models.schemas import TableSchema, ColumnInfo, DataType, DataSourceType
            schema_obj = TableSchema(
                name=schema.get("name", "table"),
                source_type=DataSourceType.MYSQL,
                columns=[
                    ColumnInfo(
                        name=col["name"],
                        data_type=DataType(col.get("data_type", "string"))
                    )
                    for col in schema.get("columns", [])
                ]
            )

            validation = text2sql.validate_and_fix(sql, schema_obj)

            return {
                "success": validation.get("valid", False),
                "sql": sql,
                "validation": validation
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def suggest_analysis(
        self,
        data_info: Dict[str, Any]
    ) -> List[str]:
        """
        建议分析方向

        Args:
            data_info: 数据信息

        Returns:
            建议列表
        """
        prompt = f"""你是数据分析专家。根据以下数据信息，给出3-5个有价值的分析建议。

数据信息:
- 数据源: {data_info.get('source', 'unknown')}
- 行数: {data_info.get('row_count', 0)}
- 列数: {data_info.get('column_count', 0)}
- 列名: {', '.join(data_info.get('columns', []))}
- 数据类型: {data_info.get('data_types', {})}

请以JSON数组格式返回建议，每个建议包含:
- type: 分析类型 (统计、对比、趋势、分布)
- description: 描述
- query: 示例查询

只返回JSON，不要其他内容。"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # 尝试解析JSON
            import json
            suggestions = json.loads(content)
            return suggestions if isinstance(suggestions, list) else []

        except:
            return []


# 全局实例
analysis_agent = AnalysisAgent()
direct_agent = DirectAnalysisAgent()
