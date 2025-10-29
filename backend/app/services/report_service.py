import uuid
from datetime import datetime
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.models.report import Report
from app.db.minio_client import minio_client
from app.services.ai_service import ai_service
from app.core.config import settings
from app.schemas.document import ReportFilters

# Import PDF generation libraries
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class ReportService:
    
    @staticmethod
    async def generate_report(
        user_id: uuid.UUID,
        filters: ReportFilters,
        db: AsyncSession
    ) -> Report:
        """Generate PDF report based on filters"""
        
        # Fetch filtered documents
        query = select(Document).where(Document.user_id == user_id)
        
        if filters.document_type:
            query = query.where(Document.document_type == filters.document_type)
        
        if filters.patient_name:
            query = query.where(Document.patient_name == filters.patient_name)
        
        if filters.date_from:
            query = query.where(Document.document_date >= filters.date_from)
        
        if filters.date_to:
            query = query.where(Document.document_date <= filters.date_to)
        
        if filters.medical_facility:
            query = query.where(Document.medical_facility == filters.medical_facility)
        
        query = query.order_by(Document.document_date.asc())
        result = await db.execute(query)
        documents = list(result.scalars().all())
        
        if not documents:
            raise ValueError("Нет документов, соответствующих выбранным фильтрам")
        
        # Generate report text using AI
        report_text = await ai_service.generate_report_content(
            documents,
            filters.dict()
        )
        
        # Create PDF
        pdf_bytes = ReportService._create_pdf(report_text, documents)
        
        # Upload to MinIO
        report_id = uuid.uuid4()
        object_name = f"{user_id}/reports/{report_id}.pdf"
        
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=BytesIO(pdf_bytes),
            length=len(pdf_bytes),
            content_type="application/pdf"
        )
        
        file_url = f"s3://{settings.MINIO_BUCKET}/{object_name}"
        
        # Save report record
        report = Report(
            id=report_id,
            user_id=user_id,
            report_type="medical_history",
            filters_applied=str(filters.dict()),
            file_url=file_url,
            file_size=len(pdf_bytes)
        )
        
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        return report
    
    @staticmethod
    def _create_pdf(text: str, documents: list) -> bytes:
        """Generate PDF from report text"""
        
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF elements
        story = []
        
        # Get default styles
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1F2937',
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("Медицинская История", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Add generation date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor='#6B7280',
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            f"Отчёт сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            date_style
        ))
        story.append(Spacer(1, 0.3 * inch))
        
        # Add report text
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['BodyText'],
            fontSize=11,
            leading=14,
            textColor='#1F2937'
        )
        
        # Split text into paragraphs and add to PDF
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Check if it's a heading (starts with #)
                if para.strip().startswith('#'):
                    para_text = para.replace('#', '').strip()
                    story.append(Paragraph(para_text, styles['Heading2']))
                else:
                    story.append(Paragraph(para.strip(), body_style))
                story.append(Spacer(1, 0.1 * inch))
        
        # Add document list
        story.append(PageBreak())
        story.append(Paragraph("Использованные документы", styles['Heading2']))
        story.append(Spacer(1, 0.2 * inch))
        
        for doc in documents:
            doc_date = doc.document_date.strftime('%d.%m.%Y') if doc.document_date else 'Дата не указана'
            doc_text = f"• {doc_date} - {doc.document_type or 'Тип не указан'} - {doc.medical_facility or 'Учреждение не указано'}"
            story.append(Paragraph(doc_text, body_style))
            story.append(Spacer(1, 0.05 * inch))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    @staticmethod
    async def get_reports(
        user_id: uuid.UUID,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> list[Report]:
        """Get user reports"""
        
        query = select(Report).where(
            Report.user_id == user_id
        ).order_by(Report.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_report_by_id(
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Report:
        """Get report by ID"""
        
        query = select(Report).where(
            Report.id == report_id,
            Report.user_id == user_id
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

