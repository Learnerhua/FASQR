#!/usr/bin/env bash
set -euo pipefail

#######################################
# Fastp QC Report Pipeline
# Author: OYJH
# Date: 2026-01
#######################################

echo "========================================"
echo "🚀 Fastp QC Report Pipeline"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$ROOT_DIR/config/report.yaml"

# 脚本路径
PLOT_QC="$ROOT_DIR/Scripts/plot_quality_curves.py"
PLOT_CONTENT="$ROOT_DIR/Scripts/plot_content_curves.py"
RENDER_HTML="$ROOT_DIR/Scripts/render_fastp_html.py"
HTML_TO_PDF="$ROOT_DIR/Scripts/html_to_pdf_playwright.py"
GENERATE_SINGLE="$ROOT_DIR/Scripts/generate_single_html.py"
ENV_CHECK="$ROOT_DIR/Scripts/env_check.py"

# 报告输出目录
REPORT_DIR="$ROOT_DIR/report"
RAW_DATA_DIR="$REPORT_DIR/rawData"

#######################################
# Step 0: 检查环境依赖
#######################################
echo ""
echo "[STEP 0] 检查环境依赖..."
echo "----------------------------------------"

# 检查 env_check.py 是否存在
if [ ! -f "$ENV_CHECK" ]; then
    echo "[ERROR] 环境检查脚本不存在: $ENV_CHECK"
    echo "请确保 env_check.py 在 Scripts/ 目录中"
    exit 1
fi

echo "运行环境检查脚本..."
python3 "$ENV_CHECK"
CHECK_RESULT=$?

if [ $CHECK_RESULT -ne 0 ]; then
    echo "[ERROR] 环境检查失败，请先解决上述问题"
    exit 1
fi

echo "✓ 环境检查通过"
echo "----------------------------------------"

#######################################
# Step 1: 生成质量曲线 (phred分数)
#######################################
echo ""
echo "[STEP 1] 生成质量曲线 (phred分数)..."
echo "----------------------------------------"
python "$PLOT_QC"
if [ $? -eq 0 ]; then
    echo "✓ 质量曲线生成成功"
else
    echo "[ERROR] 质量曲线生成失败"
    exit 1
fi
echo "----------------------------------------"

#######################################
# Step 2: 生成碱基含量曲线
#######################################
echo ""
echo "[STEP 2] 生成碱基含量曲线..."
echo "----------------------------------------"
python "$PLOT_CONTENT"
if [ $? -eq 0 ]; then
    echo "✓ 碱基含量曲线生成成功"
else
    echo "[ERROR] 碱基含量曲线生成失败"
    exit 1
fi
echo "----------------------------------------"

#######################################
# Step 3: 渲染HTML报告
#######################################
echo ""
echo "[STEP 3] 渲染HTML报告..."
echo "----------------------------------------"
python "$RENDER_HTML" --config "$CONFIG"
if [ $? -eq 0 ]; then
    echo "✓ HTML报告生成成功"
else
    echo "[ERROR] HTML报告生成失败"
    exit 1
fi
echo "----------------------------------------"

#######################################
# Step 4: 转换HTML为PDF
#######################################
echo ""
echo "[STEP 4] 转换HTML为PDF..."
echo "----------------------------------------"
python "$HTML_TO_PDF" --config "$CONFIG" --with-toc --with-cover
if [ $? -eq 0 ]; then
    echo "✓ PDF报告生成成功"
else
    echo "[ERROR] PDF报告生成失败"
    exit 1
fi
echo "----------------------------------------"

#######################################
# Step 5: 生成单文件HTML报告
#######################################
echo ""
echo "[STEP 5] 生成单文件HTML报告..."
echo "----------------------------------------"
python "$GENERATE_SINGLE"
if [ $? -eq 0 ]; then
    echo "✓ 单文件HTML报告生成成功"
else
    echo "[ERROR] 单文件HTML报告生成失败"
    exit 1
fi
echo "----------------------------------------"

#######################################
# Step 6: 整理最终报告
#######################################
echo ""
echo "[STEP 6] 整理最终报告..."
echo "----------------------------------------"

# 清理并创建报告目录
echo "  创建报告目录结构..."
rm -rf "$REPORT_DIR" 2>/dev/null || true
mkdir -p "$REPORT_DIR"
mkdir -p "$RAW_DATA_DIR"

# 复制并重命名报告文件
echo "  复制和重命名报告文件..."

# 复制单文件HTML报告
SINGLE_HTML_SOURCE="$ROOT_DIR/Output/html/fastp_qc_single_file.html"
if [ -f "$SINGLE_HTML_SOURCE" ]; then
    cp "$SINGLE_HTML_SOURCE" "$REPORT_DIR/QC_report.html"
    echo "    ✓ QC_report.html (来源: fastp_qc_single_file.html)"
else
    echo "    [ERROR] 未找到单文件HTML: $SINGLE_HTML_SOURCE"
    exit 1
fi

# 复制PDF报告
PDF_SOURCE="$ROOT_DIR/Output/pdf/fastp_qc_summary.pdf"
if [ -f "$PDF_SOURCE" ]; then
    cp "$PDF_SOURCE" "$REPORT_DIR/QC_report.pdf"
    echo "    ✓ QC_report.pdf (来源: fastp_qc_summary.pdf)"
else
    echo "    [ERROR] 未找到PDF报告: $PDF_SOURCE"
    exit 1
fi

# 创建空的rawData目录
echo "    ✓ rawData/ (创建空目录)"

echo "✓ 最终报告整理完成"
echo "----------------------------------------"

#######################################
# Step 7: 验证最终输出
#######################################
echo ""
echo "[STEP 7] 验证最终输出..."
echo "----------------------------------------"

echo ""
echo "  📁 最终报告目录结构:"
echo "    report/"
echo "    ├── QC_report.html"
echo "    ├── QC_report.pdf"
echo "    └── rawData/"
echo ""

echo "  📊 文件大小:"
if [ -f "$REPORT_DIR/QC_report.html" ]; then
    html_size=$(du -h "$REPORT_DIR/QC_report.html" | cut -f1)
    echo "    • QC_report.html: $html_size"
fi

if [ -f "$REPORT_DIR/QC_report.pdf" ]; then
    pdf_size=$(du -h "$REPORT_DIR/QC_report.pdf" | cut -f1)
    echo "    • QC_report.pdf: $pdf_size"
fi

echo ""
echo "✓ 最终输出验证完成"
echo "----------------------------------------"

#######################################
# 完成
#######################################
echo ""
echo "========================================"
echo "🎉 FASTP QC 报告流程完成!"
echo "========================================"
