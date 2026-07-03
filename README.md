# FASQR

**FASQR** — **F**astp **A**utomated **S**equencing **Q**uality **R**eport

Automated quality report generation for paired-end FASTQ sequencing data, powered by [fastp](https://github.com/OpenGene/fastp).

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org)
[![Bash 4.0+](https://img.shields.io/badge/Bash-4.0%2B-4EAA25.svg?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-FCC624.svg?logo=linux&logoColor=black)](https://www.kernel.org)
[![Powered by fastp](https://img.shields.io/badge/Powered%20by-fastp-00A1DE.svg)](https://github.com/OpenGene/fastp)

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet?logo=anthropic&logoColor=white)](https://claude.ai/code)
[![AgentSkills Standard](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)
[![Agent Ready](https://img.shields.io/badge/Agent-Ready-orange.svg)](#-usage)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](#)

</div>

A two-tier pipeline that runs parallel QC on raw reads and produces a polished HTML/PDF **quality report** with quality curves, base-content curves, and a per-sample summary table. Designed to be driven by an **AI coding agent** through the bundled `SKILL.md`, while remaining fully runnable from the command line.

## Overview

FASQR is an end-to-end solution for short-read sequencing **quality reporting**. The outer layer runs `fastp` in parallel across samples via GNU `parallel` to produce raw QC metrics; the inner layer consumes the resulting JSON files and turns them into per-sample quality / base-content plots, a multi-section HTML report, and a polished PDF report with cover page, table of contents, header/footer, and clickable outline. Suitable for WGS, RNA-seq, WES, metagenomics, and any paired-end Illumina sequencing dataset.

### Key Features

- **Agent-ready Design**: Ships with a `SKILL.md` so an AI coding agent (Claude Code, Trae, Cursor, etc.) can drive the full pipeline — environment check, parameter confirmation, project-metadata validation, execution, and error recovery
- **Parallel QC Execution**: GNU `parallel`-driven `fastp` runs across samples concurrently; thread count is configurable per sample
- **Standard Adapter / PolyG Trimming**: Built-in adapter auto-detection, polyG tail removal (for two-color chemistry), N-tail trimming, and length filtering (`-A -G -Q -L`)
- **Per-sample Quality Curves**: Phred quality score distribution for read1 and read2, A/T/C/G + N curves
- **Per-sample Base-content Curves**: A/T/C/G/N and GC content curves with range highlighting and average markers
- **Multi-section HTML Report**: Project info, summary table, embedded quality / content plots for every sample
- **Polished PDF Report**: Chromium-rendered PDF with cover page, TOC, header logo, footer with page numbers, and a clickable bookmark tree
- **Self-contained Single-file HTML**: Base64-embedded CSS and images, shareable without external dependencies
- **Project Metadata Customization**: Single YAML file drives project ID, name, description, author, date, and header/footer styling


## Pipeline Architecture

The pipeline consists of two cooperating layers:

### Outer layer — `run.sh`

| Step | Component          | Function                                |
| ---- | ------------------ | --------------------------------------- |
| 1    | `command -v` checks | Verify `fastp` and GNU `parallel` in PATH |
| 2    | argument parsing   | Parse `-i / -o / -w / -r`               |
| 3    | `GNU parallel`     | Run `fastp` for all R1 files concurrently |
| 4    | JSON collection    | Copy all `*_fastp.json` to report dir   |
| 5    | inner trigger      | `cd` into report dir and invoke `run_fastp_report.sh` |

### Inner layer — `fastp_report_deploy/run_fastp_report.sh`

| Step | Script                          | Function                                |
| ---- | ------------------------------- | --------------------------------------- |
| 0    | `Scripts/env_check.py`          | Verify Python dependencies              |
| 1    | `Scripts/plot_quality_curves.py`| Per-sample read1 / read2 quality PNGs   |
| 2    | `Scripts/plot_content_curves.py`| Per-sample read1 / read2 base-content PNGs |
| 3    | `Scripts/render_fastp_html.py`  | Aggregate JSONs into a DataFrame, render Jinja2 HTML |
| 4    | `Scripts/html_to_pdf_playwright.py` | Chromium renders PDF; PyPDF2 merges cover + TOC + main report |
| 5    | `Scripts/generate_single_html.py` | Base64-embed CSS and images into a single HTML file |
| 6    | shell reorganization            | Copy / rename to `report/QC_report.{html,pdf}` |
| 7    | shell verification              | Print final directory tree and file sizes |

## Requirements

### Required System Tools

- **fastp** (v0.20+) — ultra-fast FASTQ preprocessor
- **GNU parallel** — concurrent job scheduler
- **Python** (v3.6+) — report-generation glue
- **Chromium** (installed by Playwright) — PDF rendering engine
- **Noto Sans CJK SC** or **Microsoft YaHei** — required for Chinese text in PDF

### Required Python Packages

```bash
pip install pyyaml matplotlib numpy pandas jinja2 playwright pypdf2
playwright install chromium
```

### Input Data Convention

- Paired-end FASTQ files named `*_R1*.fq.gz` / `*_R2*.fq.gz`
- The sample name is extracted as `basename $r1 | sed 's/_R1.*//'`
- Renaming files (e.g. `*.R1.fq.gz`) requires updating `run.sh:108-109`

## Installation

### Option 1: Using Conda (Recommended)

```bash
# Create environment and install system tools
conda create -n fastp_pipeline python=3.10
conda activate fastp_pipeline
conda install -c bioconda fastp parallel

# Install Python packages
pip install pyyaml matplotlib numpy pandas jinja2 playwright pypdf2
playwright install chromium
```

### Option 2: Manual Installation

Please refer to official documentation for each tool:

- fastp: <https://github.com/OpenGene/fastp>
- GNU parallel: <https://www.gnu.org/software/parallel/>
- Playwright: <https://playwright.dev/python/docs/intro>

### Playwright System Dependencies (Linux)

If Chromium fails to start with missing-shared-library errors, install the system libraries:

```bash
sudo bash fastp_report_deploy/Help/install_playwright_deps.sh
```

## Custom Assets (User-provided)

FASQR ships with **placeholder** branding assets that you **must replace** with your own before generating client-facing reports. The pipeline will run fine without replacing them, but the report header, cover page, and footer will still show the original owner's branding.

### 1. Company Logo (Header / Single-file HTML)

| Property | Default placeholder                  | What to replace it with                                  |
| -------- | ----------------------------------- | -------------------------------------------------------- |
| Path     | `fastp_report_deploy/assets/images/logo.png` | Your own company / project logo, **≥ 600 px wide**, transparent PNG preferred |

This logo is rendered in the **PDF report header** (left side, height 25 px) and embedded into the single-file HTML report. The `pdf_header_footer.header.logo` field in `report.yaml` controls the path.

If you do not need a logo, set `pdf_header_footer.header.enabled: false` in `report.yaml` to suppress it.

### 2. PDF Cover Page

| Property | Default placeholder                              | What to replace it with                                  |
| -------- | ------------------------------------------------ | -------------------------------------------------------- |
| Path     | `fastp_report_deploy/templates/pdf_cover.pdf` | A **single-page A4 PDF** with your own cover design     |

This PDF is prepended to every generated `QC_report.pdf`. Design constraints:

- **Format**: single-page A4 (210 × 297 mm) PDF
- **Content suggestions**: company logo, project name, project ID, date, version, confidentiality notice
- **Multi-page is not supported** — only the first page is used
- If the file is missing, the report will still be generated but **without a cover** (a warning is printed)

If you do not need a cover, omit `--with-cover` when running `Scripts/html_to_pdf_playwright.py` (or have your agent skip it).

### 3. Circular Logo (Optional)

| Property      | Default placeholder                                  | Purpose                       |
| ------------- | ---------------------------------------------------- | ----------------------------- |
| Path          | `fastp_report_deploy/assets/images/KMHD_logo_circle.png` | Currently unused by the pipeline, kept for future use |

You can ignore this file — it is reserved for future extensions and not referenced anywhere in the current code.

### Verification

After replacing the assets, run a quick sanity check before kicking off a full pipeline run:

```bash
# Confirm the new files are in place
ls -la fastp_report_deploy/assets/images/logo.png
ls -la fastp_report_deploy/templates/pdf_cover.pdf

# Confirm both are valid (logo: PNG header; cover: PDF header)
file fastp_report_deploy/assets/images/logo.png
file fastp_report_deploy/templates/pdf_cover.pdf
```

If either file is missing or malformed, `run_fastp_report.sh` will either skip that part of the report (with a warning) or fail with a clear error message — never silently produce an incomplete report.

## Usage

FASQR supports two execution modes: **Agent-driven Execution (Recommended)** and **Manual Step-by-step Execution**. Most users should start with Mode 1.

---

### Mode 1 — Agent-driven Execution (Recommended)

Run the pipeline by instructing an AI coding agent that understands the bundled `SKILL.md`. This is the recommended path: the agent will validate the environment, walk you through every parameter, confirm the project metadata, and only then execute.

#### Supported Agents

Any agent that can read `SKILL.md` and execute shell commands works. Tested / confirmed:

- **Claude Code** (CLI / IDE) — `claude` command
- **Trae IDE** — built-in AI assistant
- **Cursor** — Composer / Agent mode

#### Setup

1. Place the entire `fastp_pipeline_SOP/` directory under your agent's working directory.
2. Make sure `.claude/skills/fastp-pipeline/SKILL.md` is reachable by the agent (project-level skills are auto-discovered).
3. Activate the conda / venv environment where `fastp` and the Python dependencies are installed.

#### Run

Open the project directory in the agent and issue a natural-language request. The agent will load `SKILL.md` and follow its rules (environment check → parameter confirmation → metadata confirmation → execution).

**Example prompts** the agent understands:

```
Run the full QC pipeline on /data/sampleA_*.fq.gz and /data/sampleB_*.fq.gz.
```

```
I already have fastp JSONs in fastp_report_deploy/Input/fastp_json/ — just generate the report.
```

```
Re-render only the PDF report with cover and TOC.
```

```
Change project ID to KM-XS-2601-099 and project name to "水稻抗病 GWAS" in report.yaml.
```

#### What the Agent Does (and Does Not Do)

| Action | Agent | You |
|---|---|---|
| Detect `fastp` / `parallel` / Python packages | ✅ read-only check | — |
| Ask which conda / venv / SSH / Docker to use | ✅ | confirm / supply |
| Walk through every `run.sh` parameter (`-i / -o / -w / -r`) and explain it | ✅ | confirm values |
| Validate `report.yaml` project metadata and the `project.ID` ↔ `header.right_text` linkage | ✅ read-only check | edit `report.yaml` in your own editor |
| Verify `assets/images/logo.png` and `templates/pdf_cover.pdf` exist before report generation | ✅ read-only check | replace placeholder assets with your own |
| Run `run.sh` / `run_fastp_report.sh` / single Python step | ✅ | — |
| Install missing packages (`pip install` / `apt install` / `playwright install`) | ❌ never | install yourself, then tell the agent to retry |
| Replace logo / cover PDF / edit `report.yaml` / source code | ❌ never | edit in your own editor |

> 🔒 The agent **never** installs software, never edits `report.yaml` or source code, never replaces the logo / cover PDF, and never executes without your explicit confirmation on each parameter. It only reads files, asks questions, and runs commands you approved.

---

### Mode 2 — Manual Step-by-step Execution

If you prefer to run the pipeline yourself or are integrating it into a larger workflow, follow the steps below.

#### Quick Start — Run the Full Pipeline

From the project root (`fastp_pipeline_SOP/`):

```bash
./run.sh -i <FASTQ_DIR> -o <FASTP_OUT_DIR> -w 4 -r fastp_report_deploy
```

| Parameter | Required | Default      | Description                                                  |
| --------- | -------- | ------------ | ------------------------------------------------------------ |
| `-i`      | Yes      | —            | FASTQ directory; must contain `*_R1*.fq.gz`                  |
| `-o`      | No       | `.`          | Output directory for `*_fastp.{html,json}`                   |
| `-w`      | No       | `4`          | Threads per sample (sample-level concurrency uses GNU `parallel`) |
| `-r`      | No       | (disabled)   | Report directory; set to `fastp_report_deploy` to trigger the inner pipeline |

#### Generate Reports from Existing JSONs

If `*_fastp.json` files are already available, drop them into `fastp_report_deploy/Input/fastp_json/` and run only the inner pipeline:

```bash
cp your_data/*_fastp.json fastp_report_deploy/Input/fastp_json/
cd fastp_report_deploy
./run_fastp_report.sh
```

#### Customize Project Metadata

Edit `fastp_report_deploy/config/report.yaml`:

```yaml
project:
  ID: KM-XS-2508-005
  name: <Project name>
  description: <Project description>
  author: <Department / person>
  date: 2026-01-08

pdf_header_footer:
  header:
    logo: assets/images/logo.png
    right_text: "QC report | Project: KM-XS-2508-005"
  footer:
    text: "<Company name> | <URL>"
    show_page_numbers: true
```

> Note: when changing `project.ID`, also update `pdf_header_footer.header.right_text` since the project ID is hard-coded there.
>
> 📦 **Branding assets** (company logo / PDF cover) are configured in the "Custom Assets (User-provided)" section above — replace `assets/images/logo.png` and `templates/pdf_cover.pdf` with your own before running on client data.

#### Single-step Debugging

Each Python script can be run independently:

```bash
# 0. Environment check
python3 fastp_report_deploy/Scripts/env_check.py

# 1. Quality curves only
python  fastp_report_deploy/Scripts/plot_quality_curves.py

# 2. Base-content curves only
python  fastp_report_deploy/Scripts/plot_content_curves.py

# 3. Re-render HTML
python  fastp_report_deploy/Scripts/render_fastp_html.py \
        --config fastp_report_deploy/config/report.yaml

# 4. Re-render PDF (with cover + TOC)
python  fastp_report_deploy/Scripts/html_to_pdf_playwright.py \
        --config fastp_report_deploy/config/report.yaml \
        --with-toc --with-cover

# 5. Re-pack single-file HTML
python  fastp_report_deploy/Scripts/generate_single_html.py
```
## Output Files

After pipeline completion, the following files are generated:

| Path                                                       | Description                                  |
| ---------------------------------------------------------- | -------------------------------------------- |
| `<output_dir>/*_fastp.json`                                | Per-sample fastp JSON report                 |
| `<output_dir>/*_fastp.html`                                | Per-sample fastp HTML report                 |
| `fastp_report_deploy/Output/read1_quality_curves/*.png`    | read1 Phred quality curves                   |
| `fastp_report_deploy/Output/read2_quality_curves/*.png`    | read2 Phred quality curves                   |
| `fastp_report_deploy/Output/read1_content_curves/*.png`    | read1 base-content curves                    |
| `fastp_report_deploy/Output/read2_content_curves/*.png`    | read2 base-content curves                    |
| `fastp_report_deploy/Output/html/fastp_qc_summary.html`    | Multi-section HTML report                    |
| `fastp_report_deploy/Output/html/fastp_qc_single_file.html`| Self-contained HTML with embedded resources  |
| `fastp_report_deploy/Output/pdf/fastp_qc_summary.pdf`      | PDF report with cover, TOC, header, footer   |
| `fastp_report_deploy/report/QC_report.html`                | Final deliverable — single-file HTML         |
| `fastp_report_deploy/report/QC_report.pdf`                 | Final deliverable — PDF                      |
| `fastp_report_deploy/report/rawData/`                      | Placeholder for raw data archive             |

## Report Structure

The HTML / PDF report contains six main sections:

1. **Project Information** — Project ID, name, description, author, date
2. **Sequencing Quality Statistics** — Per-sample summary table (total reads, total bases, Q20 / Q30 bases and rates, GC content)
3. **Read1 Base-quality Distribution** — Quality curves for every sample
4. **Read2 Base-quality Distribution** — Quality curves for every sample
5. **Read1 Base-content Distribution** — A/T/C/G/N and GC content curves
6. **Read2 Base-content Distribution** — A/T/C/G/N and GC content curves

The PDF additionally includes: cover page, table of contents (with page numbers from the rendered outline), and a bookmark tree for navigation.

## Example

### Input Example

```bash
./run.sh \
    -i /data/sampleA_R1.fq.gz /data/sampleA_R2.fq.gz \
        /data/sampleB_R1.fq.gz /data/sampleB_R2.fq.gz \
    -o /data/fastp_out \
    -w 8 \
    -r fastp_report_deploy
```

### Expected Result Structure

```
fastp_report_deploy/report/
├── QC_report.html        # Self-contained HTML (~5-20 MB depending on sample count)
├── QC_report.pdf         # Polished PDF with cover + TOC + outline
└── rawData/              # Empty placeholder
```

## Notes

1. **No Cleaned FASTQ Output**: The default `run.sh` discards cleaned reads (`-o /dev/null -O /tmp/null.fastq`). Modify `run.sh:113-118` if you need to keep them.
2. **Sample-naming Convention**: Changing the FASTQ naming convention (e.g. removing `_R1` / using `.R1.fq.gz`) requires updating the regex in `run.sh:108-109`.
3. **Chinese Fonts in PDF**: Install `Noto Sans CJK SC` or `Microsoft YaHei` on the rendering host; otherwise Chinese characters render as boxes.
4. **Resource Planning**: Each `fastp` process pre-allocates buffers proportional to `-w` threads; running many samples at `-w 8+` on a small machine can cause OOM.
5. **Two PDF Scripts**: `Scripts/html_to_pdf.py` (wkhtmltopdf-based, deprecated) is kept for historical reference only; `run_fastp_report.sh` invokes `Scripts/html_to_pdf_playwright.py` (Playwright + Chromium).
6. **Temporary Files**: `temp_main.pdf` / `temp_toc.pdf` are intermediate artifacts cleaned up automatically; do not delete or rename them while the pipeline is running.
7. **Disk Space**: A 100-sample RNA-seq run typically produces 1-3 GB of intermediate PNGs plus a 50-200 MB PDF; ensure sufficient disk space.
8. **Replace Branding Assets Before Client Delivery**: The shipped `assets/images/logo.png` and `templates/pdf_cover.pdf` are **placeholders belonging to the original author**. Replace them with your own company logo and cover PDF before generating any client-facing report — see "Custom Assets (User-provided)" section above.

## Project Structure

```
fastp_pipeline_SOP/
├── run.sh                                # Outer pipeline entry
├── README.md                             # This file
└── fastp_report_deploy/                  # Inner report pipeline (self-contained)
    ├── run_fastp_report.sh               # 7-step orchestrator
    ├── config/report.yaml                # Project metadata + paths + PDF header/footer
    ├── templates/
    │   ├── fastp_summary.html            # Jinja2 template
    │   └── pdf_cover.pdf            # PDF cover page
    ├── assets/
    │   ├── css/mystyle.css               # Stylesheet (inlined into single-file HTML)
    │   └── images/{logo,KMHD_logo_circle}.png
    ├── Input/fastp_json/                 # JSON landing zone
    ├── Scripts/                          # All Python steps
    └── report/                           # Final deliverables (created on run)
```

## Contact

For questions or suggestions, please submit an Issue or Pull Request.

**Email**: oyjh417701@163.com

## Copyright

Copyright (c) 2026 OYJH

All Rights Reserved.

## License

MIT License

## Acknowledgments

This pipeline integrates the following excellent open-source tools:

- [fastp](https://github.com/OpenGene/fastp) — Ultra-fast FASTQ preprocessor
- [GNU parallel](https://www.gnu.org/software/parallel/) — Concurrent job scheduler
- [Playwright](https://playwright.dev/) — Chromium automation for PDF rendering
- [PyPDF2](https://github.com/py-pdf/pypdf) — PDF manipulation and bookmark rebuild
- [matplotlib](https://matplotlib.org/) — Quality and base-content curves
- [Jinja2](https://jinja.palletsprojects.com/) — HTML templating

<br />

<br />