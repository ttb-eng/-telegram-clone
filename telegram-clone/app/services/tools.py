import logging
from datetime import datetime
import pytz
import httpx
import asyncio

from duckduckgo_search import DDGS
from urllib.parse import quote
from bs4 import BeautifulSoup


logger=logging.getLogger(__name__)
CITY_TIMEZONE = {
    "北京": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "东京": "Asia/Tokyo",
    "纽约": "America/New_York",
    "伦敦": "Europe/London",
    "巴黎": "Europe/Paris",
    "悉尼": "Australia/Sydney",
    "莫斯科": "Europe/Moscow",
    "洛杉矶": "America/Los_Angeles",
    "首尔": "Asia/Seoul",
    "新加坡": "Asia/Singapore",
    "香港": "Asia/Hong_Kong",
    "迪拜": "Asia/Dubai",
}

TOOLS=[
    {
        "type":"function",
        "function":{
            "name":"get_time",
            "description":"查询指定城市当前的时间点",
            "parameters":{
                "type":"object",
                "properties":{
                    "city":{
                        "type":"string",
                        "description":"城市名称，如北京"
                    }
                },
                "required":["city"],
            },
        },
    },
    {
        "type":"function",
        "function":{
            "name":"get_weather",
            "description":"查询天气",
            "parameters":{
                "type":"object",
                "properties":{
                    "city":{
                        "type":"string",
                        "description":"目前没有定位功能，需要你手动输入你所在城市，来查询天气"
                    }
                },
                "required":["city"],

            },
        },
    },
    {
        "type":"function",
        "function":{
            "name":"web_search",
            "description":"联网搜索",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{
                        "type":"string",
                        "description":"搜索关键词",
                    }
                },
                "required":["query"],
            },

        },
    },
]



async def execute_tools(name:str,args:dict)->str:
    func=TOOLS_FUNCTIONS.get(name)
    if not func:
        return f"还没有{name}功能"
    return await func(**args)

async def _get_time(city:str)->str:
    tz_name=CITY_TIMEZONE.get(city)
    if not tz_name:
        return f"抱歉，无法查询到{city}的时间"
    try:
        tz=pytz.timezone(tz_name)
        now=datetime.now(tz)
        return f"{city}现在的时间是：{now.strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return f"查询失败的原因是:{e}"

async def _get_weather(city:str)->str:
    url = f"https://wttr.in/{city}?format=%C+%t+%h+%w"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        return f"{city} 天气: {resp.text.strip()}"


async def _web_search(query: str) -> str:
    url = f"https://cn.bing.com/search?q={quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for item in soup.select("li.b_algo")[:3]:
                title_tag = item.select_one("h2 a")
                snippet_tag = item.select_one(".b_caption p")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    results.append(f"{title}: {snippet}")
            return "\n".join(results) if results else f"未找到关于「{query}」的信息"
    except Exception as e:
        return f"搜索失败: {e}"

TOOLS_FUNCTIONS={
    "get_time":_get_time,
    "get_weather":_get_weather,
    "web_search":_web_search
}