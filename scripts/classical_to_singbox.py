#!/usr/bin/env python3
"""把 rule/ 下的 classical 列表转成 sing-box 规则集源文件（JSON，format: source）。

  rule/Foo.list  ->  rule/sing-box/Foo.json

sing-box 里这样引用：
  {"tag": "Foo", "type": "remote", "format": "source",
   "url": "https://raw.githubusercontent.com/rule2c/Customized_Rules/refs/heads/main/rule/sing-box/Foo.json"}

规则集版本用 2（sing-box 1.10+ 都能读）。
sing-box 没有对应项的规则（如 IP-ASN）跳过并打印 GitHub Actions 警告。
内容不变时不改写文件；sing-box/ 里没有对应 .list 的旧文件会被删除。
"""

import json
import sys
from pathlib import Path

VERSION = 2

# classical 规则类型 -> sing-box 无头规则字段
FIELDS = {
    "DOMAIN": "domain",
    "DOMAIN-SUFFIX": "domain_suffix",
    "DOMAIN-KEYWORD": "domain_keyword",
    "DOMAIN-REGEX": "domain_regex",
    "IP-CIDR": "ip_cidr",
    "IP-CIDR6": "ip_cidr",
    "SRC-IP-CIDR": "source_ip_cidr",
    "PROCESS-NAME": "process_name",
}
# 端口：单个值进 port / source_port，范围 a-b 进 *_port_range（写成 a:b）
PORT_FIELDS = {"DST-PORT": "port", "SRC-PORT": "source_port"}

# 输出字段顺序固定，便于 diff
ORDER = ["domain", "domain_suffix", "domain_keyword", "domain_regex", "source_ip_cidr", "ip_cidr",
         "source_port", "source_port_range", "port", "port_range", "process_name"]


def convert(path):
    rule, skipped = {}, []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            skipped.append(line)
            continue
        kind, value = parts[0].upper(), parts[1]
        if kind in FIELDS:
            key = FIELDS[kind]
        elif kind in PORT_FIELDS:
            key = PORT_FIELDS[kind]
            if "-" in value:
                key += "_range"
                value = value.replace("-", ":")
            else:
                value = int(value)
        else:
            skipped.append(line)
            continue
        values = rule.setdefault(key, [])
        if value not in values:
            values.append(value)
    rule = {k: rule[k] for k in ORDER if k in rule}
    return {"version": VERSION, "rules": [rule] if rule else []}, skipped


def main():
    root = Path(__file__).resolve().parent.parent / "rule"
    out_dir = root / "sing-box"
    out_dir.mkdir(exist_ok=True)

    wanted = set()
    for src in sorted(root.glob("*.list")):
        data, skipped = convert(src)
        for s in skipped:
            print(f"::warning::{src.name}: sing-box 不支持，已跳过: {s}")
        out = out_dir / f"{src.stem}.json"
        wanted.add(out.name)
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if out.exists() and out.read_text(encoding="utf-8") == text:
            print(f"{out.relative_to(root.parent)}: 无变化")
            continue
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"{out.relative_to(root.parent)}: 已更新")

    for old in out_dir.glob("*.json"):
        if old.name not in wanted:
            old.unlink()
            print(f"{old.relative_to(root.parent)}: 已删除（没有对应的 .list）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
