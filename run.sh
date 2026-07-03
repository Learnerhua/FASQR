#!/bin/bash
# run_fastp.sh
# Purpose: Run fastp in parallel for paired-end FASTQ files
# -i required: input directory
# -o optional: output directory, default current directory
# -w optional: threads per sample, default 4
# -r optional: report directory, used to copy JSON files

set -euo pipefail

# -----------------------
# Colors and logging functions
# -----------------------
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

log_info()    { echo -e "${CYAN}[$(date +'%H:%M:%S')] [INFO]${RESET} $*"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] [SUCCESS]${RESET} $*"; }
log_warn()    { echo -e "${YELLOW}[$(date +'%H:%M:%S')] [WARNING]${RESET} $*"; }
log_error()   { echo -e "${RED}[$(date +'%H:%M:%S')] [ERROR]${RESET} $*"; }

# -----------------------
# Check required programs
# -----------------------
command -v fastp >/dev/null 2>&1 || { log_error "fastp is not installed or not in PATH. Exiting."; exit 1; }
command -v parallel >/dev/null 2>&1 || { log_error "GNU parallel is not installed or not in PATH. Exiting."; exit 1; }

# -----------------------
# Parse arguments
# -----------------------
usage() {
    log_info "Usage: $0 -i <input_dir> [-o <output_dir>] [-w <threads_per_sample>] [-r <report_dir>]"
    echo "  -i: input FASTQ directory (required, must contain paired-end sequencing data)"
    echo "  -o: output directory for fastp analysis results (default: current directory)"
    echo "  -w: threads per sample (default: 4)"
    echo "  -r: report directory (optional)"
    exit 1
}

input_dir=""
output_dir="."       # default current directory
threads_per_sample=4 # default threads
report_dir=""

while getopts "i:o:w:r:" opt; do
    case $opt in
        i) input_dir="$OPTARG" ;;
        o) output_dir="$OPTARG" ;;
        w) threads_per_sample="$OPTARG" ;;
        r) report_dir="$OPTARG" ;;
        *) usage ;;
    esac
done

if [[ -z "$input_dir" ]]; then
    log_error "Input directory must be specified with -i"
    usage
fi

mkdir -p "$output_dir"

# -----------------------
# Banner display
# -----------------------
echo
echo "==============================================================="
echo "======================== QC Analysis =========================="
echo
echo "Current time       : $(date '+%Y-%m-%d %H:%M:%S.%6N')"
echo "Operation system   : $(uname -s | tr '[:upper:]' '[:lower:]')"
echo "Platform           : $(uname -m)-conda-$(uname -s | tr '[:upper:]' '[:lower:]')"
echo "Working directory  : $(pwd)"
echo "Output directory   : $output_dir"
echo "Report directory   : ${report_dir:-None}"
echo "Copyright © $(date +%Y) oyjh. All Rights Reserved."
echo
echo "==============================================================="
echo

# -----------------------
# Find R1 files
# -----------------------
shopt -s nullglob
r1_files=("$input_dir"/*_R1*.fq.gz)
shopt -u nullglob

if [[ ${#r1_files[@]} -eq 0 ]]; then
    log_error "No R1 files found in '$input_dir', please check the input directory"
    exit 1
fi

log_info "Found ${#r1_files[@]} samples in $input_dir"

# -----------------------
# fastp execution function
# -----------------------
run_fastp() {
    GREEN="\033[1;32m"
    CYAN="\033[1;36m"
    RESET="\033[0m"

    log_info() { echo -e "${CYAN}[$(date +'%H:%M:%S')] [INFO]${RESET} $*"; }

    local r1="$1"
    local r2="${r1/_R1/_R2}"
    local sample=$(basename "$r1" | sed 's/_R1.*//')

    log_info "Starting sample $sample ..."

    fastp \
        -i "$r1" \
        -I "$r2" \
        -o /dev/null \
        -O /tmp/null.fastq \
        -h "$output_dir/${sample}_fastp.html" \
        -j "$output_dir/${sample}_fastp.json" \
        -R "${sample} fastp report" \
        -A -G -Q -L \
        -w "$threads_per_sample" \
        > /dev/null 2>&1
        
    echo -e "${GREEN}[$(date +'%H:%M:%S')] [DONE] Sample $sample fastp finished${RESET}"
}

export -f run_fastp

# -----------------------
# Parallel execution with progress
# -----------------------
log_info "Starting parallel fastp ..."

total=${#r1_files[@]}
counter_file=$(mktemp)
echo 0 > "$counter_file"

progress_wrapper() {
    run_fastp "$1"
    count=$(($(cat "$counter_file") + 1))
    echo "$count" > "$counter_file"
    echo -e "${CYAN}[$(date +'%H:%M:%S')] Progress: $count/$total ($((count*100/total))%)${RESET}"
}
export -f progress_wrapper
export counter_file
export total
export GREEN CYAN RESET
export threads_per_sample
export output_dir

parallel -j 0 progress_wrapper {} ::: "${r1_files[@]}"

log_success "All samples fastp analysis completed!"

# -----------------------
# Copy JSON files to report_dir if specified
# -----------------------
if [[ -n "$report_dir" ]]; then
    json_target_dir="$report_dir/Input/fastp_json"
    mkdir -p "$json_target_dir"

    all_ok=true
    for r1 in "${r1_files[@]}"; do
        sample=$(basename "$r1" | sed 's/_R1.*//')
        json_file="$output_dir/${sample}_fastp.json"
        if [[ ! -f "$json_file" ]]; then
            log_warn "JSON file for sample $sample not found: $json_file"
            all_ok=false
        fi
    done

    if [[ "$all_ok" = true ]]; then
        log_info "All JSON files found. Copying to $json_target_dir ..."
        rm -rf "$json_target_dir"/*
        cp "$output_dir"/*.json "$json_target_dir"/
        log_success "JSON files copied successfully."
        log_info "Starting visualization pipeline ..."
        cd "$report_dir"
        bash run_fastp_report.sh > $(pwd)/run_fastp_report.sh.log 2>&1
        log_success "Visualization pipeline completed. Report directory: $report_dir/report"
    else
        log_warn "Some JSON files are missing. Not copying."
    fi
fi

echo
echo "========================= All Done ==========================="
