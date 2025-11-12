#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件打印工具模块
转换Excel为PDF，在浏览器中显示并支持打印
"""

import os
import base64
import html
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

from openpyxl import load_workbook


def _to_float(value: Any) -> Optional[float]:
    """辅助函数：将单元格值转换为浮点数"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.replace(',', '').strip()
        if not candidate:
            return None
        try:
            return float(candidate)
        except ValueError:
            return None
    return None


def _extract_workbook_metadata(workbook) -> Dict[str, Any]:
    """从工作簿提取航班元数据"""
    metadata: Dict[str, Any] = {}
    if 'SUM' in workbook.sheetnames:
        ws_sum = workbook['SUM']
        flight_number = ws_sum.cell(row=4, column=11).value
        if flight_number:
            metadata['flight_number'] = str(flight_number).strip()
        flight_date_cell = ws_sum.cell(row=14, column=3).value
        if flight_date_cell:
            if isinstance(flight_date_cell, datetime):
                metadata['flight_date'] = flight_date_cell.strftime('%Y-%m-%d')
            else:
                metadata['flight_date'] = str(flight_date_cell).strip()
        unprocessed = []
        for row_idx in range(15, ws_sum.max_row + 1):
            note_value = ws_sum.cell(row=row_idx, column=3).value
            if note_value is None:
                continue
            note = str(note_value).strip()
            if note:
                unprocessed.append(note)
        if unprocessed:
            metadata['unprocessed_records'] = unprocessed
    if 'EMD' in workbook.sheetnames:
        ws_emd = workbook['EMD']
        start_row = 8
        record_count = 0
        cash_total = 0.0
        total_amount = 0.0
        for row_idx in range(start_row, ws_emd.max_row + 1):
            row_values = [
                ws_emd.cell(row=row_idx, column=col_idx).value
                for col_idx in range(ws_emd.min_column, ws_emd.max_column + 1)
            ]
            if not any(str(value).strip() for value in row_values if value is not None):
                continue
            record_count += 1
            cash_value = _to_float(ws_emd.cell(row=row_idx, column=11).value)
            total_value = _to_float(ws_emd.cell(row=row_idx, column=14).value)
            if cash_value is not None:
                cash_total += cash_value
            if total_value is not None:
                total_amount += total_value
        metadata['record_count'] = record_count
        if cash_total:
            metadata['cash_total'] = round(cash_total, 2)
        if total_amount:
            metadata['total_amount'] = round(total_amount, 2)
    return metadata


def _build_metadata_html(metadata: Dict[str, Any]) -> str:
    """将元数据转换为HTML片段"""
    if not metadata:
        return ''
    field_order = [
        'flight_number',
        'flight_date',
        'record_count',
        'cash_total',
        'total_amount',
        'unprocessed_records',
    ]
    labels = {
        'flight_number': '航班号',
        'flight_date': '航班日期',
        'record_count': '记录数量',
        'cash_total': '现金合计',
        'total_amount': '总金额',
        'unprocessed_records': '未处理记录',
    }
    rows = []
    for key in field_order:
        if key not in metadata:
            continue
        value = metadata[key]
        if value is None or value == '':
            continue
        if key == 'unprocessed_records' and isinstance(value, list):
            if not value:
                continue
            items = ''.join(f'<li>{html.escape(str(item))}</li>' for item in value)
            value_html = f'<ul>{items}</ul>'
        else:
            if isinstance(value, float):
                value_html = f'{value:,.2f}'
            else:
                value_html = html.escape(str(value))
        label = labels.get(key, html.escape(key))
        rows.append(f'<tr><th>{label}</th><td>{value_html}</td></tr>')
    if not rows:
        return ''
    return (
        '<div class="metadata-block">'
        '<h2>航班元数据</h2>'
        '<table class="metadata-table">'
        + ''.join(rows)
        + '</table>'
        '</div>'
    )


def excel_to_html_intermediate(filepath: str) -> Tuple[str, Dict[str, Any]]:
    """
    将Excel文件转换为HTML字符串，并返回提取的元数据
    Args:
        filepath: Excel文件路径
    Returns:
        (HTML字符串, 元数据字典)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    workbook = load_workbook(filepath)
    metadata = _extract_workbook_metadata(workbook)
    html_parts = [
        """
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metadata-block {{ margin-bottom: 32px; }}
        .metadata-table {{ border-collapse: collapse; width: 100%; }}
        .metadata-table th, .metadata-table td {{ border: 1px solid #d0d7de; padding: 8px; text-align: left; }}
        .metadata-table th {{ width: 180px; background-color: #f6f8fa; }}
        .sheet {{ margin-bottom: 40px; page-break-after: always; }}
        .sheet-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        td, th {{ border: 1px solid #000; padding: 8px; text-align: left; }}
        .numeric {{ text-align: right; }}
        .centered {{ text-align: center; }}
        ul {{ margin: 0; padding-left: 18px; }}
        @media print {{
            body {{ margin: 0; }}
            .sheet {{ page-break-after: always; }}
        }}
    </style>
    </head>
    <body>
    """.strip()
    ]
    metadata_html = _build_metadata_html(metadata)
    if metadata_html:
        html_parts.append(metadata_html)
    for sheet_name in workbook.sheetnames:
        worksheet = workbook[sheet_name]
        if not worksheet.dimensions:
            continue
        html_parts.append('<div class="sheet">')
        html_parts.append(f'<div class="sheet-title">{html.escape(sheet_name)}</div>')
        html_parts.append('<table>')
        for row in worksheet.iter_rows(
            min_row=worksheet.min_row,
            max_row=worksheet.max_row,
            min_col=worksheet.min_column,
            max_col=worksheet.max_column,
        ):
            html_parts.append('<tr>')
            for cell in row:
                value = cell.value
                if value is None:
                    value = ''
                cell_style = []
                if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                    try:
                        rgb = str(cell.fill.fgColor.rgb)
                        if rgb and len(rgb) >= 8:
                            color = rgb[-6:]
                            cell_style.append(f'background-color: #{color};')
                    except (AttributeError, ValueError, TypeError):
                        pass
                if cell.font:
                    if cell.font.bold:
                        cell_style.append('font-weight: bold;')
                    if cell.font.italic:
                        cell_style.append('font-style: italic;')
                if cell.alignment:
                    if cell.alignment.horizontal == 'center':
                        cell_style.append('text-align: center;')
                    elif cell.alignment.horizontal == 'right':
                        cell_style.append('text-align: right;')
                cell_class = ''
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cell_class = 'numeric'
                style_attr = f' style="{" ".join(cell_style)}"' if cell_style else ''
                class_attr = f' class="{cell_class}"' if cell_class else ''
                cell_text = html.escape(str(value))
                html_parts.append(f'<td{style_attr}{class_attr}>{cell_text}</td>')
            html_parts.append('</tr>')
        html_parts.append('</table>')
        html_parts.append('</div>')
    html_parts.append('</body></html>')
    workbook.close()
    return ''.join(html_parts), metadata


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
    except ImportError as exc:
        raise ImportError("weasyprint库未安装，请运行: pip install weasyprint") from exc
    try:
        html_obj = HTML(string=html_content)
        return html_obj.write_pdf()
    except Exception as exc:
        raise Exception(f"HTML转PDF失败: {exc}") from exc


def excel_to_pdf_with_metadata(filepath: str) -> Tuple[bytes, Dict[str, Any], str]:
    """
    将Excel文件转换为PDF，并返回元数据和HTML内容
    Args:
        filepath: Excel文件路径
    Returns:
        (PDF字节, 元数据字典, HTML字符串)
    """
    html_content, metadata = excel_to_html_intermediate(filepath)
    pdf_bytes = html_to_pdf(html_content)
    return pdf_bytes, metadata, html_content


def get_pdf_print_html_component(pdf_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    获取Streamlit HTML组件代码，用于在新标签页中展示元数据并打印
    Args:
        pdf_bytes: PDF字节
        metadata: 航班元数据
    Returns:
        HTML字符串，包含JavaScript代码用于打开和打印PDF
    """
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    metadata_html = _build_metadata_html(metadata or {})
    metadata_js = metadata_html.replace('\\', '\\\\').replace('`', '\\`')
    return f"""
<script>
(function() {{
    const metadataHtml = `{metadata_js}`;
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
                    body {{ font-family: Arial, sans-serif; margin: 24px; }}
                    h1 {{ font-size: 20px; margin-bottom: 12px; }}
                    .metadata-block {{ margin-bottom: 24px; }}
                    .metadata-table {{ border-collapse: collapse; width: 100%; }}
                    .metadata-table th, .metadata-table td {{ border: 1px solid #d0d7de; padding: 8px; text-align: left; }}
                    .metadata-table th {{ width: 180px; background-color: #f6f8fa; }}
                    ul {{ margin: 0; padding-left: 18px; }}
                    iframe {{ width: 100%; height: 80vh; border: none; }}
                </style>
            </head>
            <body>
                <h1>打印预览</h1>
                ${{metadataHtml}}
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


def print_excel_file(filepath: str) -> Tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
    """
    将Excel转换为PDF并生成可用于Streamlit的打印组件
    Args:
        filepath: Excel文件路径
    Returns:
        (成功标志, 提示消息, HTML组件字符串, 元数据字典)
    """
    if not os.path.exists(filepath):
        return False, f"文件不存在: {filepath}", None, None
    try:
        pdf_bytes, metadata, _ = excel_to_pdf_with_metadata(filepath)
        component_html = get_pdf_print_html_component(pdf_bytes, metadata)
        return True, "✅ PDF已打开，请在新窗口中完成打印", component_html, metadata
    except ImportError as exc:
        return False, f"缺少依赖库: {exc}", None, None
    except Exception as exc:
        return False, f"打印过程中发生错误: {exc}", None, None

