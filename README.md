# SQL + Excel 智能数据分析 Agent

一个基于 LangChain + LangGraph 的智能数据分析系统，支持 Excel 和 MySQL 数据源的自然语言查询与分析。

## 项目特性

- 📊 **多数据源支持**: Excel 文件 + MySQL 数据库
- 🔍 **自然语言查询**: Text-to-SQL 自动生成 SQL
- 🤖 **智能 Agent**: 基于 LangGraph 的多工具调用框架
- 📈 **统计分析**: 分组聚合、趋势分析、异常检测
- 🎨 **可视化界面**: Streamlit 构建的交互式 Web 界面

## 技术栈

| 类别 | 技术 |
|------|------|
| 核心语言 | Python 3.8+ |
| 数据处理 | Pandas, NumPy |
| Excel 操作 | OpenPyXL |
| 数据库 | SQLAlchemy, PyMySQL |
| LLM 框架 | LangChain, LangGraph |
| API | OpenAI SDK (兼容通义千问) |
| 前端界面 | Streamlit |
| 可视化 | Matplotlib, Plotly |

## 项目结构

```
SQL_EXCEL_AGENT/
├── models/                 # 数据模型
│   └── schemas.py         # 数据结构定义
├── tools/                  # 工具模块
│   ├── excel_tools.py     # Excel 处理工具
│   ├── db_tools.py        # 数据库工具
│   └── functions.py       # Function Calling 工具定义
├── agents/                 # Agent 模块
│   └── analysis_agent.py  # LangGraph Agent 核心
├── utils/                  # 工具函数
│   └── text2sql.py        # Text-to-SQL 生成器
├── config/                 # 配置
│   └── settings.py        # 应用配置
├── ui/                     # 用户界面
│   └── app.py             # Streamlit 应用
├── data/                   # 数据目录
├── output/                 # 输出目录
├── run.py                 # 启动脚本
├── test.py                # 测试文件
├── requirements.txt       # 依赖列表
├── .env.example           # 环境变量示例
└── README.md              # 项目文档
```

## 安装

### 1. 克隆项目

```bash
cd SQL_EXCEL_AGENT
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
# OpenAI API (或通义千问)
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus

# MySQL 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database
```

## 使用

### 启动 Web 界面

```bash
python run.py
```

或使用 streamlit 直接运行：

```bash
streamlit run ui/app.py
```

访问 `http://localhost:8501`

### 运行测试

```bash
python test.py
```

## 功能说明

### 1. Excel 数据分析

- 加载 Excel 文件（支持多 Sheet）
- 自动识别数据类型
- 数据质量检测（空值、重复值）
- 自然语言查询

### 2. 数据库查询

- 连接 MySQL 数据库
- 浏览表结构
- Text-to-SQL 自动生成
- 安全查询执行

### 3. 智能分析

- 分组聚合统计
- 条件筛选
- Top N 排名
- 时间趋势分析
- 异常检测

### 4. Function Calling 工具

| 工具名 | 功能 |
|--------|------|
| load_excel_file | 加载 Excel 文件 |
| query_excel_data | 查询 Excel 数据 |
| analyze_excel_data | 分析 Excel 数据 |
| connect_database | 连接数据库 |
| list_database_tables | 列出数据库表 |
| get_table_schema | 获取表结构 |
| execute_sql_query | 执行 SQL 查询 |
| calculate_statistics | 计算统计数据 |
| aggregate_data | 数据分组聚合 |

## 使用示例

### Excel 分析

```
用户: 加载 data/sales.xlsx
用户: 显示销售额最高的前5个产品
用户: 按品类统计总销售额
用户: 分析价格和销量的关系
```

### 数据库查询

```
用户: 连接数据库
用户: 查看所有表
用户: 查询 users 表的结构
用户: 统计每个城市的用户数量
```

### Text-to-SQL

输入: "查询销售额超过10000的产品"

生成:
```sql
SELECT * FROM sales WHERE 销售额 > 10000
```

## 架构设计

```
┌─────────────────────────────────────────┐
│         Streamlit Web UI                │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         LangGraph Agent                 │
│  ┌───────────┐    ┌──────────────┐     │
│  │   LLM     │───▶│  Tool Router │     │
│  │ (通义千问)  │    └──────────────┘     │
│  └───────────┘           │               │
│                           ▼               │
│  ┌─────────────────────────────────┐   │
│  │         Function Tools           │   │
│  │  - Excel Tools                   │   │
│  │  - Database Tools                │   │
│  │  - Statistics Tools              │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    ▼                       ▼
┌─────────┐          ┌──────────┐
│  Excel  │          │  MySQL   │
└─────────┘          └──────────┘
```

## 开发

### 添加新工具

1. 在 `tools/` 目录下实现工具函数
2. 在 `tools/functions.py` 中添加工具定义
3. 将工具添加到 `TOOLS_DEFINITION` 和 `TOOLS_MAP`

### 扩展数据源

1. 在 `models/schemas.py` 中添加 `DataSourceType`
2. 实现对应的 Tool 类
3. 在 Agent 中注册新工具

## 注意事项

- SQL 查询仅支持 SELECT 语句
- 大文件查询建议使用 LIMIT 限制行数
- 数据库连接信息请妥善保管
- API Key 有调用配额限制

## License

MIT License
