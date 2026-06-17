"""配置中枢：读 config.yaml + .env，返回配置对象。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    """从 config.yaml 加载的配置，外加从环境变量读取的密钥。"""

    raw: dict[str, Any]
    root: Path  # 项目根目录，用于解析相对路径（prompt_file 等）

    # ---- 顶层 ----
    @property
    def hardware(self) -> str:
        return self.raw.get("hardware", "cpu")

    @property
    def db_path(self) -> Path:
        return self.root / self.raw.get("db_path", "pipeline.db")

    @property
    def out_dir(self) -> Path:
        return self.root / self.raw.get("out_dir", "out")

    # ---- 各 stage 配置段 ----
    @property
    def l0(self) -> dict[str, Any]:
        return self.raw.get("l0", {})

    @property
    def l1(self) -> dict[str, Any]:
        return self.raw.get("l1", {})

    @property
    def l2(self) -> dict[str, Any]:
        return self.raw.get("l2", {})

    @property
    def export(self) -> dict[str, Any]:
        return self.raw.get("export", {})

    # ---- 密钥（从环境变量读，不写进 yaml）----
    @property
    def ark_api_key(self) -> str | None:
        return os.getenv("ARK_API_KEY")

    def resolve(self, rel: str) -> Path:
        """把 config 里的相对路径解析为绝对路径。"""
        return self.root / rel


def load_config(config_path: str | Path = "config.yaml") -> Config:
    """加载配置。先 load_dotenv 注入 .env，再读 yaml。"""
    config_path = Path(config_path)
    root = config_path.resolve().parent

    # 加载 .env（若存在），让 os.getenv 能读到密钥
    load_dotenv(root / ".env")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Config(raw=raw, root=root)
