import json
import os
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
input_dir = os.path.join(PROJECT_ROOT, "Input", "fastp_json")
output_dir = os.path.join(PROJECT_ROOT, "Output", "read1_quality_curves")
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if not filename.endswith(".json"):
        continue

    sample_name = filename.replace(".json", "")
    json_path = os.path.join(input_dir, filename)

    with open(json_path, "r") as f:
        data = json.load(f)

    qc_read1 = data["read1_before_filtering"]["quality_curves"]

    positions = list(range(1, len(qc_read1["mean"]) + 1))

    plt.figure(figsize=(8, 5))

    plt.plot(positions, qc_read1["A"], label="A", linewidth=1)
    plt.plot(positions, qc_read1["T"], label="T", linewidth=1)
    plt.plot(positions, qc_read1["C"], label="C", linewidth=1)
    plt.plot(positions, qc_read1["G"], label="G", linewidth=1)
    plt.plot(positions, qc_read1["mean"], label="Mean", linewidth=2, linestyle="--")

    plt.xlabel("Position (cycle)")
    plt.ylabel("Quality score")
    plt.title(f"{sample_name} Read1 Quality Curve")
    plt.legend()
    plt.grid(alpha=0.3)

    out_png = os.path.join(
        output_dir, f"{sample_name}_read1_quality.png"
    )

    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

    # 修改这里：使用相对路径输出
    relative_path = os.path.relpath(out_png, PROJECT_ROOT)
    print(f"[OK] Saved: {relative_path}")


output_dir = os.path.join(PROJECT_ROOT, "Output", "read2_quality_curves")
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if not filename.endswith(".json"):
        continue

    sample_name = filename.replace(".json", "")
    json_path = os.path.join(input_dir, filename)

    with open(json_path, "r") as f:
        data = json.load(f)

    qc_read2 = data["read2_before_filtering"]["quality_curves"]

    positions = list(range(1, len(qc_read2["mean"]) + 1))

    plt.figure(figsize=(8, 5))

    plt.plot(positions, qc_read2["A"], label="A", linewidth=1)
    plt.plot(positions, qc_read2["T"], label="T", linewidth=1)
    plt.plot(positions, qc_read2["C"], label="C", linewidth=1)
    plt.plot(positions, qc_read2["G"], label="G", linewidth=1)
    plt.plot(positions, qc_read2["mean"], label="Mean", linewidth=2, linestyle="--")

    plt.xlabel("Position (cycle)")
    plt.ylabel("Quality score")
    plt.title(f"{sample_name} Read2 Quality Curve")
    plt.legend()
    plt.grid(alpha=0.3)

    out_png = os.path.join(
        output_dir, f"{sample_name}_read2_quality.png"
    )

    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

    # 修改这里：使用相对路径输出
    relative_path = os.path.relpath(out_png, PROJECT_ROOT)
    print(f"[OK] Saved: {relative_path}")