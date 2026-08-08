#!/usr/bin/env python3
"""引用账本：登记来源、校验逐字引文、检查报告里的引用是否都真实存在。

设计原则：全部判定都是确定性字符串匹配，不依赖任何模型判断。
文字纪律会被突破，脚本不会。

用法：
    sources.py add <url> --title "..." [--ledger sources.json]
        登记一条来源，返回稳定 id。同一 URL 重复登记返回原 id。

    sources.py quote <id> --text "<引文>" --from <页面文本文件> [--ledger ...]
        校验引文是否逐字出现在抓到的页面文本里。改写/转述/记错的数字一律拒收。

    sources.py verify <报告文件...> [--ledger ...] [--min-coverage 0.0]
        检查报告里出现的每个 [S<id>] 在账本里都存在，且被引用的来源都挂过引文。
        任何一项不通过即非零退出。
"""

import argparse
import json
import re
import sys
from pathlib import Path

CITE_PATTERN = re.compile(r"\[S(\d+)\]")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
EMPHASIS = re.compile(r"[*_`~]+")
WHITESPACE = re.compile(r"\s+")


def match_key(text):
    """归一化：去 markdown 链接保留 label、去强调符、折叠空白、casefold。"""
    without_links = MD_LINK.sub(r"\1", text)
    without_emphasis = EMPHASIS.sub("", without_links)
    return WHITESPACE.sub(" ", without_emphasis).strip().casefold()


def quote_in_evidence(quote, evidence):
    key = match_key(quote)
    return bool(key) and key in match_key(evidence)


def load_ledger(path):
    if not path.exists():
        return {"sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"账本损坏，无法解析 {path}: {exc}")


def save_ledger(path, ledger):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def find_source(ledger, source_id):
    for source in ledger["sources"]:
        if source["id"] == source_id:
            return source
    return None


def cmd_add(args):
    path = Path(args.ledger)
    ledger = load_ledger(path)

    for source in ledger["sources"]:
        if source["url"] == args.url:
            print(f"S{source['id']}  (已存在)")
            return 0

    next_id = max((s["id"] for s in ledger["sources"]), default=0) + 1
    entry = {"id": next_id, "url": args.url, "title": args.title or "", "quotes": []}
    save_ledger(path, {"sources": [*ledger["sources"], entry]})
    print(f"S{next_id}")
    return 0


def cmd_quote(args):
    path = Path(args.ledger)
    ledger = load_ledger(path)
    source = find_source(ledger, args.id)
    if source is None:
        sys.exit(f"✗ 账本里没有 S{args.id}。只能使用 add 返回的 id，不要发明 id。")

    evidence_path = Path(args.source_text)
    if not evidence_path.exists():
        sys.exit(f"✗ 找不到页面文本文件：{evidence_path}")
    evidence = evidence_path.read_text(encoding="utf-8", errors="replace")

    if not quote_in_evidence(args.text, evidence):
        sys.exit(
            f"✗ 引文未在 S{args.id} 的页面文本中逐字出现。\n"
            f"  引文：{args.text[:120]}\n"
            f"  引文必须从原文粘贴。改写、转述、记错的数字一律拒收。"
        )

    updated = {**source, "quotes": [*source["quotes"], args.text]}
    others = [s for s in ledger["sources"] if s["id"] != args.id]
    save_ledger(path, {"sources": sorted([*others, updated], key=lambda s: s["id"])})
    print(f"✓ S{args.id} 引文已校验")
    return 0


def cmd_verify(args):
    path = Path(args.ledger)
    ledger = load_ledger(path)
    known = {s["id"] for s in ledger["sources"]}
    quoted = {s["id"] for s in ledger["sources"] if s["quotes"]}

    cited = set()
    for target in args.reports:
        report_path = Path(target)
        if not report_path.exists():
            sys.exit(f"✗ 找不到报告文件：{report_path}")
        text = report_path.read_text(encoding="utf-8", errors="replace")
        cited.update(int(m) for m in CITE_PATTERN.findall(text))

    problems = []

    phantom = sorted(cited - known)
    if phantom:
        problems.append(
            "账本里不存在的引用（疑似编造）：" + ", ".join(f"S{i}" for i in phantom)
        )

    if not cited:
        problems.append("报告里没有任何 [S<id>] 引用")

    unsupported = sorted(cited & known - quoted)
    if args.require_quotes and unsupported:
        problems.append(
            "被引用但没挂过逐字引文的来源：" + ", ".join(f"S{i}" for i in unsupported)
        )

    coverage = len(cited & known) / len(known) if known else 0.0
    if coverage < args.min_coverage:
        problems.append(f"账本覆盖率 {coverage:.0%} 低于要求的 {args.min_coverage:.0%}")

    if problems:
        print("✗ 校验未通过：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"✓ 校验通过：引用 {len(cited)} 条，账本 {len(known)} 条，覆盖率 {coverage:.0%}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", default="sources.json", help="账本路径（默认 sources.json）")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="登记来源，返回稳定 id")
    add.add_argument("url")
    add.add_argument("--title", default="")
    add.set_defaults(func=cmd_add)

    quote = sub.add_parser("quote", help="校验逐字引文")
    quote.add_argument("id", type=int)
    quote.add_argument("--text", required=True, help="声称的支撑引文")
    quote.add_argument("--from", dest="source_text", required=True, help="抓到的页面文本文件")
    quote.set_defaults(func=cmd_quote)

    verify = sub.add_parser("verify", help="校验报告里的引用")
    verify.add_argument("reports", nargs="+")
    verify.add_argument("--min-coverage", type=float, default=0.0)
    verify.add_argument("--require-quotes", action="store_true")
    verify.set_defaults(func=cmd_verify)

    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    sys.exit(parsed.func(parsed))
