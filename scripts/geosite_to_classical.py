#!/usr/bin/env python3
"""把 MetaCubeX meta-rules-dat 的 geosite 文本列表转成 Shadowrocket / mihomo 都能读的 classical 列表。

源格式（每行一个）：
  +.example.com   -> DOMAIN-SUFFIX,example.com
  example.com     -> DOMAIN,example.com
其他格式无法等价转换，跳过并打印 GitHub Actions 警告。

只有规则内容变化时才改写输出文件，避免每天产生只改日期的提交。
"""

import argparse
import datetime
import re
import sys
import urllib.parse
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/{category}.list"
DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", re.IGNORECASE)


def fetch(category):
    url = SOURCE_URL.format(category=urllib.parse.quote(category))
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8"), SOURCE_URL.format(category=category)


def convert(text):
    rules, skipped = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+."):
            domain, kind = line[2:], "DOMAIN-SUFFIX"
        else:
            domain, kind = line, "DOMAIN"
        if DOMAIN_RE.match(domain):
            rules.append(f"{kind},{domain.lower()}")
        else:
            skipped.append(line)
    # 去重并保持稳定顺序，便于 diff
    return sorted(set(rules), key=lambda r: (r.split(",", 1)[1], r)), skipped


def existing_rules(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("category", help="geosite 分类名，例如 category-ai-!cn")
    ap.add_argument("output", help="输出文件，例如 rule/AI_NonCN.list")
    ap.add_argument("--title", default="", help="写在文件头的说明")
    ap.add_argument("--min-rules", type=int, default=50, help="少于这个数量视为上游异常，拒绝覆盖")
    args = ap.parse_args()

    text, url = fetch(args.category)
    rules, skipped = convert(text)

    for s in skipped:
        print(f"::warning::{args.category}: 无法转换，已跳过: {s}")
    if len(rules) < args.min_rules:
        print(f"::error::{args.category} 只转换出 {len(rules)} 条，低于 {args.min_rules}，可能是上游异常，未覆盖 {args.output}")
        return 1

    if existing_rules(args.output) == rules:
        print(f"{args.output}: 无变化（{len(rules)} 条）")
        return 0

    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    header = [
        f"# {args.title or args.category}",
        f"# Update {today}",
        f"# 由 GitHub Action 每天从 {url} 自动生成，请勿手改",
        f"# 共 {len(rules)} 条",
        "",
    ]
    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + rules) + "\n")
    print(f"{args.output}: 已更新（{len(rules)} 条，跳过 {len(skipped)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
