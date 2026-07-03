#!/usr/bin/env python

import os, json, yaml, argparse
import pandas as pd
from jinja2 import Environment, FileSystemLoader


def parse_fastp_json(json_path):
    """读取单个 fastp json，返回 before_filtering 指标"""
    with open(json_path, "r") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    before = summary.get("before_filtering", {})
    return before

def format_dataframe(df):
    """
    对 fastp summary DataFrame 进行展示级格式化
    """

    # 1. 整数列：加千分位
    int_cols = [
        "total_reads",
        "total_bases",
        "q20_bases",
        "q30_bases"
    ]

    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda x: f"{int(x):,}")

    # 2. 比例列：转百分数
    rate_cols = [
        "q20_rate",
        "q30_rate",
        "gc_content"
    ]

    for col in rate_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda x: f"{x * 100:.2f}")

            # 同时修改列名，加 (%)
            df.rename(columns={col: f"{col} (%)"}, inplace=True)

    return df



def build_dataframe(json_dir):
    """读取目录下所有 json，合并成 DataFrame"""
    records = []

    for fname in os.listdir(json_dir):
        if not fname.endswith(".json"):
            continue

        sample = os.path.splitext(fname)[0]
        json_path = os.path.join(json_dir, fname)

        metrics = parse_fastp_json(json_path)
        metrics["sample"] = sample
        records.append(metrics)

    df = pd.DataFrame(records)
    cols = ["sample"] + [c for c in df.columns if c != "sample"]
    return df[cols]


def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render fastp QC HTML report"
    )
    parser.add_argument(
        "-c", "--config", required=True,
        help="Path to report.yaml"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config = load_config(args.config)
    json_dir = config["input"]["fastp_json_dir"]
    output_html = config["output"]["html"]

    # 1. JSON → DataFrame
    df = build_dataframe(json_dir)
    df = format_dataframe(df)

    # 2. DataFrame → HTML 表格
    table_html = df.to_html(
        index=False,
        classes="mystyle",
        float_format="%.4f"
    )
    # 2.1 收集 read1 碱基质量曲线图片
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    read1_img_dir = os.path.join(project_root, "Output", "read1_quality_curves")
    read1_quality_images = []
    if os.path.isdir(read1_img_dir):
        for fname in sorted(os.listdir(read1_img_dir)):
            if fname.endswith("_read1_quality.png"):
                sample = fname.replace("_read1_quality.png", "")
                read1_quality_images.append({
                    "sample": sample,
                    "img_path": os.path.join(
                        "../../Output/read1_quality_curves", fname
                    )
                })
    # 2.2 收集 read2 碱基质量曲线图片
    read2_img_dir = os.path.join(project_root, "Output", "read2_quality_curves")
    read2_quality_images = []
    if os.path.isdir(read2_img_dir):
        for fname in sorted(os.listdir(read2_img_dir)):
            if fname.endswith("_read2_quality.png"):
                sample = fname.replace("_read2_quality.png", "")
                read2_quality_images.append({
                    "sample": sample,
                    "img_path": os.path.join(
                        "../../Output/read2_quality_curves", fname
                    )
                })

    # 2.3 收集 read1 碱基含量曲线图片
    read1_content_dir = os.path.join(project_root, "Output", "read1_content_curves")
    read1_content_images = []
    if os.path.isdir(read1_content_dir):
        for fname in sorted(os.listdir(read1_content_dir)):
            if fname.endswith("_read1_content.png"):
                sample = fname.replace("_read1_content.png", "")
                read1_content_images.append({
                    "sample": sample,
                    "img_path": os.path.join(
                        "../../Output/read1_content_curves", fname
                    )
                })

    # 2.4 收集 read2 碱基含量曲线图片
    read2_content_dir = os.path.join(project_root, "Output", "read2_content_curves")
    read2_content_images = []
    if os.path.isdir(read2_content_dir):
        for fname in sorted(os.listdir(read2_content_dir)):
            if fname.endswith("_read2_content.png"):
                sample = fname.replace("_read2_content.png", "")
                read2_content_images.append({
                    "sample": sample,
                    "img_path": os.path.join(
                        "../../Output/read2_content_curves", fname
                    )
                })

    # 3. 加载模板
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("fastp_summary.html")

        # 4. 渲染 HTML
    html_out = template.render(
        table_html=table_html,
        project=config["project"],
        read1_quality_images=read1_quality_images,
        read2_quality_images=read2_quality_images,
        read1_content_images=read1_content_images,
        read2_content_images=read2_content_images
    )

    # 5. 写出 HTML
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[OK] HTML report generated: {output_html}")

if __name__ == "__main__":
    main()
