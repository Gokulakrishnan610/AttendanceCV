"""PDF report generation for attendance"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import io
import os


ORANGE = colors.HexColor('#FF8C42')
DARK = colors.HexColor('#1F2937')
LIGHT_GRAY = colors.HexColor('#F3F4F6')
GREEN = colors.HexColor('#10B981')
RED = colors.HexColor('#EF4444')
AMBER = colors.HexColor('#F59E0B')
WHITE = colors.white


def generate_daily_report(records, date_str, stats, title="Daily Attendance Report"):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('Title', fontSize=22, textColor=WHITE,
                                  spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('Sub', fontSize=11, textColor=WHITE,
                                alignment=TA_CENTER, fontName='Helvetica')
    
    # Header table with orange background
    header_data = [
        [Paragraph(f'<b>{title}</b>', title_style)],
        [Paragraph(f'Date: {date_str}  |  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', sub_style)]
    ]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ORANGE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # Stats row
    stats_data = [
        [
            Paragraph(f'<b>{stats.get("total", 0)}</b><br/>Total', ParagraphStyle('S', fontSize=14, alignment=TA_CENTER, textColor=DARK, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{stats.get("present", 0)}</b><br/>Present', ParagraphStyle('S', fontSize=14, alignment=TA_CENTER, textColor=GREEN, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{stats.get("absent", 0)}</b><br/>Absent', ParagraphStyle('S', fontSize=14, alignment=TA_CENTER, textColor=RED, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{stats.get("late", 0)}</b><br/>Late', ParagraphStyle('S', fontSize=14, alignment=TA_CENTER, textColor=AMBER, fontName='Helvetica-Bold')),
            Paragraph(f'<b>{stats.get("rate", "0%")}</b><br/>Rate', ParagraphStyle('S', fontSize=14, alignment=TA_CENTER, textColor=ORANGE, fontName='Helvetica-Bold')),
        ]
    ]
    stats_table = Table(stats_data, colWidths=[3.4*cm]*5)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.5*cm))

    # Attendance table
    table_data = [['#', 'Student ID', 'Name', 'Status', 'Updated At']]
    for i, r in enumerate(records, 1):
        status = r.get('status', '')
        table_data.append([
            str(i),
            r.get('student_id', ''),
            r.get('name', ''),
            status,
            r.get('updated_at', '')[:16] if r.get('updated_at') else ''
        ])

    col_widths = [1.2*cm, 3.5*cm, 5.5*cm, 3.2*cm, 3.6*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style = [
        ('BACKGROUND', (0, 0), (-1, 0), ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]
    # Color status cells
    for i, r in enumerate(records, 1):
        status = r.get('status', '')
        if status == 'Present':
            style.append(('TEXTCOLOR', (3, i), (3, i), GREEN))
        elif status == 'Absent':
            style.append(('TEXTCOLOR', (3, i), (3, i), RED))
        elif status == 'Late':
            style.append(('TEXTCOLOR', (3, i), (3, i), AMBER))

    t.setStyle(TableStyle(style))
    elements.append(t)

    elements.append(Spacer(1, 0.5*cm))
    footer_style = ParagraphStyle('foot', fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
    elements.append(Paragraph('Face Recognition Attendance System — Confidential', footer_style))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_summary_report(data, from_date, to_date):
    """Multi-student summary report over a date range."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('T', fontSize=20, textColor=WHITE,
                                  alignment=TA_CENTER, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('S', fontSize=10, textColor=WHITE,
                                alignment=TA_CENTER)

    header_data = [
        [Paragraph('<b>Attendance Summary Report</b>', title_style)],
        [Paragraph(f'Period: {from_date} to {to_date}  |  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', sub_style)]
    ]
    ht = Table(header_data, colWidths=[25*cm])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ORANGE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 0.5*cm))

    table_data = [['Student ID', 'Name', 'Total Days', 'Present', 'Absent', 'Late', 'Rate']]
    for row in data:
        total = row.get('total', 0)
        present = row.get('present', 0)
        rate = f"{(present/total*100):.1f}%" if total > 0 else "0%"
        table_data.append([
            row.get('student_id', ''),
            row.get('name', ''),
            str(total),
            str(present),
            str(row.get('absent', 0)),
            str(row.get('late', 0)),
            rate
        ])

    t = Table(table_data, colWidths=[3*cm, 6*cm, 3*cm, 3*cm, 3*cm, 3*cm, 4*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)

    doc.build(elements)
    buf.seek(0)
    return buf
