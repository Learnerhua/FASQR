#!/usr/bin/env python
"""
generate_single_html.py
功能：将已生成的HTML报告和所有依赖资源整合为单文件HTML
注意：此脚本不重复生成图片或数据，只做整合工作
"""

import os
import base64
import re

# 获取项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def read_file_content(filepath):
    """读取文件内容"""
    if not os.path.exists(filepath):
        print(f"[ERROR] 文件不存在: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] 读取文件失败 {filepath}: {e}")
        return None

def read_binary_file(filepath):
    """读取二进制文件"""
    if not os.path.exists(filepath):
        print(f"[ERROR] 文件不存在: {filepath}")
        return None
    
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] 读取二进制文件失败 {filepath}: {e}")
        return None

def image_to_base64(image_path):
    """将图片转换为base64编码"""
    image_data = read_binary_file(image_path)
    if image_data is None:
        return ""
    
    # 根据文件扩展名确定MIME类型
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp'
    }
    
    mime_type = mime_types.get(ext, 'image/png')
    encoded_string = base64.b64encode(image_data).decode('utf-8')
    
    return f"data:{mime_type};base64,{encoded_string}"

def find_all_images(html_content, base_dir):
    """从HTML内容中找出所有图片引用"""
    # 匹配img标签的src属性
    img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
    images = {}
    
    for match in re.finditer(img_pattern, html_content, re.IGNORECASE):
        img_src = match.group(1)
        
        # 跳过已经是data URL的图片
        if img_src.startswith('data:image'):
            continue
        
        # 构建完整路径
        if img_src.startswith('../../'):
            # 相对路径，如../../Output/read1_quality_curves/xxx.png
            img_path = os.path.join(PROJECT_ROOT, img_src.replace('../../', ''))
        else:
            # 其他路径，暂时不支持
            continue
        
        if os.path.exists(img_path):
            images[img_src] = img_path
            print(f"  找到图片: {img_src} -> {img_path}")
        else:
            print(f"  [WARNING] 图片不存在: {img_path}")
    
    return images

def embed_css(html_content, css_filepath):
    """将CSS文件内联到HTML中"""
    css_content = read_file_content(css_filepath)
    if css_content is None:
        return html_content
    
    # 找到head标签，在head末尾插入style标签
    head_end_pattern = r'(</head>)'
    
    # 清理CSS中的注释和多余空白
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    css_content = re.sub(r'\s+', ' ', css_content).strip()
    
    style_tag = f'\n<style>\n{css_content}\n</style>\n'
    
    # 替换CSS引用
    html_content = re.sub(
        r'<link[^>]*href=["\'][^"\']*mystyle\.css["\'][^>]*>',
        style_tag,
        html_content
    )
    
    return html_content

def embed_images(html_content, images_dict):
    """将图片替换为base64编码"""
    for img_src, img_path in images_dict.items():
        base64_data = image_to_base64(img_path)
        if base64_data:
            # 替换src属性
            old_pattern = f'src=["\']{re.escape(img_src)}["\']'
            new_src = f'src="{base64_data}"'
            html_content = re.sub(old_pattern, new_src, html_content, flags=re.IGNORECASE)
            print(f"  已内嵌: {os.path.basename(img_path)}")
    
    return html_content

def create_single_html():
    """创建单文件HTML"""
    print("=" * 60)
    print("单文件HTML报告生成器")
    print("=" * 60)
    
    # 1. 读取已生成的HTML报告
    html_file = os.path.join(PROJECT_ROOT, "Output", "html", "fastp_qc_summary.html")
    if not os.path.exists(html_file):
        print(f"[ERROR] HTML报告不存在，请先运行完整流程生成报告")
        print(f"       运行: ./run_fastp_report.sh")
        return False
    
    print(f"1. 读取HTML报告: {html_file}")
    html_content = read_file_content(html_file)
    if html_content is None:
        return False
    
    # 2. 内联CSS
    print("\n2. 内联CSS样式")
    css_file = os.path.join(PROJECT_ROOT, "assets", "css", "mystyle.css")
    html_content = embed_css(html_content, css_file)
    
    # 3. 查找并内嵌图片
    print("\n3. 查找并内嵌图片")
    images = find_all_images(html_content, PROJECT_ROOT)
    
    if images:
        print(f"  找到 {len(images)} 张需要内嵌的图片")
        html_content = embed_images(html_content, images)
    else:
        print("  未找到需要内嵌的图片")
    
    # 4. 保存单文件HTML（保持原格式不变）
    print("\n4. 保存单文件HTML")
    output_dir = os.path.join(PROJECT_ROOT, "Output/html")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "fastp_qc_single_file.html")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 计算文件大小
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        
        print(f"\n" + "=" * 60)
        print("✅ 单文件HTML生成成功!")
        print(f"📁 文件位置: {output_file}")
        print(f"📊 文件大小: {file_size:.2f} MB")
        print(f"🖼️ 内嵌图片: {len(images)} 张")
        print("=" * 60)
        print("\n✨ 报告特点:")
        print("• 完全独立的HTML文件，无需外部资源")
        print("• 保持原有格式和样式不变")
        print("• 可直接用浏览器打开查看")
        print("• 支持打印为PDF格式")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 保存文件失败: {e}")
        return False

def main():
    """主函数"""
    
    success = create_single_html()
    
    if success:
        print("\n🎉 单文件HTML报告生成完成!")
        print("   可以直接发送 fastp_qc_single_file.html 给客户")
    else:
        print("\n❌ 生成失败，请检查错误信息")
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())