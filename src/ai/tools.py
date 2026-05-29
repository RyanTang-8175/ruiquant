"""
AI 工具定义（DeepSeek function calling）
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "获取股票最新行情数据，包括价格、涨跌幅、成交量、换手率等",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码，如 600519"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_technical_analysis",
            "description": "获取股票技术分析指标，包括均线、MACD、RSI、KDJ、布林带等",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码"},
                    "days": {"type": "integer", "description": "分析天数，默认60"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_scoring_result",
            "description": "获取股票的量化评分结果，包括总分、评级和各因子详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_snapshot",
            "description": "获取当前市场整体概况，包括涨跌家数、涨停跌停、成交额等",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_watchlist",
            "description": "获取当前观察池中评分最高的股票列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回数量，默认10"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "获取最新财经新闻，可按股票代码或类别筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码（可选）"},
                    "category": {"type": "string", "description": "新闻类别：policy/sector/company/macro"},
                    "limit": {"type": "integer", "description": "返回条数，默认10"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_data",
            "description": "获取股票基本面数据，包括近期涨跌幅、成交量趋势、换手率等",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_positions",
            "description": "获取模拟盘当前持仓和账户状态",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_kline_data",
            "description": "获取股票K线数据（最近N天的OHLCV），用于形态分析",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "股票代码"},
                    "days": {"type": "integer", "description": "天数，默认30"}
                },
                "required": ["code"]
            }
        }
    },
]
