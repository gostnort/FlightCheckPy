#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件打印工具模块
使用Excel COM自动化直接导出PDF
"""

import base64
import tempfile
from pathlib import Path
from typing import Tuple, Optional

try:
    import win32com.client
except ImportError:
    win32com = None


def excel_to_pdf(filepath: str) -> bytes:
    """
    使用Excel COM自动化将Excel文件直接导出为PDF
    Args:
        filepath: Excel文件路径
    Returns:
        PDF字节
    """
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    if win32com is None:
        raise ImportError("win32com库未安装，请运行: pip install pywin32")
    excel = None
    wb = None
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        # 打开工作簿
        wb = excel.Workbooks.Open(str(file_path.resolve()))
        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_path = Path(tmp_file.name)
        try:
            # 导出为PDF (0 = xlTypePDF)
            wb.ExportAsFixedFormat(0, str(pdf_path))
            # 读取PDF字节
            pdf_bytes = pdf_path.read_bytes()
            return pdf_bytes
        finally:
            # 清理临时文件
            if pdf_path.exists():
                pdf_path.unlink()
    finally:
        # 关闭工作簿和Excel
        if wb:
            wb.Close(SaveChanges=False)
        if excel:
            excel.Quit()


def get_pdf_print_html_component(pdf_bytes: bytes) -> str:
    """
    获取Streamlit HTML组件代码，用于在新标签页中打开PDF并打印
    Args:
        pdf_bytes: PDF字节
    Returns:
        HTML字符串，包含JavaScript代码用于打开和打印PDF
    """
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"""
<script>
(function() {{
    const pdfData = "data:application/pdf;base64,{pdf_base64}";
    setTimeout(function() {{
        const printWindow = window.open("", "_blank");
        if (!printWindow) {{
            alert("请检查浏览器的弹出窗口设置，可能被阻止了。");
            return;
        }}
        printWindow.document.write(`
            <html>
            <head>
                <meta charset="utf-8" />
                <title>打印预览</title>
                <style>
                    body {{ margin: 0; }}
                    iframe {{ width: 100%; height: 100vh; border: none; }}
                </style>
            </head>
            <body>
                <iframe id="pdfFrame" src="${{pdfData}}" title="PDF预览"></iframe>
                <script>
                    const iframe = document.getElementById('pdfFrame');
                    iframe.addEventListener('load', function() {{
                        setTimeout(function() {{
                            window.focus();
                            window.print();
                        }}, 500);
                    }});
                <\/script>
            </body>
            </html>
        `);
        printWindow.document.close();
    }}, 100);
}})();
</script>
""".strip()


def print_excel_file(
    filepath: str,
) -> Tuple[bool, str, Optional[str], Optional[dict]]:
    """
    将Excel转换为PDF并生成可用于Streamlit的打印组件
    Args:
        filepath: Excel文件路径
    Returns:
        (成功标志, 提示消息, HTML组件字符串, 元数据字典)
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return False, f"文件不存在: {filepath}", None, None
    try:
        pdf_bytes = excel_to_pdf(filepath)
        component_html = get_pdf_print_html_component(pdf_bytes)
        return True, "✅ PDF已打开，请在新窗口中完成打印", component_html, None
    except ImportError as exc:
        return False, f"缺少依赖库: {exc}", None, None
    except Exception as exc:
        return False, f"打印过程中发生错误: {exc}", None, None
