#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件打印工具模块
转换Excel为PDF，在浏览器中显示并支持打印
"""

import subprocess
import os
from typing import Tuple
import base64
from openpyxl import load_workbook


def print_excel_file(filepath: str) -> Tuple[bool, str]:
    """
    打印Excel文件（直接打印，不转换格式）
    Args:
        filepath: Excel文件路径
    Returns:
        (成功标志, 错误信息)
    """
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return False, f"文件不存在: {filepath}"
    # 检查是否为Windows系统
    if os.name != "nt":
        return False, "打印功能仅在Windows系统上可用"
    try:
        # 方法1: 使用PowerShell Start-Process命令
        try:
            cmd = ["powershell", "-Command", f'Start-Process "{filepath}" -Verb print']
            result = subprocess.run(cmd, check=False, capture_output=True, timeout=10)
            if result.returncode == 0:
                return True, "打印任务已发送到打印机"
            else:
                # 如果PowerShell失败，尝试方法2
                raise subprocess.CalledProcessError(result.returncode, cmd)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # 方法2: 使用os.startfile（Windows特有）
            try:
                os.startfile(filepath, "print")
                return True, "打印任务已发送到打印机"
            except Exception as e:
                return False, f"打印失败: {str(e)}"
    except Exception as e:
        return False, f"打印过程中发生错误: {str(e)}"


def excel_to_html_intermediate(filepath: str) -> str:
    """
    将Excel文件转换为HTML字符串
    使用pandas读取数据，openpyxl读取格式信息
    Args:
        filepath: Excel文件路径
    Returns:
        HTML字符串
    """
    # 检查文件是否存在
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 使用openpyxl读取工作簿和格式
    wb = load_workbook(filepath)
    html_parts = []
    
    # 添加CSS样式
    html_parts.append("""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .sheet { margin-bottom: 40px; page-break-after: always; }
        .sheet-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; }
        table { border-collapse: collapse; width: 100%; }
        td, th { border: 1px solid #000; padding: 8px; text-align: left; }
        .numeric { text-align: right; }
        .centered { text-align: center; }
        @media print { 
            body { margin: 0; }
            .sheet { page-break-after: always; }
        }
    </style>
    </head>
    <body>
    """)
    
    # 处理每个工作表
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        # 获取已使用范围
        if ws.dimensions:
            html_parts.append('<div class="sheet">')
            html_parts.append(f'<div class="sheet-title">{sheet_name}</div>')
            html_parts.append('<table>')
            
            # 遍历行和列
            for row in ws.iter_rows(min_row=ws.min_row, max_row=ws.max_row, 
                                     min_col=ws.min_column, max_col=ws.max_column):
                html_parts.append('<tr>')
                for cell in row:
                    value = cell.value
                    if value is None:
                        value = ''
                    
                    # 提取样式
                    style = ''
                    if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                        try:
                            rgb = str(cell.fill.fgColor.rgb)
                            if rgb and len(rgb) >= 8:
                                color = rgb[-6:]
                                style += f'background-color: #{color};'
                        except (AttributeError, ValueError, TypeError):
                            pass
                    
                    if cell.font:
                        if cell.font.bold:
                            style += 'font-weight: bold;'
                        if cell.font.italic:
                            style += 'font-style: italic;'
                    
                    if cell.alignment:
                        if cell.alignment.horizontal == 'center':
                            style += 'text-align: center;'
                        elif cell.alignment.horizontal == 'right':
                            style += 'text-align: right;'
                    
                    # 检查是否为数字
                    cell_class = ''
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        cell_class = 'numeric'
                    
                    style_attr = f' style="{style}"' if style else ''
                    class_attr = f' class="{cell_class}"' if cell_class else ''
                    
                    html_parts.append(f'<td{style_attr}{class_attr}>{value}</td>')
                html_parts.append('</tr>')
            
            html_parts.append('</table>')
            html_parts.append('</div>')
    
    html_parts.append('</body></html>')
    wb.close()
    
    return ''.join(html_parts)


def html_to_pdf(html_content: str) -> bytes:
    """
    将HTML转换为PDF字节
    使用weasyprint库
    Args:
        html_content: HTML字符串
    Returns:
        PDF字节
    """
    try:
        from weasyprint import HTML
    except ImportError:
        raise ImportError("weasyprint库未安装，请运行: pip install weasyprint")
    
    # 转换HTML为PDF
    try:
        html_obj = HTML(string=html_content)
        pdf_bytes = html_obj.write_pdf()
        return pdf_bytes
    except Exception as e:
        raise Exception(f"HTML转PDF失败: {str(e)}")


def excel_to_pdf_with_metadata(filepath: str) -> bytes:
    """
    将Excel文件转换为PDF（包含元数据）
    Args:
        filepath: Excel文件路径
    Returns:
        PDF字节
    """
    # 转换为HTML
    html_content = excel_to_html_intermediate(filepath)
    
    # 转换为PDF
    pdf_bytes = html_to_pdf(html_content)
    
    return pdf_bytes


def get_pdf_print_html_component(pdf_bytes: bytes) -> str:
    """
    获取Streamlit HTML组件代码，用于在新标签页中打开PDF并打印
    Args:
        pdf_bytes: PDF字节
    Returns:
        HTML字符串，包含JavaScript代码用于打开和打印PDF
    """
    # 将PDF编码为base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # 创建HTML组件，包含JavaScript来打开新窗口和打印
    html_component = f"""
    <iframe id="pdfFrame" style="display:none;" src="data:application/pdf;base64,{pdf_base64}"></iframe>
    <script>
        // 延迟执行以确保iframe加载完成
        setTimeout(function() {{
            var pdfWindow = window.open("data:application/pdf;base64,{pdf_base64}", "_blank");
            if (pdfWindow) {{
                // 等待PDF加载后打印
                setTimeout(function() {{
                    pdfWindow.print();
                }}, 500);
            }} else {{
                alert("请检查浏览器的弹出窗口设置，可能被阻止了。");
            }}
        }}, 100);
    </script>
    """
    
    return html_component

