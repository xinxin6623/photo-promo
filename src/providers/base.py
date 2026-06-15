"""VLMProvider 抽象基类。

所有 VLM 实现都继承它，新接一家只加 provider 文件，不动调用方（呼应方案里
「接口抽象 + 配置切换」原则）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VLMProvider(ABC):
    @abstractmethod
    def score_and_caption(self, image_path: str, context: dict[str, Any]) -> dict[str, Any]:
        """一次调用同时做精筛判断 + 生成文案。

        Args:
            image_path: 图片路径
            context: 辅助信息（时间/位置等，由 stage2 从 DB 取出传入）

        Returns:
            dict，至少含：
              verdict: str  是否适合宣传的结论 + 理由
              caption: str  生成的宣传文案
        """
        raise NotImplementedError
