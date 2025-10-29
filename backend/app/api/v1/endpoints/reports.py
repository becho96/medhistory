from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from io import BytesIO
import uuid

from app.db.postgres import get_db
from app.models.user import User
from app.models.report import Report
from app.schemas.document import (
    ReportGenerateRequest,
    ReportGenerateResponse
)
from app.services.report_service import ReportService
from app.services.document_service import DocumentService
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    request: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a PDF report based on filters"""
    
    try:
        report = await ReportService.generate_report(
            user_id=current_user.id,
            filters=request.filters,
            db=db
        )
        
        return ReportGenerateResponse(
            report_id=report.id,
            status="completed",
            message="Отчёт успешно сгенерирован"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )

@router.get("/")
async def get_reports(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user reports"""
    
    reports = await ReportService.get_reports(
        user_id=current_user.id,
        db=db,
        skip=skip,
        limit=limit
    )
    
    return reports

@router.get("/{report_id}")
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get report metadata"""
    
    report = await ReportService.get_report_by_id(
        report_id=report_id,
        user_id=current_user.id,
        db=db
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчёт не найден"
        )
    
    return report

@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download report PDF"""
    
    report = await ReportService.get_report_by_id(
        report_id=report_id,
        user_id=current_user.id,
        db=db
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчёт не найден"
        )
    
    # Get file from MinIO
    try:
        file_content = DocumentService.get_file_from_minio(report.file_url)
        
        return StreamingResponse(
            BytesIO(file_content),
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename=medical_report_{report_id}.pdf"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при скачивании отчёта: {str(e)}"
        )

