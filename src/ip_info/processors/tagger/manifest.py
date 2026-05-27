import json
import os


def load_manifest(manifest_path: str, level: int | None = None) -> list[dict]:
    """加载 manifest.json，支持 level 过滤。

    Args:
        manifest_path: manifest.json 文件路径
        level: 标签级别过滤，仅保留 level <= 给定值的条目

    Returns:
        manifest 条目列表

    Raises:
        FileNotFoundError: manifest 文件不存在
        ValueError: manifest 中存在重复标签名
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"清单文件不存在: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    labels = [item["label"] for item in manifest]
    if len(labels) != len(set(labels)):
        dup = [label for label in labels if labels.count(label) > 1]
        raise ValueError(f"manifest.json 中存在重复标签名: {set(dup)}")

    if level is not None:
        manifest = [item for item in manifest if item.get("level", 1) <= level]

    return manifest


def validate_manifest(manifest: list[dict], config_dir: str) -> None:
    """验证 manifest 中引用的文件是否都存在。

    Args:
        manifest: manifest 条目列表
        config_dir: 配置文件目录

    Raises:
        FileNotFoundError: 有文件缺失
    """
    missing = []
    for item in manifest:
        fpath = os.path.join(config_dir, item["file"])
        if not os.path.exists(fpath):
            missing.append(item["file"])
    if missing:
        raise FileNotFoundError(f"以下配置文件缺失: {', '.join(missing)}")
