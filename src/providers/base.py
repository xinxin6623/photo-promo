"""VLMProvider 抽象基类。

所有 VLM 实现都继承它，新接一家只加 provider 文件，不动调用方（呼应方案里
「接口抽象 + 配置切换」原则）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VLMProvider(ABC):
    @abstractmethod
    def score_and_describe(self, image_path: str, context: dict[str, Any]) -> dict[str, Any]:
        """一次调用同时做精筛判断 + 输出结构化语义描述（非文案）。

        Args:
            image_path: 图片路径
            context: 辅助信息（时间/位置等，由 stage2 从 DB 取出传入）

        Returns:
            dict，对齐 docs/io-contract.md §3.3 的描述 schema，至少含：
              verdict: dict  {fit: bool, reason: str} 是否适合入库 + 理由
              （fit=True 时）summary / description / scene / subjects /
              people_count / mood / tags / suitable_for / quality 等结构化字段
        """
        raise NotImplementedError
