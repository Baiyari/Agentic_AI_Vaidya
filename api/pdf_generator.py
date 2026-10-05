import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from data.models import TriageRecord


def generate_case_pdf(record: TriageRecord) -> io.BytesIO:
    """
    Generates a professional clinical referral & escalation PDF report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )
    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold"
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("VAIDYA CLINICAL ADVISORY & REFERRAL REPORT", title_style))
    story.append(Paragraph("Autonomous Multi-Agent Health Decision Support • Confidential Medical Document", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=10))

    # Case Summary Banner
    severity_color = colors.HexColor("#dc2626") if record.severity == "EMERGENCY" else (
        colors.HexColor("#ea580c") if record.severity == "HIGH" else (
            colors.HexColor("#ca8a04") if record.severity == "MODERATE" else colors.HexColor("#16a34a")
        )
    )

    try:
        symptoms_list = json.loads(record.symptoms)
        symptoms_str = ", ".join(symptoms_list)
    except Exception:
        symptoms_str = str(record.symptoms)

    created_at_str = record.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if record.created_at else "N/A"

    info_data = [
        [
            Paragraph("<b>Case ID:</b>", bold_label), Paragraph(f"#{record.id}", body_style),
            Paragraph("<b>Date/Time:</b>", bold_label), Paragraph(created_at_str, body_style)
        ],
        [
            Paragraph("<b>Patient ID:</b>", bold_label), Paragraph(record.patient_id or "Anonymous / Intake", body_style),
            Paragraph("<b>Demographics:</b>", bold_label), Paragraph(f"Age {record.age} • Duration: {record.duration_days} day(s)", body_style)
        ],
        [
            Paragraph("<b>Safety Severity:</b>", bold_label), Paragraph(f"<font color='{severity_color.hexval()}'><b>{record.severity} (Score {record.score}/100)</b></font>", body_style),
            Paragraph("<b>Assigned Specialty:</b>", bold_label), Paragraph(record.specialist or "General Medicine", body_style)
        ],
        [
            Paragraph("<b>Presenting Symptoms:</b>", bold_label), Paragraph(symptoms_str, body_style),
            Paragraph("<b>Triage Reason:</b>", bold_label), Paragraph(record.reason, body_style)
        ]
    ]

    info_table = Table(info_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.3 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # Chief Complaint
    if record.chief_complaint:
        story.append(Paragraph("Patient Conversational Narrative / Chief Complaint", section_heading))
        story.append(Paragraph(f"<i>\"{record.chief_complaint}\"</i>", body_style))
        story.append(Spacer(1, 8))

    # Narrative Summary / Explainability Report
    story.append(Paragraph("Clinical Synthesis & Decision Rationale", section_heading))
    summary_text = record.narrative_summary or "No narrative summary recorded."
    for line in summary_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 3))
        elif line.startswith("=") or line.startswith("***"):
            continue
        elif line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4."):
            story.append(Paragraph(f"<b>{line}</b>", ParagraphStyle("SubHead", parent=body_style, fontName="Helvetica-Bold", spaceBefore=4)))
        else:
            story.append(Paragraph(line, body_style))

    story.append(Spacer(1, 10))

    # Evidence Citations
    if record.citations:
        story.append(Paragraph("Peer-Reviewed Evidence Citations (NCBI PubMed)", section_heading))
        cit_data = [
            [Paragraph("<b>PMID</b>", bold_label), Paragraph("<b>Title & Publication Reference</b>", bold_label)]
        ]
        for c in record.citations:
            cit_data.append([
                Paragraph(c.pmid or "Ref", body_style),
                Paragraph(f"<b>{c.title}</b><br/><font color='#2563eb'>{c.url or ''}</font>", body_style)
            ])
        cit_table = Table(cit_data, colWidths=[1.0 * inch, 6.2 * inch])
        cit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(cit_table)
        story.append(Spacer(1, 10))

    # Audit Trail Trace Summary
    if record.traces:
        story.append(Paragraph("Multi-Agent Execution Audit Log", section_heading))
        trace_data = [
            [Paragraph("<b>Agent</b>", bold_label), Paragraph("<b>Decision Summary & Reasoning</b>", bold_label)]
        ]
        for t in record.traces:
            trace_data.append([
                Paragraph(f"<b>{t.agent_name}</b>", body_style),
                Paragraph(f"{t.output_summary or ''}<br/><font color='#64748b'>{t.reasoning or ''}</font>", body_style)
            ])
        trace_table = Table(trace_data, colWidths=[1.8 * inch, 5.4 * inch])
        trace_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(trace_table)

    # Footer Disclaimer
    story.append(Spacer(1, 14))
    disclaimer = (
        "<b>CLINICAL AUDIT NOTICE:</b> Vaidya incorporates a 100% deterministic safety rule engine for "
        "triage scoring. Specialist agent recommendations and literature retrieval provide decision support "
        "and do not substitute for in-person physician clinical judgment."
    )
    story.append(Paragraph(disclaimer, ParagraphStyle("Footer", parent=body_style, fontSize=7, leading=10, textColor=colors.HexColor("#94a3b8"))))

    doc.build(story)
    buffer.seek(0)
    return buffer
