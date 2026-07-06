#!/usr/bin/env python
"""
Generate fastp base content distribution curves
Plot A/T/C/G/N/GC content curves for read1 and read2
Show average percentage in legend for A/T/C/G/N
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Input and output directories
input_dir = os.path.join(PROJECT_ROOT, "Input", "fastp_json")
output_dir_read1 = os.path.join(PROJECT_ROOT, "Output", "read1_content_curves")
output_dir_read2 = os.path.join(PROJECT_ROOT, "Output", "read2_content_curves")

# Create output directories
os.makedirs(output_dir_read1, exist_ok=True)
os.makedirs(output_dir_read2, exist_ok=True)

print("[INFO] Generating base content curves...")

def plot_base_content_curve(sample_name, content_data, read_type):
    """
    Plot base content distribution curve for a single sample and read type
    
    Parameters:
    - sample_name: sample identifier
    - content_data: dictionary with A/T/C/G/N/GC data
    - read_type: 'read1' or 'read2'
    """
    
    # Generate position sequence (1-based)
    positions = list(range(1, len(content_data["A"]) + 1))
    
    # Calculate average content for each base (percentage)
    avg_a = np.mean(content_data["A"]) * 100  # convert to percentage
    avg_t = np.mean(content_data["T"]) * 100
    avg_c = np.mean(content_data["C"]) * 100
    avg_g = np.mean(content_data["G"]) * 100
    avg_n = np.mean(content_data["N"]) * 100
    avg_gc = np.mean(content_data["GC"]) * 100
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 12))
    
    # ===== First subplot: A/T/C/G/N content =====
    ax1 = axes[0]
    
    # Plot A/T/C/G/N curves with average in legend
    line_a = ax1.plot(positions, content_data["A"], label=f"A ({avg_a:.1f}%)", 
                      color="#1f77b4", linewidth=2, marker='o', markersize=3)
    line_t = ax1.plot(positions, content_data["T"], label=f"T ({avg_t:.1f}%)", 
                      color="#ff7f0e", linewidth=2, marker='s', markersize=3)
    line_c = ax1.plot(positions, content_data["C"], label=f"C ({avg_c:.1f}%)", 
                      color="#2ca02c", linewidth=2, marker='^', markersize=3)
    line_g = ax1.plot(positions, content_data["G"], label=f"G ({avg_g:.1f}%)", 
                      color="#d62728", linewidth=2, marker='v', markersize=3)
    
    # Create secondary axis for N (N values are usually very small)
    ax1_n = ax1.twinx()
    line_n = ax1_n.plot(positions, content_data["N"], label=f"N ({avg_n:.3f}%)", 
                       color="#9467bd", linewidth=1.5, linestyle='--', marker='x', markersize=2)
    
    # Configure primary axis
    ax1.set_xlabel("Position (cycle)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Base Content (A/T/C/G)", fontsize=12, fontweight='bold')
    ax1.set_title(f"{sample_name} - {read_type.upper()} Base Content Distribution", 
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_ylim(0, 0.6)  # Set reasonable Y-axis range
    
    # Configure secondary axis (N)
    ax1_n.set_ylabel("N Content", fontsize=10, color='#9467bd')
    ax1_n.tick_params(axis='y', labelcolor='#9467bd')
    # N values are usually small, adjust range automatically
    n_max = max(content_data["N"])
    ax1_n.set_ylim(0, n_max * 2 if n_max > 0 else 0.00001)
    
    # Combine legends
    lines = line_a + line_t + line_c + line_g + line_n
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right', ncol=3, fontsize=9)
    
    # ===== Second subplot: GC content =====
    ax2 = axes[1]
    
    # Plot GC content curve (without percentage in label)
    ax2.plot(positions, content_data["GC"], label="GC Content", 
             color="#8c564b", linewidth=3, marker='D', markersize=4)
    
    # Add horizontal reference line (average GC content)
    ax2.axhline(y=avg_gc/100, color='r', linestyle='--', linewidth=1.5, 
                label=f'Average: {avg_gc:.1f}%')
    
    # Mark GC content range
    min_gc = min(content_data["GC"]) * 100  # convert to percentage for display
    max_gc = max(content_data["GC"]) * 100
    gc_range_percent = f"{min_gc:.1f}%-{max_gc:.1f}%"
    ax2.fill_between(positions, min(content_data["GC"]), max(content_data["GC"]), 
                     alpha=0.2, color='gray', label=f'Range: {gc_range_percent}')
    
    # Configure second subplot
    ax2.set_xlabel("Position (cycle)", fontsize=12, fontweight='bold')
    ax2.set_ylabel("GC Content", fontsize=12, fontweight='bold')
    ax2.set_title("GC Content Distribution", fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_ylim(0.3, 0.8)  # GC content range as per your modification
    ax2.legend(loc='best', fontsize=10)
    
    # Adjust layout
    plt.tight_layout()
    
    # Determine output directory based on read type
    if read_type == "read1":
        output_dir = output_dir_read1
        output_filename = f"{sample_name}_read1_content.png"
    else:
        output_dir = output_dir_read2
        output_filename = f"{sample_name}_read2_content.png"
    
    # Save image
    output_path = os.path.join(output_dir, output_filename)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Return relative path for logging
    relative_path = os.path.relpath(output_path, PROJECT_ROOT)
    return relative_path, avg_gc

# ============================
# Process read1 base content curves for all samples
# ============================
print("\nProcessing read1 content curves...")
read1_count = 0
read1_avg_gcs = []

for filename in os.listdir(input_dir):
    if not filename.endswith(".json"):
        continue

    sample_name = filename.replace(".json", "")
        # Strip the trailing "_fastp" suffix produced by run.sh so plot titles
        # (e.g. "sampleA - READ1 Base Content Distribution") and PNG filenames
        # (e.g. "sampleA_read1_content.png") use the clean sample name.
        if sample_name.endswith("_fastp"):
            sample_name = sample_name[:-len("_fastp")]
    json_path = os.path.join(input_dir, filename)

    with open(json_path, "r") as f:
        data = json.load(f)

    # Get read1 content_curves data
    if "read1_before_filtering" not in data or "content_curves" not in data["read1_before_filtering"]:
        print(f"  [WARNING] No content_curves found for {sample_name} read1")
        continue

    content_data = data["read1_before_filtering"]["content_curves"]
    relative_path, avg_gc = plot_base_content_curve(sample_name, content_data, "read1")
    
    print(f"  [OK] Saved: {relative_path} (Avg GC: {avg_gc:.1f}%)")
    read1_count += 1
    read1_avg_gcs.append(avg_gc)

if read1_count > 0:
    avg_gc_overall = np.mean(read1_avg_gcs)
    print(f"[SUCCESS] Generated {read1_count} read1 content curve images")
    print(f"  Average GC across all read1 samples: {avg_gc_overall:.1f}%")
else:
    print("[WARNING] No read1 content curves generated")

# ============================
# Process read2 base content curves for all samples
# ============================
print("\nProcessing read2 content curves...")
read2_count = 0
read2_avg_gcs = []

for filename in os.listdir(input_dir):
    if not filename.endswith(".json"):
        continue

    sample_name = filename.replace(".json", "")
        # Strip the trailing "_fastp" suffix produced by run.sh so plot titles
        # (e.g. "sampleA - READ1 Base Content Distribution") and PNG filenames
        # (e.g. "sampleA_read1_content.png") use the clean sample name.
        if sample_name.endswith("_fastp"):
            sample_name = sample_name[:-len("_fastp")]
    json_path = os.path.join(input_dir, filename)

    with open(json_path, "r") as f:
        data = json.load(f)

    # Get read2 content_curves data
    if "read2_before_filtering" not in data or "content_curves" not in data["read2_before_filtering"]:
        print(f"  [WARNING] No content_curves found for {sample_name} read2")
        continue

    content_data = data["read2_before_filtering"]["content_curves"]
    relative_path, avg_gc = plot_base_content_curve(sample_name, content_data, "read2")
    
    print(f"  [OK] Saved: {relative_path} (Avg GC: {avg_gc:.1f}%)")
    read2_count += 1
    read2_avg_gcs.append(avg_gc)

if read2_count > 0:
    avg_gc_overall = np.mean(read2_avg_gcs)
    print(f"[SUCCESS] Generated {read2_count} read2 content curve images")
    print(f"  Average GC across all read2 samples: {avg_gc_overall:.1f}%")
else:
    print("[WARNING] No read2 content curves generated")

# ============================
# Summary
# ============================
print("\n" + "="*50)
print("SUMMARY")
print("="*50)
print(f"Total JSON files processed: {len([f for f in os.listdir(input_dir) if f.endswith('.json')])}")
print(f"Read1 images generated: {read1_count}")
print(f"Read2 images generated: {read2_count}")
print(f"Output directories:")
print(f"  Read1: {os.path.relpath(output_dir_read1, PROJECT_ROOT)}")
print(f"  Read2: {os.path.relpath(output_dir_read2, PROJECT_ROOT)}")
print("="*50)