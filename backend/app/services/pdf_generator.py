import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import List, Dict, Any

class PDFGenerator:
    def generate_audit_report(self, filepath: str, data: Dict[str, Any]) -> str:
        # data keys: title, compliance_score, total_obligations, compliant_count, gap_count, gaps, evidence_items, pending_tasks
        doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        styles = getSampleStyleSheet()

        # Custom Premium Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#0F172A'), # slate-900
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1E293B'), # slate-800
            spaceBefore=15,
            spaceAfter=10
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'), # slate-700
        )
        
        bold_body_style = ParagraphStyle(
            'BoldBody',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        meta_style = ParagraphStyle(
            'MetaText',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B'), # slate-500
        )

        # Title / Header
        story.append(Paragraph("SEBI CoPilot - Compliance Audit Report", title_style))
        story.append(Paragraph(f"Generated on: {data.get('generated_at', '2026-06-30')}", meta_style))
        story.append(Spacer(1, 15))

        # Metrics Table
        metrics_data = [
            [Paragraph("<b>Compliance KPI Metric</b>", bold_body_style), Paragraph("<b>Value</b>", bold_body_style)],
            [Paragraph("Overall Compliance Score", body_style), Paragraph(f"{data.get('compliance_score', 100.0):.1f}%", bold_body_style)],
            [Paragraph("Total Identified Obligations", body_style), Paragraph(str(data.get('total_obligations', 0)), body_style)],
            [Paragraph("Completed Compliance Items", body_style), Paragraph(str(data.get('compliant_count', 0)), body_style)],
            [Paragraph("Compliance Gaps / Violations", body_style), Paragraph(str(data.get('gap_count', 0)), body_style)]
        ]
        
        t1 = Table(metrics_data, colWidths=[250, 150])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#F1F5F9')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        story.append(t1)
        story.append(Spacer(1, 20))

        # Section: Gaps and Risk Items
        story.append(Paragraph("Active Compliance Gaps & Risks", section_style))
        gaps = data.get('gaps', [])
        if not gaps:
            story.append(Paragraph("No active compliance gaps detected. The organization has satisfied all current regulatory items.", body_style))
        else:
            gaps_data = [
                [Paragraph("<b>Obligation</b>", bold_body_style), Paragraph("<b>Risk Level</b>", bold_body_style), Paragraph("<b>Status Description</b>", bold_body_style)]
            ]
            for g in gaps:
                risk_color = '#EF4444' if g.get('risk_level') == 'High' else ('#F59E0B' if g.get('risk_level') == 'Medium' else '#3B82F6')
                gaps_data.append([
                    Paragraph(g.get('obligation_title', 'Untitled'), body_style),
                    Paragraph(f"<font color='{risk_color}'><b>{g.get('risk_level', 'Medium')}</b></font>", body_style),
                    Paragraph(g.get('message', ''), body_style)
                ])
            
            t2 = Table(gaps_data, colWidths=[180, 80, 240])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#F8FAFC')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t2)
        
        story.append(Spacer(1, 20))

        # Section: Evidence Matrix
        story.append(Paragraph("Compliance Evidence Verification Matrix", section_style))
        evidence = data.get('evidence_items', [])
        if not evidence:
            story.append(Paragraph("No evidence files submitted for the audited period.", body_style))
        else:
            evidence_data = [
                [Paragraph("<b>Evidence File</b>", bold_body_style), Paragraph("<b>Task / Objective</b>", bold_body_style), Paragraph("<b>Status</b>", bold_body_style), Paragraph("<b>Uploaded</b>", bold_body_style)]
            ]
            for ev in evidence:
                status_color = '#10B981' if ev.get('status') == 'approved' else ('#EF4444' if ev.get('status') == 'rejected' else '#64748B')
                evidence_data.append([
                    Paragraph(ev.get('filename', ''), body_style),
                    Paragraph(ev.get('task_title', ''), body_style),
                    Paragraph(f"<font color='{status_color}'><b>{ev.get('status', 'pending').upper()}</b></font>", body_style),
                    Paragraph(ev.get('uploaded_at', ''), body_style)
                ])
            
            t3 = Table(evidence_data, colWidths=[130, 200, 80, 90])
            t3.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#F8FAFC')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t3)

        doc.build(story)
        return filepath

pdf_generator = PDFGenerator()
