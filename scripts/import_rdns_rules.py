"""导入 RDNS 分类规则脚本。

用法: python scripts/import_rdns_rules.py <excel_file> [--rules-dir config/classifier] [--dry-run]
例:   python scripts/import_rdns_rules.py data/0518-0524/0518-0524.unclassified_rdns.xlsx
      python scripts/import_rdns_rules.py data/0518-0524/0518-0524.unclassified_rdns.xlsx --dry-run
"""

import argparse
import logging
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("import_rdns_rules")


def main():
    from ip_info.export.rdns_classify_import import import_rdns_rules

    parser = argparse.ArgumentParser(description="导入 RDNS 分类规则")
    parser.add_argument("excel_file", help="标注后的未分类 RDNS Excel 文件路径")
    parser.add_argument("--rules-dir", default=os.path.join(project_root, "config", "classifier"), help="分类规则目录")
    parser.add_argument("--dry-run", action="store_true", help="只验证不写入")
    args = parser.parse_args()

    added, errors = import_rdns_rules(args.excel_file, args.rules_dir, dry_run=args.dry_run)

    if errors:
        logger.error("发现 %d 个错误，请修正后重试:", len(errors))
        for err in errors:
            logger.error("  - %s", err)
        sys.exit(1)

    if added > 0:
        logger.info("成功导入 %d 条规则", added)
    else:
        logger.info("无新规则需要导入")


if __name__ == "__main__":
    main()
