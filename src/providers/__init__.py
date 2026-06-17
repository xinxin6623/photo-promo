"""VLM provider 工厂：按 config 的 l2.provider 切换实现。"""
from __future__ import annotations

from ..config import Config
from .base import VLMProvider


def get_provider(cfg: Config) -> VLMProvider:
    name = cfg.l2.get("provider", "ark")
    if name == "ark":
        from .ark import ArkProvider

        prompt_path = cfg.resolve(cfg.l2.get("prompt_file", "prompts/l2_describe.txt"))
        prompt = prompt_path.read_text(encoding="utf-8")
        return ArkProvider(
            model=cfg.l2.get("model", ""),
            base_url=cfg.l2.get("base_url", ""),
            api_key=cfg.ark_api_key,
            prompt=prompt,
        )
    raise ValueError(f"未知 VLM provider: {name!r}（在 config.yaml 的 l2.provider 配置）")
