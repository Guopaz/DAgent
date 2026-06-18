"""测试辅助 — WDA 连接。"""
import os
from dotenv import load_dotenv
from wda_client import WDAClient

load_dotenv()


def connect_wda(url: str | None = None) -> WDAClient:
    wda = WDAClient(url or os.getenv("WDA_URL", "http://localhost:8100"))
    print(f"WDA: {wda.get_status().get('value', {}).get('state', '?')}")
    wda.create_session()
    print(f"Session: {wda.session_id}")
    return wda
