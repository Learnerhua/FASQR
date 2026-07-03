#!/usr/bin/env python

import subprocess
import os
import yaml
import argparse


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Convert HTML report to PDF using wkhtmltopdf"
    )
    parser.add_argument(
        "-c", "--config", required=True,
        help="Path to report.yaml"
    )
    args = parser.parse_args()

    config = load_config(args.config)

    html_in = config["output"]["html"]
    pdf_out = config["output"]["pdf"]

    os.makedirs(os.path.dirname(pdf_out), exist_ok=True)

    cmd = [
        "wkhtmltopdf",
        "--enable-local-file-access",
        "--print-media-type",
        "--outline",
        "--outline-depth", "3",
        "--encoding", "utf-8",
        "--page-size", "A4",
        "--margin-top", "15mm",
        "--margin-bottom", "15mm",
        "--margin-left", "10mm",
        "--margin-right", "10mm",
        
        html_in,
        pdf_out
    ]

    print("[INFO] Running wkhtmltopdf...")
    subprocess.run(cmd, check=True)

    print(f"[OK] PDF report generated: {pdf_out}")


if __name__ == "__main__":
    main()