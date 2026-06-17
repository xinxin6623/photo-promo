"""火山方舟 Ark VLM provider（Phase 3 实现）。

Ark 走 OpenAI 兼容接口：
  base_url: https://ark.cn-beijing.volces.com/api/v3
  api_key:  环境变量 ARK_API_KEY
  model:    doubao-vision 系列模型名，或推理接入点 ID（ep-xxxx）

一次调用同时拿到「精筛结论」+「结构化语义描述」（JSON）：把图片以 base64
data URL 传入，system 用 prompts/l2_describe.txt（其中 {taken_at}/{location}
由 context 填充），要求模型按 io-contract §3.3 的 schema 输出 JSON。

注意：这里只产出**结构化语义描述**，不是成稿文案——出口是照片库 vault。
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

from .base import VLMProvider

log = logging.getLogger(__name__)


class ArkProvider(VLMProvider):
    def __init__(self, model: str, base_url: str, api_key: str | None, prompt: str):
        if not api_key:
            raise ValueError(
                "ARK_API_KEY 未设置：L2 需要环境变量 ARK_API_KEY（见 .env.example）"
            )
        self.model = model
        self.prompt = prompt
        # 延迟导入，保持「依赖按 Phase 增量加」——只有真跑 L2 才需要 openai
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def _image_data_url(self, image_path: str) -> str:
        """把本地图片读成 base64 data URL（Ark 接受 data: 内联图）。"""
        mime, _ = mimetypes.guess_type(image_path)
        mime = mime or "image/jpeg"
        raw = Path(image_path).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def score_and_describe(self, image_path: str, context: dict[str, Any]) -> dict[str, Any]:
        # prompt 里的 {taken_at}/{location} 占位用 context 填充（缺失填「未知」）。
        # 用 replace 而非 str.format：prompt 含 JSON 示例的 {}，format 会误判成占位符。
        system_prompt = (
            self.prompt
            .replace("{taken_at}", str(context.get("taken_at") or "未知"))
            .replace("{location}", str(context.get("location") or "未知"))
        )
        data_url = self._image_data_url(image_path)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": "请按要求输出 JSON。"},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        return self._parse(content, image_path)

    @staticmethod
    def _parse(content: str, image_path: str) -> dict[str, Any]:
        """解析模型返回的 JSON。容错：剥 ```json 围栏；解析失败标 fit=False 不入库。"""
        text = content.strip()
        if text.startswith("```"):
            # 去掉 ```json ... ``` 围栏
            text = text.split("```", 2)[1] if text.count("```") >= 2 else text
            text = text.lstrip("json").strip().rstrip("`").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.warning("[ark] JSON 解析失败，按不入库处理：%s\n原始返回: %s", image_path, content[:200])
            return {
                "verdict": {"fit": False, "reason": "VLM 返回非合法 JSON，无法解析"},
            }
        # 兜底：确保有 verdict 结构
        if "verdict" not in data or not isinstance(data.get("verdict"), dict):
            data["verdict"] = {"fit": True, "reason": "(模型未给 verdict，默认入库)"}
        return data
