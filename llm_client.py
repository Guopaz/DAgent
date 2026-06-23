"""LLM 客户端 — 封装 OpenAI API 调用。"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


class LLMClient:
    """LLM 客户端。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ):
        # 从环境变量读取配置（支持自定义变量名）
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "gpt-4o"
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_key:
            raise ValueError(
                "API key not found. Set LLM_API_KEY or OPENAI_API_KEY in .env or environment."
            )

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def chat(self, system_prompt: str, user_prompt: str = "") -> str:
        """发送聊天请求。"""
        messages = [{"role": "system", "content": system_prompt}]
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content or ""

    def chat_with_image(self, system_prompt: str, image_base64: str, user_prompt: str = "") -> str:
        """发送带图片的聊天请求（用于视觉分析）。"""
        messages = [{"role": "system", "content": system_prompt}]
        
        user_content = []
        if user_prompt:
            user_content.append({"type": "text", "text": user_prompt})
        
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            })
        
        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content or ""
