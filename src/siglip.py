"""L1 SigLIP 粗筛打分器：零样本图文相似度算「宣传适配度」。

净分 = 正面 prompt 相似度均值 − 负面 prompt 相似度均值，越高越适合宣传。
模型走 AutoModel/AutoProcessor，换模型只改 config 的 l1.model；
device 跟随硬件档位（cpu/mps/cuda），只改 config 不改代码。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _pooled(out):
    """兼容 transformers 不同版本：get_*_features 可能返回 tensor 或
    BaseModelOutputWithPooling（取 pooler_output）。"""
    return out.pooler_output if hasattr(out, "pooler_output") else out


# 硬件档位 → torch device
_DEVICE_MAP = {
    "cpu": "cpu",
    "mac": "mps",        # Apple Silicon
    "small_gpu": "cuda",
    "large_gpu": "cuda",
}


def parse_prompts(prompt_file: str | Path) -> tuple[list[str], list[str]]:
    """解析 prompt 文件，返回 (正面列表, 负面列表)。

    格式：[positive] / [negative] 段标记；# 开头注释；空行忽略。
    """
    positive: list[str] = []
    negative: list[str] = []
    bucket: list[str] | None = None

    for line in Path(prompt_file).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        low = s.lower()
        if low == "[positive]":
            bucket = positive
        elif low == "[negative]":
            bucket = negative
        elif bucket is not None:
            bucket.append(s)

    if not positive:
        raise ValueError(f"prompt 文件 {prompt_file} 缺少 [positive] 段或为空")
    return positive, negative


def resolve_device(hardware: str, override: str | None) -> str:
    """决定 torch device：l1.device 显式覆盖 > 硬件档位映射 > cpu。"""
    if override:
        return override
    return _DEVICE_MAP.get(hardware, "cpu")


class SiglipScorer:
    """SigLIP 零样本打分器。懒加载模型，文本特征只算一次缓存复用。"""

    def __init__(self, model_name: str, device: str, prompt_file: str | Path):
        self.model_name = model_name
        self.device = device
        self.positive, self.negative = parse_prompts(prompt_file)
        self._model = None
        self._processor = None
        self._text_feats = None  # (n_pos+n_neg, dim) 归一化后的文本特征
        self._n_pos = len(self.positive)

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModel, AutoProcessor

        log.info("[stage1] 加载 SigLIP 模型 %s 到 %s（首次会下载权重）", self.model_name, self.device)
        try:
            self._model = AutoModel.from_pretrained(self.model_name).to(self.device).eval()
        except Exception as e:  # noqa: BLE001 — device 不可用时退回 CPU
            log.warning("[stage1] 加载到 %s 失败（%s），退回 cpu", self.device, e)
            self.device = "cpu"
            self._model = AutoModel.from_pretrained(self.model_name).to("cpu").eval()
        self._processor = AutoProcessor.from_pretrained(self.model_name)

        # 文本特征预计算 + 归一化（所有图共用，不必每张图重算）
        texts = self.positive + self.negative
        inputs = self._processor(text=texts, padding="max_length", return_tensors="pt").to(self.device)
        with torch.no_grad():
            feats = _pooled(self._model.get_text_features(**inputs))
        self._text_feats = feats / feats.norm(dim=-1, keepdim=True)

    def score(self, image_path: str) -> float:
        """返回宣传适配度净分。读图失败返回极低分（-1e9）便于排序时垫底。"""
        import torch
        from PIL import Image

        self._ensure_loaded()
        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:  # noqa: BLE001
            log.debug("[stage1] 读图失败 %s: %s", image_path, e)
            return -1e9

        inputs = self._processor(images=img, return_tensors="pt").to(self.device)
        with torch.no_grad():
            feat = _pooled(self._model.get_image_features(**inputs))
        feat = feat / feat.norm(dim=-1, keepdim=True)

        # 图文余弦相似度（文本特征已归一化）
        sims = (feat @ self._text_feats.T).squeeze(0)  # (n_pos+n_neg,)
        pos_mean = sims[: self._n_pos].mean().item()
        neg_mean = sims[self._n_pos :].mean().item() if sims.shape[0] > self._n_pos else 0.0
        return pos_mean - neg_mean
