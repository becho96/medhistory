# MedHistory - Technical Design Document

## Document Info
- **Version:** 1.0
- **Date:** October 15, 2025
- **Authors:** Development Team
- **Status:** Draft

---

## 1. System Overview

### 1.1 Architecture Style
Microservices-oriented architecture with the following components:
- **Frontend:** React SPA (Single Page Application)
- **Backend:** Python FastAPI REST API
- **Database:** PostgreSQL (structured) + MongoDB (unstructured)
- **Object Storage:** MinIO (S3-compatible)
- **AI Processing:** OpenRouter API (Claude VLM)
- **Deployment:** Docker Compose (local → cloud migration)

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         React SPA (Responsive Web App)                 │ │
│  │  - Document Upload UI                                  │ │
│  │  - Timeline Visualization                              │ │
│  │  - Filtering & Search                                  │ │
│  │  - Report Generation                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTPS/REST API
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              FastAPI Backend Service                   │ │
│  │                                                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   Auth       │  │   Document   │  │   Report    │ │ │
│  │  │   Service    │  │   Service    │  │   Service   │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  │                                                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   AI         │  │   Timeline   │  │   User      │ │ │
│  │  │   Service    │  │   Service    │  │   Service   │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                         Data Layer                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PostgreSQL   │  │  MongoDB     │  │  MinIO (S3)      │  │
│  │              │  │              │  │                  │  │
│  │ - Users      │  │ - Document   │  │ - Original Files │  │
│  │ - Documents  │  │   Metadata   │  │ - Generated PDFs │  │
│  │ - Tags       │  │ - Dynamic    │  │                  │  │
│  │              │  │   Parameters │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      OpenRouter API (Claude VLM / Sonnet 4.5)          │ │
│  │      - Document Analysis                               │ │
│  │      - Metadata Extraction                             │ │
│  │      - Report Generation                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI Framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| TanStack Query | 5.x | Data fetching & caching |
| React Router | 6.x | Routing |
| Zustand | 4.x | State management |
| TailwindCSS | 3.x | Styling |
| shadcn/ui | latest | Component library |
| vis-timeline | 7.x | Timeline visualization |
| react-dropzone | 14.x | File upload |
| pdf-lib | 1.x | PDF generation client-side |

### 2.2 Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Programming language |
| FastAPI | 0.104+ | Web framework |
| Pydantic | 2.x | Data validation |
| SQLAlchemy | 2.x | PostgreSQL ORM |
| Motor | 3.x | MongoDB async driver |
| PyMongo | 4.x | MongoDB sync driver |
| MinIO Python SDK | 7.x | Object storage |
| Pillow | 10.x | Image processing |
| PyPDF2 | 3.x | PDF parsing |
| python-docx | 1.x | DOCX parsing |
| httpx | 0.25+ | HTTP client for OpenRouter |
| python-jose | 3.x | JWT tokens |
| passlib | 1.7+ | Password hashing |
| python-multipart | 0.0.6+ | File upload handling |
| ReportLab | 4.x | PDF generation server-side |

### 2.3 Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| Database (Relational) | PostgreSQL 16 | Structured metadata |
| Database (Document) | MongoDB 7 | Dynamic parameters |
| Object Storage | MinIO (latest) | File storage |
| Reverse Proxy | Nginx | Frontend serving, SSL |
| Containerization | Docker + Docker Compose | Orchestration |
| API Gateway | Traefik (optional) | Routing, SSL management |

---

## 3. Database Design

### 3.1 PostgreSQL Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Documents table (core metadata)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File information
    original_filename VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL, -- bytes
    file_type VARCHAR(50) NOT NULL, -- pdf, jpg, png, docx
    file_url TEXT NOT NULL, -- MinIO path
    
    -- Core metadata (extracted by AI)
    document_type VARCHAR(100), -- прием врача, анализ крови, etc.
    specialty VARCHAR(100), -- гастроэнтеролог, кардиолог, etc.
    document_date DATE, -- date of the medical event
    patient_name VARCHAR(255),
    medical_facility VARCHAR(255),
    document_language VARCHAR(10), -- ru, en, etc.
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    ai_confidence_score FLOAT, -- 0.0-1.0
    
    -- MongoDB reference for extended metadata
    mongodb_metadata_id VARCHAR(255), -- ObjectId reference
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_document_type (document_type),
    INDEX idx_specialty (specialty),
    INDEX idx_document_date (document_date),
    INDEX idx_processing_status (processing_status)
);

-- Tags table (for manual and auto tags)
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7), -- hex color #RRGGBB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, name)
);

-- Document tags junction table
CREATE TABLE document_tags (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    is_auto_generated BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (document_id, tag_id)
);

-- Specialties catalog (dynamic, learned from documents)
CREATE TABLE specialties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- NULL for system-wide
    name VARCHAR(100) NOT NULL,
    category VARCHAR(100), -- врачебная специальность, тип анализа, etc.
    icon_name VARCHAR(50), -- icon identifier
    usage_count INTEGER DEFAULT 1,
    
    UNIQUE(user_id, name, category)
);

-- Document types catalog (dynamic)
CREATE TABLE document_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    parent_type_id UUID REFERENCES document_types(id), -- for hierarchy
    icon_name VARCHAR(50),
    color VARCHAR(7),
    usage_count INTEGER DEFAULT 1,
    
    UNIQUE(user_id, name)
);

-- Reports history
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    report_type VARCHAR(100), -- specialty_summary, full_history, etc.
    filters_applied JSONB, -- stored filter parameters
    
    file_url TEXT NOT NULL, -- MinIO path to generated PDF
    file_size INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_reports (user_id, created_at DESC)
);
```

### 3.2 MongoDB Schema

```javascript
// Collection: document_metadata
{
  _id: ObjectId("..."),
  document_id: "uuid-from-postgres",
  user_id: "uuid",
  
  // Dynamic extracted data (varies by document type)
  extracted_data: {
    // For анализ крови
    test_results: [
      {
        parameter: "Гемоглобин",
        value: 145,
        unit: "г/л",
        reference_range: "130-160",
        is_abnormal: false
      },
      // ... more results
    ],
    
    // For прием врача
    diagnosis: {
      primary: "Гастрит хронический",
      icd10_code: "K29.5",
      secondary: []
    },
    prescribed_medications: [
      {
        name: "Омепразол",
        dosage: "20мг",
        frequency: "1 раз в день",
        duration: "30 дней"
      }
    ],
    
    // For МРТ/УЗИ
    imaging_findings: {
      organ: "Печень",
      conclusion: "Без патологических изменений",
      recommendations: "Контроль через 6 месяцев"
    },
    
    // Future: any new structured data
    custom_fields: {}
  },
  
  // Raw AI response for debugging
  ai_response: {
    model: "anthropic/claude-sonnet-4-20250514",
    prompt_tokens: 1200,
    completion_tokens: 450,
    raw_output: "...",
    processing_time_ms: 2340
  },
  
  // Full text extraction (for future search)
  full_text: "extracted text from document...",
  
  created_at: ISODate("2024-10-15T10:30:00Z"),
  updated_at: ISODate("2024-10-15T10:30:00Z")
}

// Indexes
db.document_metadata.createIndex({ "document_id": 1 }, { unique: true })
db.document_metadata.createIndex({ "user_id": 1, "created_at": -1 })
db.document_metadata.createIndex({ "extracted_data.test_results.parameter": 1 }) // future
```

---

## 4. API Design

### 4.1 Authentication Endpoints

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
```

### 4.2 Document Endpoints

```
POST   /api/v1/documents/upload
       - Multipart form data
       - Accepts: file, optional metadata
       - Returns: document_id, processing_status
       - Max size: 20MB

GET    /api/v1/documents
       - Query params: filters, pagination
       - Returns: list of documents with metadata

GET    /api/v1/documents/{document_id}
       - Returns: full document metadata

GET    /api/v1/documents/{document_id}/file
       - Returns: original file (redirect to MinIO presigned URL)

DELETE /api/v1/documents/{document_id}
       - Deletes file + all metadata

PATCH  /api/v1/documents/{document_id}
       - Update manual fields (tags, notes)

POST   /api/v1/documents/{document_id}/reprocess
       - Re-run AI analysis
```

### 4.3 Timeline Endpoints

```
GET    /api/v1/timeline
       - Query params: filters (specialty, document_type, date_range)
       - Returns: timeline data structure

GET    /api/v1/timeline/stats
       - Returns: aggregated statistics
```

### 4.4 Report Endpoints

```
POST   /api/v1/reports/generate
       - Body: filter parameters
       - Returns: report_id, generation_status

GET    /api/v1/reports/{report_id}
       - Returns: report metadata

GET    /api/v1/reports/{report_id}/download
       - Returns: PDF file

GET    /api/v1/reports
       - Returns: list of generated reports
```

### 4.5 Tags & Catalogs Endpoints

```
GET    /api/v1/tags
POST   /api/v1/tags
DELETE /api/v1/tags/{tag_id}

GET    /api/v1/specialties
GET    /api/v1/document-types
```

### 4.6 Example Request/Response

**POST /api/v1/documents/upload**

Request:
```http
POST /api/v1/documents/upload HTTP/1.1
Host: localhost:8000
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="analiz_krovi.pdf"
Content-Type: application/pdf

[binary data]
------WebKitFormBoundary--
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Document uploaded successfully and is being analyzed"
}
```

**GET /api/v1/timeline?specialty=гастроэнтеролог**

Response:
```json
{
  "total_count": 15,
  "date_range": {
    "start": "2020-01-15",
    "end": "2024-10-01"
  },
  "events": [
    {
      "document_id": "...",
      "date": "2024-10-01",
      "document_type": "прием врача",
      "specialty": "гастроэнтеролог",
      "title": "Прием - Гастроэнтеролог",
      "medical_facility": "Клиника Здоровье",
      "icon": "doctor-visit",
      "color": "#4CAF50"
    },
    // ... more events
  ]
}
```

---

## 5. Core Services Implementation

### 5.1 Document Processing Service

**Workflow:**

```python
# document_service.py

class DocumentService:
    def __init__(self, 
                 minio_client, 
                 ai_service, 
                 postgres_db, 
                 mongo_db):
        self.minio = minio_client
        self.ai = ai_service
        self.postgres = postgres_db
        self.mongo = mongo_db
    
    async def upload_and_process(self, file: UploadFile, user_id: str):
        """Main upload workflow"""
        
        # 1. Validate file
        self._validate_file(file)
        
        # 2. Create initial DB record
        doc = await self._create_document_record(file, user_id)
        
        # 3. Upload to MinIO
        file_url = await self._upload_to_minio(file, doc.id)
        await self._update_file_url(doc.id, file_url)
        
        # 4. Trigger async AI processing
        await self._trigger_ai_analysis(doc.id, file_url)
        
        return doc
    
    async def _trigger_ai_analysis(self, document_id: str, file_url: str):
        """Background task for AI processing"""
        try:
            # Update status
            await self._update_status(document_id, "processing")
            
            # Download file from MinIO
            file_bytes = await self.minio.get_object(file_url)
            
            # Call AI service
            metadata = await self.ai.analyze_document(file_bytes)
            
            # Save to PostgreSQL
            await self._update_metadata(document_id, metadata)
            
            # Save extended data to MongoDB
            mongo_id = await self.mongo.insert_one({
                "document_id": document_id,
                "extracted_data": metadata.extended_data,
                "ai_response": metadata.raw_response
            })
            
            # Link MongoDB document
            await self._link_mongodb(document_id, str(mongo_id))
            
            # Update catalogs (specialties, document types)
            await self._update_catalogs(metadata)
            
            # Mark as completed
            await self._update_status(document_id, "completed")
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            await self._update_status(document_id, "failed")
```

### 5.2 AI Service (OpenRouter Integration)

```python
# ai_service.py

class AIService:
    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def analyze_document(self, file_bytes: bytes, file_type: str) -> DocumentMetadata:
        """Analyze document and extract metadata"""
        
        # Prepare file for API
        if file_type in ['jpg', 'jpeg', 'png']:
            file_data = self._encode_image_base64(file_bytes)
            content_type = f"image/{file_type}"
        elif file_type == 'pdf':
            file_data = self._encode_pdf_base64(file_bytes)
            content_type = "application/pdf"
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Build prompt
        prompt = self._build_extraction_prompt()
        
        # API call
        response = await self._call_openrouter({
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url" if file_type in ['jpg', 'jpeg', 'png'] else "document",
                            "image_url": {
                                "url": f"data:{content_type};base64,{file_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1  # low for consistent extraction
        })
        
        # Parse response
        metadata = self._parse_ai_response(response)
        
        return metadata
    
    def _build_extraction_prompt(self) -> str:
        return """
Analyze this medical document and extract the following information in JSON format:

{
  "document_type": "тип документа (прием врача, анализ крови, МРТ, и т.д.)",
  "specialty": "специализация врача или тип исследования",
  "document_date": "дата документа в формате YYYY-MM-DD",
  "patient_name": "ФИО пациента",
  "medical_facility": "название медицинского учреждения",
  "language": "язык документа (ru, en, и т.д.)",
  "confidence": "уверенность в извлечении (0.0-1.0)",
  "summary": "краткое описание документа (2-3 предложения)"
}

Rules:
- If information is not found, use null
- Date format: YYYY-MM-DD
- Be precise and consistent
- For document_type and specialty, use lowercase Russian terminology
- Confidence reflects your certainty in extraction accuracy

Respond ONLY with valid JSON, no additional text.
"""
    
    async def _call_openrouter(self, payload: dict) -> dict:
        """Make API call to OpenRouter"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
```

### 5.3 Report Generation Service

```python
# report_service.py

class ReportService:
    async def generate_report(self, user_id: str, filters: ReportFilters) -> str:
        """Generate PDF report based on filters"""
        
        # 1. Fetch filtered documents
        documents = await self._get_filtered_documents(user_id, filters)
        
        if not documents:
            raise ValueError("No documents match the filters")
        
        # 2. Fetch extended metadata from MongoDB
        extended_data = await self._fetch_mongodb_data(documents)
        
        # 3. Generate report content using AI
        report_text = await self._generate_report_text(documents, extended_data, filters)
        
        # 4. Create PDF
        pdf_bytes = await self._create_pdf(report_text, documents)
        
        # 5. Upload to MinIO
        report_id = str(uuid.uuid4())
        file_url = await self._upload_report(report_id, pdf_bytes)
        
        # 6. Save report record
        await self._save_report_record(user_id, report_id, file_url, filters)
        
        return report_id
    
    async def _generate_report_text(self, documents, extended_data, filters) -> str:
        """Use AI to generate comprehensive report"""
        
        # Prepare context
        context = self._prepare_context(documents, extended_data)
        
        prompt = f"""
Create a comprehensive medical report for a patient based on the following documents:

{context}

The report should:
1. Start with patient information summary
2. Present a chronological timeline of events
3. Include key findings from analyses and examinations
4. Cite specific documents and dates
5. Provide a summary of current health status
6. Be detailed and professional

Format the report in clear sections with headers.
Write in Russian.
"""
        
        response = await self.ai_service.generate_text(prompt)
        return response
    
    async def _create_pdf(self, text: str, documents: list) -> bytes:
        """Generate PDF from report text"""
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        story.append(Paragraph("Медицинская История", styles['Title']))
        story.append(Spacer(1, 12))
        
        # Add report text
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para, styles['BodyText']))
                story.append(Spacer(1, 6))
        
        # Add document list
        story.append(Spacer(1, 12))
        story.append(Paragraph("Использованные документы:", styles['Heading2']))
        for doc in documents:
            doc_text = f"{doc.document_date} - {doc.document_type} - {doc.medical_facility}"
            story.append(Paragraph(doc_text, styles['BodyText']))
        
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
```

---

## 6. Frontend Architecture

### 6.1 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn components
│   │   ├── Layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── Documents/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── DocumentCard.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   └── DocumentFilters.tsx
│   │   ├── Timeline/
│   │   │   ├── TimelineView.tsx
│   │   │   ├── TimelineEvent.tsx
│   │   │   └── TimelineFilters.tsx
│   │   └── Reports/
│   │       ├── ReportGenerator.tsx
│   │       └── ReportHistory.tsx
│   │
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Documents.tsx
│   │   ├── Timeline.tsx
│   │   └── Reports.tsx
│   │
│   ├── services/
│   │   ├── api.ts              # Axios instance
│   │   ├── auth.ts             # Auth API calls
│   │   ├── documents.ts        # Documents API
│   │   ├── timeline.ts         # Timeline API
│   │   └── reports.ts          # Reports API
│   │
│   ├── stores/
│   │   ├── authStore.ts        # Auth state (Zustand)
│   │   ├── documentsStore.ts   # Documents cache
│   │   └── filtersStore.ts     # Filter state
│   │
│   ├── hooks/
│   │   ├── useDocuments.ts     # React Query hook
│   │   ├── useTimeline.ts
│   │   └── useAuth.ts
│   │
│   ├── utils/
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   ├── types/
│   │   ├── document.ts
│   │   ├── user.ts
│   │   └── api.ts
│   │
│   ├── App.tsx
│   └── main.tsx
│
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### 6.2 Key Component Examples

**Timeline Component:**

```typescript
// TimelineView.tsx
import { useEffect, useRef } from 'react';
import { Timeline } from 'vis-timeline/standalone';
import { useTimeline } from '@/hooks/useTimeline';
import { useFiltersStore } from '@/stores/filtersStore';

export function TimelineView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<Timeline | null>(null);
  
  const filters = useFiltersStore(state => state.filters);
  const { data, isLoading } = useTimeline(filters);
  
  useEffect(() => {
    if (!containerRef.current || !data) return;
    
    // Transform API data to vis-timeline format
    const items = data.events.map(event => ({
      id: event.document_id,
      content: event.title,
      start: event.date,
      className: `timeline-${event.document_type}`,
      type: 'point'
    }));
    
    // Initialize timeline
    const timeline = new Timeline(containerRef.current, items, {
      width: '100%',
      height: '600px',
      zoomMin: 1000 * 60 * 60 * 24 * 7, // 1 week
      zoomMax: 1000 * 60 * 60 * 24 * 365 * 10, // 10 years
    });
    
    // Handle click events
    timeline.on('select', (properties) => {
      if (properties.items.length > 0) {
        const docId = properties.items[0];
        // Navigate to document details
        window.location.href = `/documents/${docId}`;
      }
    });
    
    timelineRef.current = timeline;
    
    return () => {
      timeline.destroy();
    };
  }, [data]);
  
  if (isLoading) return <div>Loading timeline...</div>;
  
  return <div ref={containerRef} className="timeline-container" />;
}
```

**Upload Component:**

```typescript
// UploadZone.tsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadDocument } from '@/services/documents';
import { toast } from 'sonner';

export function UploadZone() {
  const queryClient = useQueryClient();
  
  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded successfully!');
    },
    onError: (error) => {
      toast.error(`Upload failed: ${error.message}`);
    }
  });
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach(file => {
      uploadMutation.mutate(file);
    });
  }, [uploadMutation]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 20 * 1024 * 1024, // 20MB
    multiple: true
  });
  
  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        transition-colors
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
      `}
    >
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Drop files here...</p>
      ) : (
        <div>
          <p className="text-lg mb-2">Drag & drop files here</p>
          <p className="text-sm text-gray-500">or click to select files</p>
          <p className="text-xs text-gray-400 mt-2">
            Supported: PDF, JPG, PNG, DOCX (max 20MB)
          </p>
        </div>
      )}
    </div>
  );
}
```

---

## 7. Docker Compose Configuration

```yaml
# docker-compose.yml

version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: medhistory_postgres
    environment:
      POSTGRES_DB: medhistory
      POSTGRES_USER: medhistory_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medhistory_user"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # MongoDB Database
  mongodb:
    image: mongo:7
    container_name: medhistory_mongodb
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: medhistory
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    container_name: medhistory_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: medhistory_backend
    environment:
      DATABASE_URL: postgresql://medhistory_user:${POSTGRES_PASSWORD}@postgres:5432/medhistory
      MONGODB_URL: mongodb://admin:${MONGO_PASSWORD}@mongodb:27017/medhistory?authSource=admin
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      JWT_SECRET: ${JWT_SECRET}
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      mongodb:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: medhistory_frontend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    command: npm run dev
  
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: medhistory_nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  mongodb_data:
  minio_data:
```

**.env file:**
```bash
# Database
POSTGRES_PASSWORD=secure_postgres_password_here
MONGO_PASSWORD=secure_mongo_password_here

# MinIO
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=secure_minio_password_here

# Backend
OPENROUTER_API_KEY=your_openrouter_api_key_here
JWT_SECRET=your_jwt_secret_key_here

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## 8. Deployment & DevOps

### 8.1 Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/medhistory.git
cd medhistory

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
```

### 8.2 Production Deployment Considerations

**Cloud Migration Steps:**
1. Choose cloud provider (AWS, GCP, Azure, DigitalOcean)
2. Set up managed databases (RDS, Cloud SQL)
3. Use S3 or equivalent for object storage
4. Deploy backend on Kubernetes or managed container service
5. Use CDN for frontend (Cloudflare, Vercel)
6. Configure SSL/TLS certificates
7. Set up monitoring (Prometheus, Grafana)
8. Configure backup strategies

**Security Enhancements for Production:**
- Enable HTTPS everywhere
- Implement rate limiting
- Add CORS configuration
- Use secrets management (Vault, AWS Secrets Manager)
- Enable audit logging
- Implement data encryption at rest
- Add WAF (Web Application Firewall)

---

## 9. Testing Strategy

### 9.1 Backend Testing

```python
# tests/test_document_service.py

import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, auth_headers):
    """Test document upload"""
    
    with open("test_files/sample.pdf", "rb") as f:
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "document_id" in data
    assert data["status"] == "processing"

@pytest.mark.asyncio
async def test_get_timeline(client: AsyncClient, auth_headers):
    """Test timeline retrieval"""
    
    response = await client.get(
        "/api/v1/timeline?specialty=гастроэнтеролог",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
```

### 9.2 Frontend Testing

```typescript
// __tests__/UploadZone.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { UploadZone } from '@/components/Documents/UploadZone';

describe('UploadZone', () => {
  it('renders upload area', () => {
    render(<UploadZone />);
    expect(screen.getByText(/drag & drop/i)).toBeInTheDocument();
  });
  
  it('accepts file drops', () => {
    const { container } = render(<UploadZone />);
    const dropzone = container.querySelector('[role="presentation"]');
    
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const event = { dataTransfer: { files: [file] } };
    
    fireEvent.drop(dropzone!, event);
    
    // Assert upload mutation was called
    // (requires mocking)
  });
});
```

---

## 10. Performance Optimization

### 10.1 Database Optimization
- Create appropriate indexes on frequently queried columns
- Use connection pooling (SQLAlchemy async pool)
- Implement query result caching (Redis)
- Partition large tables by date if needed

### 10.2 API Optimization
- Implement response caching with ETags
- Use pagination for list endpoints
- Compress responses (gzip)
- Implement request rate limiting

### 10.3 Frontend Optimization
- Lazy load routes and components
- Implement virtual scrolling for large lists
- Optimize images (WebP, lazy loading)
- Use React.memo for expensive components
- Cache API responses with TanStack Query

### 10.4 File Processing Optimization
- Process files asynchronously (Celery/RQ)
- Implement retry logic for failed API calls
- Cache AI responses to avoid reprocessing
- Compress images before upload

---

## 11. Monitoring & Logging

### 11.1 Application Logging

```python
# logging_config.py

import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Usage
logger.info("Document processed", extra={
    "document_id": doc_id,
    "user_id": user_id,
    "processing_time_ms": elapsed_time
})
```

### 11.2 Metrics to Track
- API response times (p50, p95, p99)
- Error rates by endpoint
- AI processing success rate
- File upload success rate
- Database query performance
- Active users count
- Documents processed per day

---

## 12. Future Enhancements

### Phase 2 Features (Technical Implementation)
- **Structured Data Extraction:** Extend MongoDB schema to store parsed lab results
- **Search Engine:** Integrate Elasticsearch for full-text search
- **Real-time Updates:** WebSocket support for live processing status
- **Background Jobs:** Celery/RQ for async processing

### Phase 3 Features
- **Graph Database:** Neo4j for document relationships
- **Vector Search:** Embeddings for semantic document search
- **Mobile Apps:** React Native or Flutter
- **Offline Mode:** PWA with service workers

---

## 13. Appendices

### A. OpenRouter Model Selection
- **Primary:** `anthropic/claude-sonnet-4-20250514`
- **Alternatives:** `anthropic/claude-opus-4`, `openai/gpt-4-vision-preview`
- **Fallback:** Use cheaper models for retry on failure

### B. Error Handling Matrix

| Error Type | HTTP Code | Client Action | Server Action |
|------------|-----------|---------------|---------------|
| File too large | 413 | Show error message | Reject upload |
| Invalid file type | 400 | Show validation error | Return specific message |
| AI processing failed | 500 | Retry or skip | Log error, notify admin |
| Unauthorized | 401 | Redirect to login | Clear session |
| Rate limit exceeded | 429 | Show wait message | Return retry-after header |

### C. Naming Conventions
- **Python:** `snake_case` for functions/variables, `PascalCase` for classes
- **TypeScript:** `camelCase` for functions/variables, `PascalCase` for components
- **Database:** `snake_case` for tables/columns
- **API endpoints:** `kebab-case` for URL paths

---

## Document Sign-off

This technical design document outlines the complete architecture for MedHistory MVP. Implementation should follow these specifications with flexibility for optimization based on real-world testing.

**Next Steps:**
1. Set up development environment
2. Initialize repositories and project structure
3. Implement core backend services (Week 1-2)
4. Develop frontend components (Week 2-4)
5. Integration testing (Week 4-5)
6. User acceptance testing (Week 5-6)
7. Production deployment (Week 6-7)