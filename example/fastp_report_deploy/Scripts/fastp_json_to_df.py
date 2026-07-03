#!/usr/bin/env python

import json, os
import pandas as pd

# fastp json 输入目录（先写死，后面再参数化）
JSON_DIR = "Input/fastp_json"

def parse_fastp_json(json_path):
    """
    读取单个 fastp json，返回一个 dict
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    before = summary.get("before_filtering", {})

    return before


def main():
    records = []

    for fname in os.listdir(JSON_DIR):
        if not fname.endswith(".json"):
            continue

        sample_name = os.path.splitext(fname)[0]
        json_path = os.path.join(JSON_DIR, fname)

        metrics = parse_fastp_json(json_path)
        metrics["sample"] = sample_name

        records.append(metrics)

    df = pd.DataFrame(records)

    # 把 sample 列放到第一列
    cols = ["sample"] + [c for c in df.columns if c != "sample"]
    df = df[cols]

    print(df)

    html_table = df.to_html(
        index=False,
        classes="mystyle",
        float_format="%.4f"
    )

    print("\n===== HTML TABLE =====\n")
    print(html_table)


if __name__ == "__main__":
    main()
