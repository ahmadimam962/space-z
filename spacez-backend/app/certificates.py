from datetime import datetime
from typing import Optional
from uuid import uuid4
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, Course, User, Notification
from app.users import get_current_user

from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
import qrcode

# المكتبات الجديدة للعربية
import arabic_reshaper
from bidi.algorithm import get_display

router = APIRouter(tags=["Certificates"])


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "Tajawal-Regular.ttf")

# تسجيل الخط
try:
    pdfmetrics.registerFont(TTFont("Arabic", FONT_PATH))
except:
    pass

def reshape_arabic(text: str) -> str:
    """إعادة تشكيل النص العربي بشكل صحيح"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except:
        return text


def add_border(canvas, doc):
    """إضافة إطار زخرفي للصفحة"""
    canvas.saveState()
    
    # Outer border
    canvas.setStrokeColor(HexColor("#1a5f7a"))
    canvas.setLineWidth(3)
    canvas.rect(
        0.5*cm, 
        0.5*cm, 
        doc.pagesize[0] - 1*cm, 
        doc.pagesize[1] - 1*cm,
        stroke=1, 
        fill=0
    )
    
    # Inner border
    canvas.setStrokeColor(HexColor("#159895"))
    canvas.setLineWidth(1)
    canvas.rect(
        0.8*cm, 
        0.8*cm, 
        doc.pagesize[0] - 1.6*cm, 
        doc.pagesize[1] - 1.6*cm,
        stroke=1, 
        fill=0
    )
    
    # Decorative corners
    corner_size = 2*cm
    canvas.setStrokeColor(HexColor("#c9ada7"))
    canvas.setLineWidth(2)
    
    # Top-left
    canvas.line(0.8*cm, doc.pagesize[1] - 0.8*cm, 0.8*cm + corner_size, doc.pagesize[1] - 0.8*cm)
    canvas.line(0.8*cm, doc.pagesize[1] - 0.8*cm, 0.8*cm, doc.pagesize[1] - 0.8*cm - corner_size)
    
    # Top-right
    canvas.line(doc.pagesize[0] - 0.8*cm, doc.pagesize[1] - 0.8*cm, 
                doc.pagesize[0] - 0.8*cm - corner_size, doc.pagesize[1] - 0.8*cm)
    canvas.line(doc.pagesize[0] - 0.8*cm, doc.pagesize[1] - 0.8*cm, 
                doc.pagesize[0] - 0.8*cm, doc.pagesize[1] - 0.8*cm - corner_size)
    
    # Bottom-left
    canvas.line(0.8*cm, 0.8*cm, 0.8*cm + corner_size, 0.8*cm)
    canvas.line(0.8*cm, 0.8*cm, 0.8*cm, 0.8*cm + corner_size)
    
    # Bottom-right
    canvas.line(doc.pagesize[0] - 0.8*cm, 0.8*cm, 
                doc.pagesize[0] - 0.8*cm - corner_size, 0.8*cm)
    canvas.line(doc.pagesize[0] - 0.8*cm, 0.8*cm, 
                doc.pagesize[0] - 0.8*cm, 0.8*cm + corner_size)
    
    canvas.restoreState()


def certificate_to_dict(certificate: Certificate, db: Session) -> dict:
    user = db.query(User).filter(User.id == certificate.user_id).first()
    course = db.query(Course).filter(Course.id == certificate.course_id).first()

    return {
        "id": certificate.id,
        "certificateCode": certificate.certificate_code,
        "issuedAt": certificate.issued_at,
        "student": {
            "id": user.id if user else None,
            "name": f"{user.first_name} {user.last_name}" if user else "-",
            "email": user.email if user else "-"
        },
        "course": {
            "id": course.id if course else None,
            "title": course.title if course else "-"
        }
    }


def generate_certificate_code() -> str:
    return f"SZ-{uuid4().hex[:12].upper()}"


def create_certificate_if_eligible(db: Session, user_id: int, course_id: int) -> Optional[Certificate]:
    existing = db.query(Certificate).filter(
        Certificate.user_id == user_id,
        Certificate.course_id == course_id
    ).first()

    if existing:
        return None

    code = generate_certificate_code()
    while db.query(Certificate).filter(Certificate.certificate_code == code).first():
        code = generate_certificate_code()

    certificate = Certificate(
        user_id=user_id,
        course_id=course_id,
        certificate_code=code,
        issued_at=datetime.utcnow()
    )

    db.add(certificate)

    course = db.query(Course).filter(Course.id == course_id).first()
    db.add(Notification(
        user_id=user_id,
        title="تم إصدار شهادة جديدة",
        message=f"مبروك! تم إصدار شهادة إكمال كورس {course.title if course else ''}."
    ))

    return certificate


@router.get("/api/my-certificates")
def my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    certificates = db.query(Certificate).filter(
        Certificate.user_id == current_user.id
    ).order_by(Certificate.issued_at.desc()).all()

    return {
        "success": True,
        "data": [certificate_to_dict(certificate, db) for certificate in certificates]
    }


@router.get("/api/certificates/{certificate_code}")
def verify_certificate(
    certificate_code: str,
    db: Session = Depends(get_db)
):
    certificate = db.query(Certificate).filter(
        Certificate.certificate_code == certificate_code
    ).first()

    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    return {
        "success": True,
        "valid": True,
        "data": certificate_to_dict(certificate, db)
    }


@router.get("/api/certificates/{certificate_code}/download")
def download_certificate(
    certificate_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    certificate = db.query(Certificate).filter(
        Certificate.certificate_code == certificate_code
    ).first()

    if not certificate:
        raise HTTPException(404, "Certificate not found")

    if certificate.user_id != current_user.id:
        raise HTTPException(403, "Not allowed")

    course = db.query(Course).filter(
        Course.id == certificate.course_id
    ).first()

    # Generate QR Code
    qr = qrcode.make(
        f"https://spacez.edu/verify/{certificate.certificate_code}"
    )
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Create PDF
    pdf_buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=(29.7*cm, 21*cm),
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    
    # Custom styles with Arabic font
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles["Title"],
        fontName="Arabic",
        fontSize=32,
        textColor=HexColor("#1a5f7a"),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles["Heading1"],
        fontName="Arabic",
        fontSize=28,
        textColor=HexColor("#159895"),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles["BodyText"],
        fontName="Arabic",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    name_style = ParagraphStyle(
        'StudentName',
        parent=styles["Heading2"],
        fontName="Arabic",
        fontSize=32,
        textColor=HexColor("#570a57"),
        alignment=TA_CENTER,
        spaceAfter=20,
        leading=40
    )
    
    story = []
    story.append(Spacer(1, 1*cm))
    
    # SPACE Z Title
    story.append(Paragraph("SPACE Z", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Decorative line
    decorative_style = ParagraphStyle(
        'Decorative',
        parent=body_style,
        fontSize=10,
        textColor=HexColor("#159895"),
        letterSpacing=5
    )
    story.append(Paragraph("━" * 40, decorative_style))
    story.append(Spacer(1, 1*cm))
    
    # Certificate Title - Arabic
    story.append(Paragraph(reshape_arabic("شهادة إتمام"), heading_style))
    story.append(Paragraph("Certificate of Completion", body_style))
    story.append(Spacer(1, 1.5*cm))
    
    # Main text
    center_style = ParagraphStyle(
        'Center',
        parent=body_style,
        fontSize=16,
        leading=24
    )
    story.append(Paragraph(reshape_arabic("تشهد منصة Space Z بأن"), center_style))
    story.append(Spacer(1, 1*cm))
    
    # Student Name
    student_name = f"{current_user.first_name} {current_user.last_name}"
    story.append(Paragraph(student_name, name_style))
    story.append(Spacer(1, 1*cm))
    
    # Course completion text
    story.append(Paragraph(reshape_arabic("قد أتم بنجاح دراسة الكورس التالي"), center_style))
    story.append(Spacer(1, 0.8*cm))
    
    # Course Title
    course_style = ParagraphStyle(
        'Course',
        parent=body_style,
        fontSize=20,
        textColor=HexColor("#1a5f7a"),
        leading=28
    )
    course_title = course.title if course else "Course Name"
    story.append(Paragraph(f"<b>{course_title}</b>", course_style))
    story.append(Spacer(1, 1.5*cm))
    
    # Issue Date
    issue_date = certificate.issued_at.strftime("%Y/%m/%d")
    date_style = ParagraphStyle(
        'Date',
        parent=body_style,
        fontSize=12,
        textColor=HexColor("#6c757d")
    )
    story.append(Paragraph(reshape_arabic(f"تاريخ الإصدار: {issue_date}"), date_style))
    story.append(Spacer(1, 0.8*cm))
    
    # Certificate Code
    code_style = ParagraphStyle(
        'Code',
        parent=body_style,
        fontSize=12,
        textColor=HexColor("#570a57")
    )
    story.append(Paragraph(reshape_arabic(f"رقم الشهادة: <b>{certificate.certificate_code}</b>"), code_style))
    story.append(Spacer(1, 2*cm))
    
    # QR Code and Signature
    qr_img = Image(qr_buffer, width=3.5*cm, height=3.5*cm)
    
    sig_style = ParagraphStyle(
        'Signature',
        parent=body_style,
        fontSize=11,
        alignment=TA_CENTER
    )
    
    sig_data = [[
        qr_img,
        Paragraph("<br/>", body_style),
        Paragraph(reshape_arabic("____________________") + "<br/>" + reshape_arabic("التوقيع الإلكتروني"), sig_style)
    ]]
    
    sig_table = Table(sig_data, colWidths=[4*cm, 2*cm, 6*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(sig_table)
    story.append(Spacer(1, 1.5*cm))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=body_style,
        fontSize=10,
        textColor=HexColor("#6c757d")
    )
    story.append(Paragraph(reshape_arabic("يمكن التحقق من صحة هذه الشهادة عبر الرابط:"), footer_style))
    
    link_style = ParagraphStyle(
        'Link',
        parent=body_style,
        fontSize=9,
        textColor=HexColor("#159895"),
        wordWrap='RTL'
    )
    story.append(Paragraph(f"https://spacez.edu/verify/{certificate.certificate_code}", link_style))
    
    # Build PDF
    doc.build(story, onFirstPage=add_border, onLaterPages=add_border)
    
    pdf_buffer.seek(0)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{certificate.certificate_code}.pdf"'
        }
    )