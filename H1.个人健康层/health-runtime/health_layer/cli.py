from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .aggregate import aggregate_day, aggregate_range
from .audit import audit_database
from .database import initialize
from .diagnostics import source_contributions
from .importer import import_apple_health, renormalize_all
from .reporting import generate_report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="health-layer", description="个人健康数据层")
    root.add_argument("--db", default="data/health.db", help="SQLite 数据库路径")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="初始化本地数据库")
    commands.add_parser("audit", help="审计导入完整性、质量状态和未知指标")
    commands.add_parser("normalize", help="基于当前指标字典重建标准化层")

    import_command = commands.add_parser("import", help="导入 Apple 健康 export.zip 或 export.xml")
    import_command.add_argument("path")

    aggregate_command = commands.add_parser("aggregate", help="生成每日汇总")
    aggregate_command.add_argument("--date")
    aggregate_command.add_argument("--from", dest="date_from")
    aggregate_command.add_argument("--to", dest="date_to")

    report_command = commands.add_parser("report", help="生成 JSON 和 Markdown 健康日报")
    report_command.add_argument("date")
    report_command.add_argument("--output", default="reports/daily")

    pipeline_command = commands.add_parser("pipeline", help="完成导入、汇总和最新日报生成")
    pipeline_command.add_argument("path")
    pipeline_command.add_argument("--output", default="reports/daily")

    inspect_command = commands.add_parser("inspect-sources", help="查看某日某指标的来源贡献")
    inspect_command.add_argument("date")
    inspect_command.add_argument("metric")
    return root


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    db_path = Path(args.db)

    if args.command == "init":
        initialize(db_path)
        print(f"数据库已初始化：{db_path.resolve()}")
        return 0

    if args.command == "audit":
        print(json.dumps(audit_database(db_path), ensure_ascii=False, indent=2))
        return 0

    if args.command == "normalize":
        print(json.dumps(renormalize_all(db_path), ensure_ascii=False, indent=2))
        return 0

    if args.command == "inspect-sources":
        print(json.dumps(source_contributions(args.date, args.metric, db_path), ensure_ascii=False, indent=2))
        return 0

    if args.command == "import":
        result = import_apple_health(args.path, db_path=db_path)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0 if result.status.startswith("completed") else 1

    if args.command == "aggregate":
        if args.date:
            result = [aggregate_day(args.date, db_path=db_path)]
        elif args.date_from and args.date_to:
            result = aggregate_range(args.date_from, args.date_to, db_path=db_path)
        else:
            raise SystemExit("aggregate 需要 --date，或同时提供 --from 与 --to")
        print(
            json.dumps(
                {
                    "generated": len(result),
                    "from": result[0]["date"] if result else None,
                    "to": result[-1]["date"] if result else None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "report":
        _report, json_path, markdown_path = generate_report(
            args.date,
            db_path=db_path,
            output_dir=args.output,
        )
        print(f"JSON：{json_path.resolve()}")
        print(f"Markdown：{markdown_path.resolve()}")
        return 0

    if args.command == "pipeline":
        result = import_apple_health(args.path, db_path=db_path)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        if not result.status.startswith("completed"):
            return 1
        if result.min_date and result.max_date:
            aggregate_range(result.min_date, result.max_date, db_path=db_path)
            _report, json_path, markdown_path = generate_report(
                result.max_date,
                db_path=db_path,
                output_dir=args.output,
            )
            print(f"最新日报：{markdown_path.resolve()}")
            print(f"机器可读报告：{json_path.resolve()}")
        return 0

    return 2

