"""火山方舟 Ark VLM provider（占位，Phase 3 填实现）。

Ark 走 OpenAI 兼容接口：
  base_url: https://ark.cn-beijing.volces.com/api/v3
  api_key:  环境变量 ARK_API_KEY
  model:    doubao-vision 系列模型名，或推理接入点 ID（ep-xxxx）

Phase 3 将做：用 openai 库指向 Ark base_url，把图片以 base64 data URL 传入，
配合 prompts/l2_describe.txt 一次拿到 精筛结论 + 结构化语义描述（JSON）。
描述 schema 见 docs/io-contract.md §3.3。

Phase 0：占位，不调 API，返回固定结构，保证链路能空跑。
"""
from __future__ import annotations

from typing import Any

from .base import VLMProvider


class ArkProvider(VLMProvider):
    def __init__(self, model: str, base_url: str, api_key: str | None):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        # TODO(Phase 3): from openai import OpenAI; self.client = OpenAI(base_url=..., api_key=...)

    def score_and_describe(self, image_path: str, context: dict[str, Any]) -> dict[str, Any]:
        # TODO(Phase 3): 读图 -> base64 -> 调 chat.completions（model=self.model）-> 解析 JSON
        return {
            "verdict": {"fit": True, "reason": "(占位) Phase 3 未实现，未真实调用 Ark API"},
            "summary": "(占位描述)",
        }
