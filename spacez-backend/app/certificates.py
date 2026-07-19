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
    # جلب البيانات من قاعدة البيانات
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
    
    user = db.query(User).filter(User.id == certificate.user_id).first()
    
    student_name = f"{user.first_name} {user.last_name}" if user else "Student Name"
    course_title = str(course.title) if (course and course.title) else "Voice Acting - Introduction Level"
    
    pdf_buffer = BytesIO()
    
    # إعداد الصفحة A4 بالعرض (Landscape)
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=(29.7 * cm, 21 * cm),
        leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0
    )
    
    # دالة رسم الخلفية والنصوص بالإحداثيات المرفوعة
    def draw_certificate_content(canvas, document):
        canvas.saveState()
        
        # 1. رسم الصورة الخلفية المفرغة المعتمدة
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(base_dir, "assets", "cert_template.png")
        
        if os.path.exists(bg_path):
            canvas.drawImage(bg_path, 0, 0, width=document.pagesize[0], height=document.pagesize[1])
        else:
            canvas.setFillColor(HexColor("#ffffff"))
            canvas.rect(0, 0, document.pagesize[0], document.pagesize[1], fill=1, stroke=0)
        
        # منتصف المنطقة البيضاء المخصصة للكتابة
        center_x = 19.7 * cm
        
        # 2. طباعة اسم الطالب (تم رفعه من 10.4 إلى 11.2)
        canvas.setFont("Helvetica-Bold", 32)
        canvas.setFillColor(HexColor("#0c2d3a"))
        canvas.drawCentredString(center_x, 11.2 * cm, student_name)
        
        # 3. طباعة اسم الكورس (تم رفعه من 7.8 إلى 8.5)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.setFillColor(HexColor("#0c2d3a"))
        canvas.drawCentredString(center_x, 8.5 * cm, course_title)
        
        # 4. طباعة الرقم المرجعي للشهادة أسفل اليمين
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(HexColor("#778c94"))
        canvas.drawRightString(28.2 * cm, 1.4 * cm, f"VA-2026-{certificate.certificate_code[-4:]}")
        
        canvas.restoreState()
        
    # بناء الملف بالاعتماد الصريح على أبعاد الـ Canvas
    doc.build([Spacer(1, 1)], onFirstPage=draw_certificate_content)
    pdf_buffer.seek(0)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificate_{certificate_code}.pdf"'
        }
    )