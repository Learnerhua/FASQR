#!/usr/bin/env python

import subprocess
import os
import yaml
import argparse
from pathlib import Path
import base64
import time
import re
import json
from typing import List, Tuple, Dict

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def image_to_base64(image_path):
    """将图片转换为base64编码"""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                ext = os.path.splitext(image_path)[1].lower()
                if ext == '.png':
                    mime_type = 'png'
                elif ext in ['.jpg', '.jpeg']:
                    mime_type = 'jpeg'
                elif ext == '.svg':
                    mime_type = 'svg+xml'
                else:
                    mime_type = 'png'
                return f"data:image/{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"[WARNING] 无法加载图片 {image_path}: {e}")
    return ""

def extract_outline_with_hierarchy_fixed(pdf_path: str):
    """
    提取PDF大纲，正确处理特殊结构
    
    根据调试输出，大纲结构是：
    1. 顶层大纲项列表
    2. 某些项后面跟着子项列表
    
    返回: 包含层级关系的树形结构
    """
    try:
        from PyPDF2 import PdfReader
        
        reader = PdfReader(pdf_path)
        outline_tree = []
        
        def process_items(items, parent_title=None, level=0):
            """处理大纲项，识别层级结构"""
            tree_items = []
            
            if not items:
                return tree_items
            
            i = 0
            while i < len(items):
                item = items[i]
                
                if isinstance(item, dict):
                    if '/Title' in item:
                        title = item['/Title']
                        try:
                            page_num = reader.get_destination_page_number(item) + 1
                        except:
                            page_num = 1
                        
                        # 创建树节点
                        tree_item = {
                            'title': title.strip(),
                            'page': page_num,
                            'level': level,
                            'item_ref': item,
                            'children': []
                        }
                        
                        # 检查下一个项是否是列表（可能是子项）
                        if i + 1 < len(items) and isinstance(items[i + 1], list):
                            # 下一个项是列表，可能是子项
                            sub_items = items[i + 1]
                            
                            # 处理子项
                            tree_item['children'] = process_items(sub_items, title, level + 1)
                            i += 1  # 跳过已处理的列表
                        
                        tree_items.append(tree_item)
                        
                elif isinstance(item, list):
                    # 处理列表项（子项）
                    sub_tree_items = process_items(item, parent_title, level)
                    tree_items.extend(sub_tree_items)
                
                i += 1
            
            return tree_items
        
        if hasattr(reader, 'outline') and reader.outline:
            outline_tree = process_items(reader.outline)
        
        print(f"[INFO] 提取到 {len(outline_tree)} 个大纲项")
        return outline_tree
        
    except Exception as e:
        print(f"[ERROR] 提取大纲层级失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def extract_title_to_page_map(outline_tree: List[Dict]) -> Dict[str, int]:
    """
    从大纲树中提取标题到页码的映射
    
    返回: {标题: 页码} 的字典
    """
    title_to_page = {}
    
    def collect_titles(items):
        for item in items:
            title = item['title']
            page = item['page']
            title_to_page[title] = page
            
            # 递归收集子项
            if item.get('children'):
                collect_titles(item['children'])
    
    if outline_tree:
        collect_titles(outline_tree)
    
    print(f"[INFO] 提取到 {len(title_to_page)} 个标题-页码映射")
    return title_to_page

def create_toc_html(title_to_page: Dict[str, int]) -> str:
    """生成目录页HTML"""
    
    # 定义目录章节结构，直接从title_to_page中获取页码
    toc_sections = [
        ("1. 项目信息", 1),
        ("2. 测序数据质量统计", 1),
        ("3. Read1 碱基质量分布", 1),
        ("4. Read2 碱基质量分布", 1),
        ("5. Read1 碱基含量分布", 1),
        ("6. Read2 碱基含量分布", 1),
        ("7. 分析软件与方法学", 1),
        ("7.1 Fastp 软件简介", 2),
        ("7.2 分析流程概述", 2),
        ("7.3 命令与参数", 2),
        ("7.4 参考文献", 2),
        ("8. 报告解读与交付说明", 1),
        ("8.1 FASTQ 文件格式", 2),
        ("8.2 Phred 质量分数系统", 2),
        ("8.2.1 质量分数定义", 3),
        ("8.2.2 质量分数与错误率对照", 3),
        ("8.2.3 ASCII 编码系统", 3),
        ("8.3 文件交付说明", 2),
        ("8.3.1 交付文件结构", 3),
        ("8.3.2 文件详细说明", 3),
        ("8.3.3 使用建议", 3)
    ]
    
    # 生成目录项
    toc_items = []
    for section_title, level in toc_sections:
        # 从PDF大纲中获取准确的页码
        page_num = title_to_page.get(section_title, 1)
        
        level_class = f"level-{level}"
        
        # 处理标题显示
        if level == 1:
            number_color = "#4682B4"
            title_color = "#2c3e50"
            font_weight = "600"
        elif level == 2:
            number_color = "#5D9CEC"
            title_color = "#34495e"
            font_weight = "500"
        else:
            number_color = "#7FB3D5"
            title_color = "#5D6D7E"
            font_weight = "normal"
        
        # 分离数字和文字
        match = re.match(r'^(\d+(?:\.\d+)*)[\.\s]*(.+)', section_title)
        if match:
            number_part = match.group(1) + "."
            text_part = match.group(2)
            colored_title = f'<span class="toc-number" style="color:{number_color}; font-weight:{font_weight};">{number_part}</span><span class="toc-text" style="color:{title_color};">{text_part}</span>'
        else:
            colored_title = f'<span class="toc-text" style="color:{title_color}; font-weight:{font_weight};">{section_title}</span>'
        
        # 根据层级设置缩进
        indent_px = (level - 1) * 20
        
        toc_item = f'''
        <li class="toc-item {level_class}">
            <div class="toc-line">
                <div class="toc-title-container" style="margin-left: {indent_px}px;">
                    {colored_title}
                </div>
                <span class="toc-dots"></span>
                <span class="toc-page" style="color: #4682B4; font-weight: 500;">{page_num}</span>
            </div>
        </li>
        '''
        toc_items.append(toc_item)
    
    toc_items_html = '\n'.join(toc_items)
    
    toc_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            margin: 15mm 20mm 15mm 20mm;
        }}
        
        body {{
            font-family: "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        
        .toc-container {{
            max-width: 100%;
            padding: 5mm 0 0 0;
        }}
        
        .toc-header {{
            text-align: center;
            margin-bottom: 10mm;
            padding-bottom: 5mm;
            border-bottom: 2px solid #4682B4;
            position: relative;
        }}
        
        .toc-title {{
            font-size: 22pt;
            font-weight: bold;
            color: #4682B4;
            margin: 0;
            letter-spacing: 3px;
        }}
        
        .toc-subtitle {{
            font-size: 11pt;
            color: #7FB3D5;
            margin-top: 3mm;
            font-style: italic;
        }}
        
        .toc-list {{
            list-style: none;
            padding: 0;
            margin: 5mm 0 0 0;
        }}
        
        .toc-item {{
            margin: 8px 0;
            line-height: 1.5;
            position: relative;
        }}
        
        .toc-line {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            position: relative;
        }}
        
        .toc-title-container {{
            display: flex;
            align-items: baseline;
            background: white;
            padding-right: 8px;
            z-index: 1;
        }}
        
        .toc-number {{
            margin-right: 6px;
            min-width: 25px;
        }}
        
        .toc-text {{
            flex: 1;
        }}
        
        .level-1 .toc-text {{
            font-size: 11.5pt;
        }}
        
        .level-2 .toc-text {{
            font-size: 10.5pt;
        }}
        
        .level-3 .toc-text {{
            font-size: 10pt;
        }}
        
        .toc-dots {{
            flex: 1;
            border-bottom: 1px dotted #B0C4DE;
            margin: 0 10px;
            position: relative;
            top: -3px;
            opacity: 0.6;
        }}
        
        .toc-page {{
            background: white;
            padding-left: 8px;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
            min-width: 18px;
            text-align: right;
        }}
        
        .toc-decoration {{
            position: absolute;
            top: 5px;
            right: 5px;
            width: 30px;
            height: 30px;
            border-right: 2px solid #4682B4;
            border-top: 2px solid #4682B4;
            opacity: 0.2;
        }}
    </style>
</head>
<body>
    <div class="toc-container">
        <div class="toc-header">
            <div class="toc-decoration"></div>
            <h1 class="toc-title">目 录</h1>
            <div class="toc-subtitle">Table of Contents</div>
        </div>
        
        <ul class="toc-list">
            {toc_items_html}
        </ul>
    </div>
</body>
</html>'''
    
    return toc_html

def create_header_template(header_config, header_logo_base64, project_id):
    """创建页眉HTML模板"""
    if not header_config.get('enabled', True):
        return ''
    
    header_style = """
        width: 100%;
        font-size: 10px;
        padding: 5px 0 0 0;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        position: relative;
        box-sizing: border-box;
    """
    
    logo_html = ''
    if header_logo_base64:
        logo_height = header_config.get('logo_height', '25px')
        logo_html = f'<img src="{header_logo_base64}" style="height: {logo_height};" />'
    
    right_text = header_config.get('right_text', f'康美华大测序数据质控报告 | 项目编号: {project_id}')
    
    return f'''
    <div style="{header_style}">
        <div style="display: flex; align-items: flex-start; margin-left: 10mm; padding-bottom: 5px;">
            {logo_html}
        </div>
        
        <div style="
            color: #333; 
            font-size: 9px; 
            text-align: right; 
            margin-right: 10mm;
            align-self: flex-end;
        ">
            {right_text}
        </div>
        
        <div style="
            position: absolute;
            bottom: 0;
            left: 10mm;
            right: 10mm;
            border-top: 1px solid #000000;
            height: 0;
        "></div>
    </div>
    '''

def create_footer_template(footer_config):
    """创建页脚HTML模板"""
    if not footer_config.get('enabled', True):
        return ''
    
    footer_style = """
        width: 100%;
        font-size: 9px;
        padding: 8px 0 5px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #666;
        box-sizing: border-box;
        position: relative;
    """
    
    footer_text = footer_config.get('text', '康美华大基因技术有限公司 | https://www.kmhdgene.com')
    
    page_numbers_html = ''
    if footer_config.get('show_page_numbers', True):
        page_numbers_html = '''
        <div style="
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            color: #4682B4; 
            font-weight: 500;
            white-space: nowrap;
        ">
            第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页
        </div>
        '''
    
    return f'''
    <div style="{footer_style}">
        <div style="margin-left: 10mm; text-align: left; flex: 1;">
            {footer_text}
        </div>
        
        {page_numbers_html}
        
        <div style="margin-right: 10mm; flex: 1; text-align: right;">
            <!-- 右侧空白占位 -->
        </div>
    </div>
    '''

def merge_pdfs_with_proper_hierarchy(cover_pdf_path: str, main_pdf_path: str, output_pdf_path: str, 
                                    toc_pdf_path: str = None):
    """
    合并PDF并正确保持大纲层级结构
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
        
        print(f"[INFO] 合并PDF文件并保持大纲层级...")
        
        writer = PdfWriter()
        
        # 1. 添加封页（如果有）
        if cover_pdf_path and os.path.exists(cover_pdf_path):
            print(f"[INFO] 添加封页: {cover_pdf_path}")
            cover_reader = PdfReader(cover_pdf_path)
            writer.append_pages_from_reader(cover_reader)
        
        # 2. 添加目录（如果有）
        if toc_pdf_path and os.path.exists(toc_pdf_path):
            print(f"[INFO] 添加目录: {toc_pdf_path}")
            toc_reader = PdfReader(toc_pdf_path)
            writer.append_pages_from_reader(toc_reader)
        
        # 3. 添加主报告
        print(f"[INFO] 添加主报告: {main_pdf_path}")
        main_reader = PdfReader(main_pdf_path)
        main_start_page = len(writer.pages)  # 主报告在最终PDF中的起始页码
        
        # 逐页添加主报告
        for i, page in enumerate(main_reader.pages):
            writer.add_page(page)
        
        print(f"[INFO] 主报告起始页码: {main_start_page + 1}")
        
        # 4. 提取主报告的大纲层级结构
        print(f"[INFO] 提取主报告大纲层级...")
        outline_tree = extract_outline_with_hierarchy_fixed(main_pdf_path)
        
        if outline_tree:
            print(f"[INFO] 开始重建大纲层级...")
            
            def add_outline_tree(items, parent=None, level=0):
                """递归添加大纲项，建立层级关系"""
                for item in items:
                    title = item['title']
                    original_page = item['page'] - 1  # 转换为0-based
                    final_page = original_page + main_start_page
                    
                    # 添加大纲项
                    outline_item = writer.add_outline_item(
                        title=title,
                        page_number=final_page,
                        parent=parent,  # 关键：传递父项引用
                        color=None,
                        bold=False,
                        italic=False
                    )
                    
                    # 递归添加子项
                    if item.get('children'):
                        add_outline_tree(item['children'], outline_item, level + 1)
            
            # 添加整个大纲树
            add_outline_tree(outline_tree)
            print(f"[INFO] 大纲层级重建完成")
        else:
            print(f"[INFO] 主报告没有大纲")
        
        # 5. 写入最终PDF
        with open(output_pdf_path, 'wb') as output_file:
            writer.write(output_file)
        
        print(f"[OK] PDF合并完成: {output_pdf_path}")
        print(f"[INFO] 文件大小: {os.path.getsize(output_pdf_path) / 1024 / 1024:.2f} MB")
        
        return True
        
    except ImportError:
        print("[ERROR] PyPDF2 未安装")
        return False
    except Exception as e:
        print(f"[ERROR] 合并PDF失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Convert HTML report to PDF using Playwright"
    )
    parser.add_argument("-c", "--config", required=True, help="Path to report.yaml")
    parser.add_argument("--with-toc", action="store_true", help="Add table of contents")
    parser.add_argument("--with-cover", action="store_true", help="Add cover page")
    args = parser.parse_args()

    config = load_config(args.config)
    html_in = config["output"]["html"]
    pdf_out = config["output"]["pdf"]
    os.makedirs(os.path.dirname(pdf_out), exist_ok=True)

    print("[INFO] Converting HTML to PDF using Playwright...")
    start_time = time.time()
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--disable-gpu', '--no-sandbox']
            )
            
            # ====================================================
            # 第一步：生成主报告PDF（包含页眉页脚和页码）
            # ====================================================
            print("\n[STEP 4.1] 生成主报告PDF...")
            context_main = browser.new_context()
            page_main = context_main.new_page()
            
            html_path = os.path.abspath(html_in)
            page_main.goto(f"file://{html_path}", wait_until="networkidle")
            page_main.wait_for_timeout(1000)
            
            # 添加打印样式
            page_main.add_style_tag(content="""
    @media print {
        .content { margin-left: 0 !important; padding: 0 !important; width: 100% !important; }
        .layout { display: block !important; }
        .table-wrapper { width: 100% !important; margin: 0 auto !important; }
        .mystyle { width: 100% !important; font-size: 8pt !important; transform: scale(0.95) !important; transform-origin: 0 0 !important; }
        .mystyle th, .mystyle td { padding: 4px 6px !important; font-size: 8pt !important; white-space: normal !important; }
        .section-title { page-break-after: avoid !important; page-break-inside: avoid !important; }
        #project-info h1.section-title { margin-top: 5px !important; }
        h1, h2 { page-break-after: avoid !important; }
        .report-section { page-break-inside: avoid !important; }
        .qc-image-grid { grid-template-columns: 1fr !important; gap: 20px !important; }
        .project-info { box-shadow: none !important; border: 1px solid #ddd !important; margin: 10px 0 !important; }
        body { margin: 0 !important; padding: 0 !important; width: 100% !important; margin-top: 10px !important; margin-bottom: 25px !important; }
        main { width: 100% !important; margin: 0 !important; padding: 0 !important; }
        .mystyle { table-layout: fixed !important; }
        .mystyle th:first-child, .mystyle td:first-child { width: 100px !important; }
        .mystyle th:not(:first-child), .mystyle td:not(:first-child) { width: 80px !important; }
    }
""")
            
            # PDF配置
            pdf_config = config.get('pdf_header_footer', {})
            header_config = pdf_config.get('header', {})
            footer_config = pdf_config.get('footer', {})
            margin_config = pdf_config.get('margins', {})
            project_id = config['project']['ID']
            
            # 页眉页脚
            header_logo_base64 = ""
            if header_config.get('enabled', True):
                logo_path = header_config.get('logo', '')
                if logo_path:
                    if not os.path.exists(logo_path):
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        logo_path = os.path.join(script_dir, logo_path)
                    header_logo_base64 = image_to_base64(logo_path)
            
            header_template = create_header_template(header_config, header_logo_base64, project_id)
            footer_template = create_footer_template(footer_config)
            
            margins = {
                "top": margin_config.get('top', '25mm'),
                "bottom": margin_config.get('bottom', '20mm'),
                "left": margin_config.get('left', '10mm'),
                "right": margin_config.get('right', '10mm')
            }
            
            # 生成主报告PDF（必须包含大纲和页码）
            temp_main_pdf = "temp_main.pdf"
            pdf_options = {
                "path": temp_main_pdf,
                "format": "A4",
                "margin": margins,
                "print_background": True,
                "prefer_css_page_size": True,
                "tagged": True,   # 重要：启用标签
                "outline": True   # 重要：生成大纲
            }
            
            # 重要：主报告必须包含页眉页脚
            pdf_options["display_header_footer"] = True
            pdf_options["header_template"] = header_template
            pdf_options["footer_template"] = footer_template
            
            page_main.pdf(**pdf_options)
            page_main.close()
            context_main.close()
            
            print(f"[OK] 主报告PDF生成完成: {temp_main_pdf}")
            
            # ====================================================
            # 第二步：根据主报告PDF提取大纲，生成目录页
            # ====================================================
            toc_pdf = None
            
            if args.with_toc:
                print("\n[STEP 4.2] 根据主报告大纲生成目录页...")
                
                # 从主报告PDF提取大纲层级结构
                outline_tree = extract_outline_with_hierarchy_fixed(temp_main_pdf)
                
                # 从大纲树中提取标题-页码映射
                title_to_page = extract_title_to_page_map(outline_tree)
                
                # 生成目录页HTML（使用你的原始create_toc_html函数）
                context_toc = browser.new_context()
                page_toc = context_toc.new_page()
                
                toc_html = create_toc_html(title_to_page)
                page_toc.set_content(toc_html, wait_until="networkidle")
                page_toc.wait_for_timeout(800)
                
                # 生成目录页PDF（无页眉页脚）
                toc_pdf = "temp_toc.pdf"
                page_toc.pdf(
                    path=toc_pdf,
                    format="A4",
                    margin=margins,
                    print_background=True,
                    display_header_footer=False,
                    prefer_css_page_size=False
                )
                page_toc.close()
                context_toc.close()
                
                print(f"[OK] 目录页生成完成: {toc_pdf}")
            
            browser.close()
            
            # ====================================================
            # 第三步：合并PDF，保持大纲层级
            # ====================================================
            print("\n[STEP 4.3] 合并PDF文件（保持大纲层级）...")
            
            # 获取封页路径
            cover_pdf = None
            if args.with_cover:
                cover_pdf = "templates/pdf_cover.pdf"
                if not os.path.exists(cover_pdf):
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    cover_pdf = os.path.join(script_dir, "templates", "pdf_cover.pdf")
                    if not os.path.exists(cover_pdf):
                        print(f"[WARNING] 封页文件不存在: {cover_pdf}")
                        cover_pdf = None
                else:
                    print(f"[INFO] 使用封页: {cover_pdf}")
            
            # 使用新的合并函数，保持大纲层级
            if merge_pdfs_with_proper_hierarchy(cover_pdf, temp_main_pdf, pdf_out, toc_pdf):
                print(f"\n[SUCCESS] PDF报告生成完成: {pdf_out}")
            else:
                # 如果合并失败，使用简单方法
                print("[WARNING] 层级合并失败，使用简单合并...")
                try:
                    from PyPDF2 import PdfMerger
                    merger = PdfMerger()
                    
                    if cover_pdf and os.path.exists(cover_pdf):
                        merger.append(cover_pdf)
                    if toc_pdf and os.path.exists(toc_pdf):
                        merger.append(toc_pdf)
                    merger.append(temp_main_pdf)
                    
                    merger.write(pdf_out)
                    merger.close()
                    print(f"[OK] PDF报告生成完成（简单合并）: {pdf_out}")
                except Exception as e:
                    print(f"[ERROR] 简单合并也失败: {e}")
                    # 最后手段：只复制主报告
                    import shutil
                    shutil.copy(temp_main_pdf, pdf_out)
                    print(f"[OK] PDF报告生成完成（仅主报告）: {pdf_out}")
            
            # ====================================================
            # 第四步：清理临时文件
            # ====================================================
            print("\n[STEP 4.4] 清理临时文件...")
            temp_files = ["temp_main.pdf", "temp_toc.pdf"]
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            total_time = time.time() - start_time
            print(f"\n[INFO] 总耗时: {total_time:.2f} 秒")
            
            # 最终说明
            if os.path.exists(pdf_out):
                file_size = os.path.getsize(pdf_out) / 1024 / 1024
                print(f"[INFO] 最终文件: {pdf_out} ({file_size:.2f} MB)")
                print(f"[提示] 目录中的页码与主报告底部显示的页码一致")
        
    except ImportError:
        print("[ERROR] Playwright is not installed.")
        print("Please install: pip install playwright && playwright install chromium")
        return 1
    except Exception as e:
        print(f"[ERROR] 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())