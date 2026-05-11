"""Build the Protego 3-minute demo script PDF."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether,
)

OUTPUT = r"C:\Users\Fritz\Documents\PROJECTS\CYBER AGENT\Protego_Demo_Script_3min45s.pdf"

NAVY = HexColor("#0F3D5C")
ACCENT = HexColor("#1F6FB2")
MUTED = HexColor("#5A6B78")

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=20, leading=24,
    textColor=NAVY, spaceAfter=4,
)
subtitle_style = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=13,
    textColor=MUTED, spaceAfter=14,
)
section_style = ParagraphStyle(
    "Section", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12.5, leading=15,
    textColor=ACCENT, spaceBefore=10, spaceAfter=2,
)
case_style = ParagraphStyle(
    "Case", parent=styles["Heading3"],
    fontName="Helvetica-Bold", fontSize=11.5, leading=14,
    textColor=NAVY, spaceBefore=6, spaceAfter=4,
)
stage_style = ParagraphStyle(
    "Stage", parent=styles["Italic"],
    fontName="Helvetica-Oblique", fontSize=9.5, leading=12,
    textColor=MUTED, leftIndent=10, spaceAfter=4,
)
vo_style = ParagraphStyle(
    "VO", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=14.5,
    textColor=black, leftIndent=12, rightIndent=12,
    borderPadding=6, spaceAfter=6,
)
note_style = ParagraphStyle(
    "Note", parent=styles["Normal"],
    fontName="Helvetica", fontSize=9.5, leading=12.5,
    textColor=MUTED, spaceBefore=8,
)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=HexColor("#D0D7DE"),
                      spaceBefore=8, spaceAfter=8)

def vo(text):
    return Paragraph(f"<i>&ldquo;{text}&rdquo;</i>", vo_style)

def stage(text):
    return Paragraph(f"<i>({text})</i>", stage_style)

doc = SimpleDocTemplate(
    OUTPUT, pagesize=letter,
    leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    title="Protego Cyber Agent — 3-Minute Demo Script",
    author="ProtegoNet",
)

story = []

# Header
story.append(Paragraph("Protego Cyber Agent", title_style))
story.append(Paragraph(
    "Demo Script &nbsp;&middot;&nbsp; watsonx Orchestrate UI &nbsp;&middot;&nbsp; "
    "Runtime ~3:43 &nbsp;&middot;&nbsp; ~555 words @ 150 wpm",
    subtitle_style,
))
story.append(hr())

# INTRO — PART 1: PROBLEM
story.append(Paragraph("[0:00 – 0:30] &nbsp; INTRO — The Problem", section_style))
story.append(stage("Slides only — industry stats, pain-point bullets."))
story.append(vo(
    "Small businesses are the front line of cybercrime. They absorb <b>43%</b> of all "
    "cyberattacks. Business Email Compromise has driven over <b>fifty billion dollars</b> "
    "in cumulative global losses, and phishing is involved in nearly <b>90%</b> of data "
    "breaches. Most small businesses have no dedicated security team and no advanced tools "
    "— finance and operations staff make payment decisions on manual judgment alone. When "
    "a major attack lands, many never recover. They shut down within months. And today&rsquo;s "
    "attacks exploit human trust, not just technical gaps — AI-generated emails, realistic "
    "executive impersonation, fake invoices that look exactly like the real thing."
))

# INTRO — PART 2: SOLUTION
story.append(Paragraph("[0:30 – 1:05] &nbsp; INTRO — The Solution", section_style))
story.append(stage("Slides: Solution + Architectural Diagram + Ethical AI bullets."))
story.append(vo(
    "Existing security tools are too expensive, too technical, and miss the social-"
    "engineering attacks that hurt small businesses most. Meet <b>Protego</b> — an AI-"
    "powered cybersecurity agent built natively in <b>IBM watsonx Orchestrate</b>. One "
    "Orchestrator routes every email, link, and invoice to three specialist collaborators "
    "— Phishing, BEC, and Invoice — backed by a company knowledge base and live security "
    "tools. Protego doesn&rsquo;t rely on a single model: every decision combines multiple "
    "agents, shows its reasoning, and ends in a clear action — Allow, Alert, Quarantine, "
    "or Block. The AI flags threats. The human always has the final word."
))
story.append(stage("Cut to wxo Agent Builder canvas: Orchestrator + 3 collaborators visible."))

# CASE 1
story.append(hr())
story.append(Paragraph("[1:05 – 1:45] &nbsp; Case 1 — Phishing", section_style))
story.append(Paragraph("Miami Dade fake-job email", case_style))
story.append(stage("Paste email into wxo chat. Trace panel opens."))
story.append(vo(
    "The Orchestrator identifies a URL and hands off to the <b>Phishing Agent</b>. The trace "
    "shows the tool calls in order: <b>Google Safe Browsing V2</b> flags the Forms link as "
    "social engineering, <b>URLscan</b> returns the domain reputation, and a <b>Knowledge "
    "Base lookup</b> confirms the gmail sender is not on the Miami Dade College domain. The "
    "agent runs a five-step Chain-of-Thought across URL, content, text, technical, and final "
    "assessment."
))
story.append(stage("Verdict renders."))
story.append(vo(
    "<b>Risk Level: Phishing — 92% confidence.</b> Action: delete and report."
))

# CASE 2
story.append(hr())
story.append(Paragraph("[1:45 – 2:30] &nbsp; Case 2 — Invoice Fraud", section_style))
story.append(Paragraph("43,571 ZAR new-vendor invoice", case_style))
story.append(stage("Upload invoice. Orchestrator routes to Invoice Agent."))
story.append(vo(
    "The <b>Invoice Agent</b> calls the <b>Vendor API</b> against our supplier database — "
    "no historical record for this vendor ID. It cross-checks the bank account — never seen "
    "before. It compares the <b>43,571 ZAR</b> total against vendor invoice ranges in the "
    "knowledge base — far above any first-time threshold. Three fraud patterns trigger at "
    "once: new vendor, bank-detail change, and amount anomaly."
))
story.append(stage("Verdict renders."))
story.append(vo(
    "<b>Final Classification: Invoice Fraud — High confidence.</b> "
    "Action: <b>Quarantine</b> and route to a human reviewer before any payment."
))

# CASE 3
story.append(hr())
story.append(Paragraph("[2:30 – 3:20] &nbsp; Case 3 — Business Email Compromise", section_style))
story.append(Paragraph("Rachel Martin &mdash; $84,215.50 wire transfer", case_style))
story.append(stage("Paste the Project Alpha email. Orchestrator fans out."))
story.append(vo(
    "This one tests the multi-agent logic. The <b>BEC Agent</b> runs its content-semantics "
    "and impersonation analyses — it detects executive impersonation, urgency pressure, "
    "payment redirection to a new escrow account, and a deliberate block on verification: "
    "&lsquo;do not call my mobile.&rsquo; The <b>Knowledge Base lookup</b> confirms "
    "&lsquo;Rachel Martin&rsquo; is <b>not</b> in the employee directory."
))
story.append(vo(
    "The Orchestrator applies its cross-agent reinforcement rule — strong signals from BEC "
    "plus payment manipulation cues from Invoice — and elevates the verdict."
))
story.append(stage("Verdict renders."))
story.append(vo(
    "<b>Final Classification: BEC Fraud — 93% confidence.</b> "
    "Action: <b>Block and escalate.</b> The system alerts the security and finance teams "
    "with a recommended out-of-band callback to a known number — no payment moves until a "
    "verified human approves."
))

# CLOSE
story.append(hr())
story.append(Paragraph("[3:20 – 3:43] &nbsp; CLOSE — Call to Action &amp; Future", section_style))
story.append(stage("Slides: Conclusion / Call to Action / Opportunity for the Future."))
story.append(vo(
    "Every Protego decision is explainable, auditable, and human-supervised — and the "
    "system evolves as new fraud patterns emerge. Small businesses move from reactive "
    "defense to <b>proactive prevention</b>. Looking ahead: end-to-end protection across "
    "email, ERP, and payment systems — continuously learning from new AI-driven attacks, "
    "and scaled to support millions of small businesses globally. "
    "<b>Protego — small business, big defense.</b>"
))

# Production note
story.append(hr())
story.append(Paragraph("Production note", section_style))
story.append(Paragraph(
    "The wxo trace panel is the visual centerpiece — let it linger after each verdict so "
    "viewers can read the tool-call sequence on screen. The UI itself tells the agentic "
    "story; no extra architecture diagrams needed.",
    note_style,
))

doc.build(story)
print(f"Wrote {OUTPUT}")
