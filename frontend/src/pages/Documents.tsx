import { useEffect, useState, useRef, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, FlaskConical, Upload, ChevronLeft, ChevronRight, List, Clock, Brain, X, Maximize2, Minimize2, Search } from 'lucide-react'
import { toast } from 'sonner'
import { Timeline as VisTimeline, DataSet } from 'vis-timeline/standalone'
import { documentsService, type DocumentSearchHit } from '../services/documents'
import UploadModal from '../components/Documents/UploadModal'
import DocumentFilters, { DocumentFilterValues } from '../components/Documents/DocumentFilters'
import InterpretationConfirmModal from '../components/Documents/InterpretationConfirmModal'
import DocumentModal from '../components/Documents/DocumentModal'
import DocumentListItem from '../components/Documents/DocumentListItem'

import type { TimelineEvent } from '../types'
import 'vis-timeline/styles/vis-timeline-graph2d.min.css'

const ITEMS_PER_PAGE = 50

// Custom styles for selected timeline items
const timelineStyles = `
  .vis-item.vis-selected {
    border-width: 3px !important;
    border-style: solid !important;
    box-shadow:
      0 0 0 4px rgba(16, 185, 129, 0.4),
      0 8px 16px rgba(0, 0, 0, 0.25),
      0 4px 8px rgba(0, 0, 0, 0.15) !important;
    z-index: 100 !important;
    transition: all 0.2s ease-in-out !important;
  }

  .vis-item.vis-selected .vis-item-content {
    font-weight: 600 !important;
  }

  .vis-item.vis-dot.vis-selected {
    border-width: 4px !important;
    box-shadow:
      0 0 0 4px rgba(16, 185, 129, 0.4),
      0 8px 16px rgba(0, 0, 0, 0.3),
      0 4px 8px rgba(0, 0, 0, 0.2) !important;
  }
`

type ViewMode = 'list' | 'timeline'

const getDocumentGroupLabel = (dateStr: string | null | undefined, now: Date): string => {
  if (!dateStr) return 'Без даты'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Без даты'

  const sameYear = date.getFullYear() === now.getFullYear()
  const sameMonth = sameYear && date.getMonth() === now.getMonth()
  const sameDay = sameMonth && date.getDate() === now.getDate()

  if (sameDay) return 'Сегодня'
  if (sameMonth) return 'В этом месяце'

  const monthName = date.toLocaleDateString('ru-RU', { month: 'long' })
  const capitalizedMonth = monthName.charAt(0).toUpperCase() + monthName.slice(1)
  return sameYear ? capitalizedMonth : `${capitalizedMonth} ${date.getFullYear()}`
}

// Transform documents to timeline events (unified data transformation)
const transformDocumentsToTimelineEvents = (docs: any[]): TimelineEvent[] => {
  // Color mapping for document types
  const colorMap: Record<string, string> = {
    'прием врача': '#10B981',
    'результаты анализа': '#EF4444',
    'инструментальное исследование': '#0EA5E9',
    'функциональная диагностика': '#8B5CF6',
    'другое': '#6B7280'
  }
  
  return docs.map((doc) => {
    const docTypeLower = (doc.document_type || '').toLowerCase()
    
    // Build title with specialty
    let title = doc.document_type || 'Документ'
    if (doc.specialty) {
      title += ` - ${doc.specialty}`
    }
    
    return {
      document_id: doc.id,
      date: doc.document_date || new Date().toISOString(),
      document_type: doc.document_type,
      document_subtype: doc.document_subtype,
      specialty: doc.specialty,
      title: title,
      medical_facility: doc.medical_facility,
      icon: 'document',
      color: colorMap[docTypeLower] || '#6B7280',
      file_url: doc.file_url,
      original_filename: doc.original_filename,
      summary: doc.summary,
    } as TimelineEvent
  })
}

export default function Documents() {
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [filters, setFilters] = useState<DocumentFilterValues>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<'document_date' | 'created_at'>('document_date')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [openLabsFor, setOpenLabsFor] = useState<string | null>(null)
  const [labsByDoc, setLabsByDoc] = useState<Record<string, Array<{ test_name: string; value: string; unit?: string | null; reference_range?: string | null; flag?: string | null }>>>({})
  const [labsSummary, setLabsSummary] = useState<Record<string, { has_labs: boolean; count: number }>>({})
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)

  // Semantic search: input, debounced query, and result query
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setSearchQuery(searchInput.trim()), 400)
    return () => clearTimeout(t)
  }, [searchInput])

  const { data: searchResults, isFetching: isSearching } = useQuery<DocumentSearchHit[]>({
    queryKey: ['documents-search', searchQuery],
    queryFn: () => documentsService.searchDocuments(searchQuery, 20),
    enabled: searchQuery.length > 0,
  })
  const isSearchActive = searchQuery.length > 0

  // Timeline-specific state
  const timelineRef = useRef<HTMLDivElement>(null)
  const timelineInstance = useRef<VisTimeline | null>(null)
  const fullscreenTimelineRef = useRef<HTMLDivElement>(null)
  const fullscreenTimelineInstance = useRef<VisTimeline | null>(null)
  const eventsMapRef = useRef<Map<string, TimelineEvent>>(new Map())
  const tooltipRef = useRef<HTMLDivElement | null>(null)
  const [lastSelectedDocumentId, setLastSelectedDocumentId] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const timelineStateRef = useRef<{ range: { start: Date; end: Date } | null }>({ range: null })
  
  // Interpretation mode state
  const [interpretationMode, setInterpretationMode] = useState(false)
  const interpretationModeRef = useRef(false)
  const [selectedDocumentsForInterpretation, setSelectedDocumentsForInterpretation] = useState<Set<string>>(new Set())
  const [showInterpretationConfirmModal, setShowInterpretationConfirmModal] = useState(false)

  // Query for paginated documents (for List view)
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', filters, currentPage, sortBy],
    queryFn: () =>
      documentsService.getDocuments({
        skip: (currentPage - 1) * ITEMS_PER_PAGE,
        limit: ITEMS_PER_PAGE,
        document_type: filters.document_type,
        patient_name: filters.patient_name,
        medical_facility: filters.medical_facility,
        specialties: filters.specialties,
        document_subtype: filters.document_subtype,
        research_area: filters.research_area,
        date_from: filters.date_from,
        date_to: filters.date_to,
        created_from: filters.created_from,
        created_to: filters.created_to,
        sort_by: sortBy,
      }),
  })

  // Query for total documents count
  const { data: totalCount = 0 } = useQuery({
    queryKey: ['documents-count', filters],
    queryFn: () =>
      documentsService.getDocumentsCount({
        document_type: filters.document_type,
        patient_name: filters.patient_name,
        medical_facility: filters.medical_facility,
        specialties: filters.specialties,
        document_subtype: filters.document_subtype,
        research_area: filters.research_area,
        date_from: filters.date_from,
        date_to: filters.date_to,
        created_from: filters.created_from,
        created_to: filters.created_to,
      }),
  })

  // Query for ALL filtered documents (for Timeline view) - using the SAME endpoint and filters
  const { data: allDocuments, isLoading: isTimelineLoading } = useQuery({
    queryKey: ['documents-all', filters],
    queryFn: async () => {
      console.log('📡 Загрузка всех документов для timeline с фильтрами:', filters)
      const result = await documentsService.getDocuments({
        skip: 0,
        limit: 10000, // Get all documents for timeline
        document_type: filters.document_type,
        patient_name: filters.patient_name,
        medical_facility: filters.medical_facility,
        specialties: filters.specialties,
        document_subtype: filters.document_subtype,
        research_area: filters.research_area,
        date_from: filters.date_from,
        date_to: filters.date_to,
        created_from: filters.created_from,
        created_to: filters.created_to,
        sort_by: 'document_date', // Sort by document date for timeline
      })
      console.log('📦 Получено документов для timeline:', result?.length || 0)
      return result
    },
  })
  
  // Сбросить страницу при изменении фильтров или сортировки
  useEffect(() => {
    setCurrentPage(1)
  }, [filters, sortBy])

  // Calculate total pages
  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)

  const deleteMutation = useMutation({
    mutationFn: documentsService.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['documents-count'] })
      queryClient.invalidateQueries({ queryKey: ['documents-all'] })
      toast.success('Документ удалён')
    },
    onError: () => {
      toast.error('Ошибка при удалении документа')
    },
  })

  // Preload labs summary for listed documents (only for "Результаты анализа")
  useEffect(() => {
    if (!Array.isArray(documents)) return
    const controller = new AbortController()
    const load = async () => {
      for (const d of documents) {
        // Only load summary for lab result documents
        if (d.document_type === 'Результаты анализа') {
          try {
            const summary = await documentsService.getLabsSummary(d.id)
            setLabsSummary((prev) => ({ ...prev, [d.id]: summary }))
          } catch (_) {}
        }
      }
    }
    load()
    return () => controller.abort()
  }, [documents])

  const openLabsModal = async (docId: string) => {
    setOpenLabsFor(docId)
    if (!labsByDoc[docId]) {
      try {
        const data = await documentsService.getLabs(docId)
        setLabsByDoc((prev) => ({ ...prev, [docId]: data.lab_results }))
      } catch (_) {
        toast.error('Не удалось получить извлеченные анализы')
      }
    }
  }
  const closeLabsModal = () => setOpenLabsFor(null)

  const handleDownload = (docId: string, filename: string) => {
    const url = documentsService.getDocumentFileUrl(docId)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Create timeline data from documents (using the same filtered data)
  const timelineData = useMemo(() => {
    console.log('🔄 Создание timeline данных из allDocuments:', allDocuments?.length || 0, 'документов')
    
    if (!allDocuments || allDocuments.length === 0) {
      console.log('⚠️ allDocuments пустой или undefined')
      return null
    }
    
    const events = transformDocumentsToTimelineEvents(allDocuments)
    console.log('✅ Создано событий для timeline:', events.length)
    
    return {
      total_count: allDocuments.length,
      date_range: {
        start: allDocuments.reduce((min, doc) => 
          doc.document_date && (!min || doc.document_date < min) ? doc.document_date : min, 
          null as string | null
        ) || new Date().toISOString(),
        end: allDocuments.reduce((max, doc) => 
          doc.document_date && (!max || doc.document_date > max) ? doc.document_date : max, 
          null as string | null
        ) || new Date().toISOString(),
      },
      events: events
    }
  }, [allDocuments])

  // Helper function to create tooltip HTML for timeline
  const createTooltipHTML = (event: TimelineEvent): string => {
    const parts: string[] = []
    
    parts.push(`<div style="font-weight: 600; margin-bottom: 8px; color: #111827;">${event.title}</div>`)
    
    if (event.date) {
      const dateStr = new Date(event.date).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Дата:</strong> ${dateStr}</div>`)
    }
    
    if (event.document_type) {
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Тип:</strong> ${event.document_type}</div>`)
    }
    
    if (event.document_subtype) {
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Подтип:</strong> ${event.document_subtype}</div>`)
    }
    
    if (event.specialty) {
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Специализация:</strong> ${event.specialty}</div>`)
    }
    
    if (event.medical_facility) {
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Учреждение:</strong> ${event.medical_facility}</div>`)
    }
    
    if (event.original_filename) {
      parts.push(`<div style="margin-bottom: 4px; color: #4B5563;"><strong>Файл:</strong> ${event.original_filename}</div>`)
    }
    
    if (event.summary) {
      const safeSummary = event.summary.length > 400 ? event.summary.slice(0, 400) + '…' : event.summary
      parts.push(`<div style="margin-top: 8px; color: #1F2937;"><strong>Summary:</strong> ${safeSummary}</div>`)
    }
    
    parts.push(`<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #E5E7EB; color: #059669; font-size: 0.875rem;">
      <strong>Нажмите, чтобы открыть детали документа</strong>
    </div>`)
    
    return parts.join('')
  }

  // Update interpretation mode ref when state changes
  useEffect(() => {
    interpretationModeRef.current = interpretationMode
  }, [interpretationMode])

  // Timeline visualization effect
  useEffect(() => {
    if (!timelineRef.current || !timelineData || !timelineData.events || viewMode !== 'timeline') {
      // Clean up timeline if switching away from timeline view
      if (viewMode !== 'timeline' && timelineInstance.current) {
        timelineInstance.current.destroy()
        timelineInstance.current = null
      }
      return
    }

    // Reset selection when data changes
    setLastSelectedDocumentId(null)

    // Store events in a map for quick access
    eventsMapRef.current.clear()
    timelineData.events.forEach((event) => {
      eventsMapRef.current.set(event.document_id, event)
    })

    // Create custom tooltip element if it doesn't exist
    if (!tooltipRef.current) {
      tooltipRef.current = document.createElement('div')
      tooltipRef.current.className = 'custom-timeline-tooltip'
      tooltipRef.current.style.cssText = `
        position: fixed;
        display: none;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px;
        max-width: 300px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        z-index: 9999;
        pointer-events: none;
        font-family: Inter, system-ui, sans-serif;
        font-size: 14px;
        line-height: 1.5;
      `
      document.body.appendChild(tooltipRef.current)
    }

    // Transform data to vis-timeline format
    const items = new DataSet(
      timelineData.events.map((event) => {
        // Function to get emoji for document type
        const getDocumentTypeEmoji = (docType: string | undefined, docSubtype: string | undefined): string => {
          if (!docType) return '📄'
          
          const typeLower = docType.toLowerCase()
          
          // Результаты анализа - different emoji based on subtype
          if (typeLower.includes('анализ')) {
            if (docSubtype) {
              const subtypeLower = docSubtype.toLowerCase()
              if (subtypeLower.includes('кров')) return '🩸'
              if (subtypeLower.includes('моч')) return '💦'
              if (subtypeLower.includes('кал')) return '💩'
              if (subtypeLower.includes('гормон')) return '🧪'
              if (subtypeLower.includes('генетич') || subtypeLower.includes('днк')) return '🧬'
              if (subtypeLower.includes('микробиолог') || subtypeLower.includes('бактериолог')) return '🦠'
              if (subtypeLower.includes('аллерг')) return '🤧'
            }
            return '🔬' // Default for lab tests
          }
          
          // Инструментальное исследование
          if (typeLower.includes('инструментальн')) {
            if (docSubtype) {
              const subtypeLower = docSubtype.toLowerCase()
              if (subtypeLower.includes('узи')) return '🔊'
              if (subtypeLower.includes('мрт') || subtypeLower.includes('кт') || subtypeLower.includes('томограф')) return '🧲'
              if (subtypeLower.includes('рентген') || subtypeLower.includes('флюорограф')) return '☢️'
              if (subtypeLower.includes('экг') || subtypeLower.includes('электрокардиограф')) return '💓'
              if (subtypeLower.includes('эндоскоп') || subtypeLower.includes('гастроскоп') || subtypeLower.includes('колоноскоп')) return '🔍'
            }
            return '🏥'
          }
          
          // Прием врача
          if (typeLower.includes('прием') || typeLower.includes('врач')) return '👨‍⚕️'
          
          // Функциональная диагностика
          if (typeLower.includes('функциональн') || typeLower.includes('диагностик')) return '📊'
          
          // Другое
          return '📄'
        }
        
        const emoji = getDocumentTypeEmoji(event.document_type, event.document_subtype)
        
        // Create multi-line content with document type, subtype, and specialty
        let contentHTML = `<div style="line-height: 1.4;">`
        
        // Main document type - larger and bold for primary focus with emoji
        contentHTML += `<div style="font-size: 12px; font-weight: 700;">${emoji} ${event.document_type || 'Документ'}</div>`
        
        // Secondary info - subtype and specialty with smaller font
        if (event.document_subtype) {
          contentHTML += `<div style="font-size: 10px; color: #6B7280; margin-top: 3px;">Подтип: ${event.document_subtype}</div>`
        }
        
        if (event.specialty) {
          contentHTML += `<div style="font-size: 10px; color: #6B7280; margin-top: 2px;">Специализация: ${event.specialty}</div>`
        }
        
        contentHTML += `</div>`
        
        return {
          id: event.document_id,
          content: contentHTML,
          start: event.date || new Date(),
          type: 'point',
          className: 'timeline-item',
          style: `background-color: ${event.color}; border-color: ${event.color};`,
        }
      })
    )

    // Create or update timeline
    // Always recreate if container dimensions are not valid (e.g., after fullscreen exit)
    const container = timelineRef.current
    const needsRecreate = !timelineInstance.current || 
      !container || 
      container.offsetWidth === 0 || 
      container.offsetHeight === 0
    
    if (needsRecreate) {
      // Destroy existing instance if it exists
      if (timelineInstance.current) {
        timelineInstance.current.destroy()
        timelineInstance.current = null
      }
      
      // Wait a bit for container to be ready
      setTimeout(() => {
        if (timelineRef.current && timelineData && timelineData.events.length > 0) {
          timelineInstance.current = new VisTimeline(timelineRef.current, items, {
            width: '100%',
            height: '600px',
            zoomMin: 1000 * 60 * 60 * 24 * 7, // 1 week
            zoomMax: 1000 * 60 * 60 * 24 * 365 * 10, // 10 years
            locale: 'ru',
            orientation: 'top',
            stack: true,
            showCurrentTime: false,
            multiselect: true, // Always enable multiselect
          })
          
          // Setup event handlers
          setupTimelineEventHandlers()
          
          // Fit to data
          if (timelineData.events.length > 0) {
            timelineInstance.current.fit()
          }
        }
      }, 100)
    } else if (timelineInstance.current) {
      // Update items and force redraw
      timelineInstance.current.setItems(items)
      // Setup event handlers
      setupTimelineEventHandlers()
      // Force redraw after a short delay to ensure DOM is ready
      setTimeout(() => {
        if (timelineInstance.current && timelineData.events.length > 0) {
          timelineInstance.current.redraw()
          timelineInstance.current.fit()
        }
      }, 100)
    }
    
    // Helper function to setup event handlers
    function setupTimelineEventHandlers() {
      if (!timelineInstance.current) return
      
      // Remove all existing select event listeners
      timelineInstance.current.off('select')
      
      // Add select event handler with current mode
      timelineInstance.current.on('select', (properties: any) => {
        if (properties.items.length > 0) {
          // Use ref to get current mode value
          if (interpretationModeRef.current) {
            // In interpretation mode: update selection
            setSelectedDocumentsForInterpretation(new Set(properties.items))
          } else {
            // Normal mode: open document details (only single selection)
            const docId = properties.items[0]
            const event = eventsMapRef.current.get(docId)
            if (event) {
              setLastSelectedDocumentId(docId)
              setSelectedDocumentId(docId)
            }
          }
        } else {
          // Deselection
          if (interpretationModeRef.current) {
            setSelectedDocumentsForInterpretation(new Set())
          }
        }
      })
    }

    // Add mouse event listeners for custom tooltip
    const timelineContainer = timelineRef.current
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!tooltipRef.current || !timelineInstance.current) return
      
      try {
        if (typeof timelineInstance.current.getEventProperties === 'function') {
          const props = timelineInstance.current.getEventProperties(e as any)
          
          if (props && props.item !== null && props.item !== undefined) {
            const itemId = String(props.item)
            const event = eventsMapRef.current.get(itemId)
            
            if (event) {
              tooltipRef.current.innerHTML = createTooltipHTML(event)
              tooltipRef.current.style.display = 'block'
              tooltipRef.current.style.left = `${e.clientX + 15}px`
              tooltipRef.current.style.top = `${e.clientY + 15}px`
              return
            }
          }
        }
        
        const target = e.target as HTMLElement
        const visItem = target.closest('.vis-item')
        
        if (visItem) {
          const itemId = visItem.getAttribute('data-item-id') || 
                        visItem.getAttribute('data-id') ||
                        visItem.className.match(/vis-item-(\d+)/)?.[1]
          
          if (itemId) {
            const event = eventsMapRef.current.get(itemId)
            
            if (event) {
              tooltipRef.current.innerHTML = createTooltipHTML(event)
              tooltipRef.current.style.display = 'block'
              tooltipRef.current.style.left = `${e.clientX + 15}px`
              tooltipRef.current.style.top = `${e.clientY + 15}px`
              return
            }
          }
        }
        
        tooltipRef.current.style.display = 'none'
        
      } catch (error) {
        console.error('Tooltip error:', error)
      }
    }
    
    const handleMouseLeave = () => {
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none'
      }
    }
    
    timelineContainer.addEventListener('mousemove', handleMouseMove)
    timelineContainer.addEventListener('mouseleave', handleMouseLeave)

    // Fit timeline to data and ensure it's visible
    if (timelineData.events.length > 0) {
      // Use setTimeout to ensure DOM is ready
      setTimeout(() => {
        if (timelineInstance.current && timelineRef.current) {
          timelineInstance.current.fit()
          timelineInstance.current.redraw()
        }
      }, 50)
    }

    return () => {
      timelineContainer.removeEventListener('mousemove', handleMouseMove)
      timelineContainer.removeEventListener('mouseleave', handleMouseLeave)
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none'
      }
    }
  }, [allDocuments, viewMode, timelineData, interpretationMode])

  // Fullscreen timeline visualization effect
  useEffect(() => {
    if (!fullscreenTimelineRef.current || !timelineData || !timelineData.events || !isFullscreen) {
      // Clean up if fullscreen is closed
      if (!isFullscreen && fullscreenTimelineInstance.current) {
        fullscreenTimelineInstance.current.destroy()
        fullscreenTimelineInstance.current = null
      }
      return
    }

    // Store events in a map for quick access (reuse the same map)
    eventsMapRef.current.clear()
    timelineData.events.forEach((event) => {
      eventsMapRef.current.set(event.document_id, event)
    })

    // Transform data to vis-timeline format (same as regular timeline)
    const items = new DataSet(
      timelineData.events.map((event) => {
        const getDocumentTypeEmoji = (docType: string | undefined, docSubtype: string | undefined): string => {
          if (!docType) return '📄'
          const typeLower = docType.toLowerCase()
          
          if (typeLower.includes('анализ')) {
            if (docSubtype) {
              const subtypeLower = docSubtype.toLowerCase()
              if (subtypeLower.includes('кров')) return '🩸'
              if (subtypeLower.includes('моч')) return '💦'
              if (subtypeLower.includes('кал')) return '💩'
              if (subtypeLower.includes('гормон')) return '🧪'
              if (subtypeLower.includes('генетич') || subtypeLower.includes('днк')) return '🧬'
              if (subtypeLower.includes('микробиолог') || subtypeLower.includes('бактериолог')) return '🦠'
              if (subtypeLower.includes('аллерг')) return '🤧'
            }
            return '🔬'
          }
          
          if (typeLower.includes('инструментальн')) {
            if (docSubtype) {
              const subtypeLower = docSubtype.toLowerCase()
              if (subtypeLower.includes('узи')) return '🔊'
              if (subtypeLower.includes('мрт') || subtypeLower.includes('кт') || subtypeLower.includes('томограф')) return '🧲'
              if (subtypeLower.includes('рентген') || subtypeLower.includes('флюорограф')) return '☢️'
              if (subtypeLower.includes('экг') || subtypeLower.includes('электрокардиограф')) return '💓'
              if (subtypeLower.includes('эндоскоп') || subtypeLower.includes('гастроскоп') || subtypeLower.includes('колоноскоп')) return '🔍'
            }
            return '🏥'
          }
          
          if (typeLower.includes('прием') || typeLower.includes('врач')) return '👨‍⚕️'
          if (typeLower.includes('функциональн') || typeLower.includes('диагностик')) return '📊'
          return '📄'
        }
        
        const emoji = getDocumentTypeEmoji(event.document_type, event.document_subtype)
        
        let contentHTML = `<div style="line-height: 1.4;">`
        contentHTML += `<div style="font-size: 12px; font-weight: 700;">${emoji} ${event.document_type || 'Документ'}</div>`
        
        if (event.document_subtype) {
          contentHTML += `<div style="font-size: 10px; color: #6B7280; margin-top: 3px;">Подтип: ${event.document_subtype}</div>`
        }
        
        if (event.specialty) {
          contentHTML += `<div style="font-size: 10px; color: #6B7280; margin-top: 2px;">Специализация: ${event.specialty}</div>`
        }
        
        contentHTML += `</div>`
        
        return {
          id: event.document_id,
          content: contentHTML,
          start: event.date || new Date(),
          type: 'point',
          className: 'timeline-item',
          style: `background-color: ${event.color}; border-color: ${event.color};`,
        }
      })
    )

    // Always recreate timeline instance for fullscreen to ensure clean state
    // Destroy existing instance if it exists
    if (fullscreenTimelineInstance.current) {
      fullscreenTimelineInstance.current.destroy()
      fullscreenTimelineInstance.current = null
    }

    // Create new timeline instance
    fullscreenTimelineInstance.current = new VisTimeline(fullscreenTimelineRef.current, items, {
      width: '100%',
      height: '100%', // Will be set via container height
      zoomMin: 1000 * 60 * 60 * 24 * 7, // 1 week
      zoomMax: 1000 * 60 * 60 * 24 * 365 * 10, // 10 years
      locale: 'ru',
      orientation: 'top',
      stack: true,
      showCurrentTime: false,
      multiselect: true,
    })
    
    // Restore saved state if available
    if (timelineStateRef.current.range) {
      fullscreenTimelineInstance.current.setWindow(
        timelineStateRef.current.range.start,
        timelineStateRef.current.range.end
      )
    } else if (timelineData.events.length > 0) {
      fullscreenTimelineInstance.current.fit()
    }

    // Remove all existing select event listeners
    fullscreenTimelineInstance.current.off('select')
    
    // Add select event handler
    fullscreenTimelineInstance.current.on('select', (properties: any) => {
      if (properties.items.length > 0) {
        if (interpretationModeRef.current) {
          setSelectedDocumentsForInterpretation(new Set(properties.items))
        } else {
          const docId = properties.items[0]
          const event = eventsMapRef.current.get(docId)
          if (event) {
            setLastSelectedDocumentId(docId)
            setSelectedDocumentId(docId)
          }
        }
      } else {
        if (interpretationModeRef.current) {
          setSelectedDocumentsForInterpretation(new Set())
        }
      }
    })

    // Add mouse event listeners for custom tooltip
    const timelineContainer = fullscreenTimelineRef.current
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!tooltipRef.current || !fullscreenTimelineInstance.current) return
      
      try {
        if (typeof fullscreenTimelineInstance.current.getEventProperties === 'function') {
          const props = fullscreenTimelineInstance.current.getEventProperties(e as any)
          
          if (props && props.item !== null && props.item !== undefined) {
            const itemId = String(props.item)
            const event = eventsMapRef.current.get(itemId)
            
            if (event) {
              tooltipRef.current.innerHTML = createTooltipHTML(event)
              tooltipRef.current.style.display = 'block'
              tooltipRef.current.style.left = `${e.clientX + 15}px`
              tooltipRef.current.style.top = `${e.clientY + 15}px`
              return
            }
          }
        }
        
        const target = e.target as HTMLElement
        const visItem = target.closest('.vis-item')
        
        if (visItem) {
          const itemId = visItem.getAttribute('data-item-id') || 
                        visItem.getAttribute('data-id') ||
                        visItem.className.match(/vis-item-(\d+)/)?.[1]
          
          if (itemId) {
            const event = eventsMapRef.current.get(itemId)
            
            if (event) {
              tooltipRef.current.innerHTML = createTooltipHTML(event)
              tooltipRef.current.style.display = 'block'
              tooltipRef.current.style.left = `${e.clientX + 15}px`
              tooltipRef.current.style.top = `${e.clientY + 15}px`
              return
            }
          }
        }
        
        tooltipRef.current.style.display = 'none'
      } catch (error) {
        console.error('Tooltip error:', error)
      }
    }
    
    const handleMouseLeave = () => {
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none'
      }
    }
    
    timelineContainer.addEventListener('mousemove', handleMouseMove)
    timelineContainer.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      timelineContainer.removeEventListener('mousemove', handleMouseMove)
      timelineContainer.removeEventListener('mouseleave', handleMouseLeave)
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none'
      }
    }
  }, [isFullscreen, timelineData, interpretationMode])

  // Restore selection after closing modal (for timeline) - only in normal mode
  useEffect(() => {
    if (!interpretationMode && !selectedDocumentId && lastSelectedDocumentId && timelineInstance.current) {
      timelineInstance.current.setSelection([lastSelectedDocumentId])
    }
  }, [selectedDocumentId, lastSelectedDocumentId, interpretationMode])
  
  // Clear timeline selection when exiting interpretation mode
  useEffect(() => {
    if (!interpretationMode && timelineInstance.current) {
      timelineInstance.current.setSelection([])
    }
  }, [interpretationMode])

  // Inject custom styles for timeline selection
  useEffect(() => {
    const styleElement = document.createElement('style')
    styleElement.id = 'timeline-custom-styles'
    styleElement.innerHTML = timelineStyles
    document.head.appendChild(styleElement)

    return () => {
      const existingStyle = document.getElementById('timeline-custom-styles')
      if (existingStyle) {
        document.head.removeChild(existingStyle)
      }
    }
  }, [])

  // Cleanup tooltip and timeline on unmount
  useEffect(() => {
    return () => {
      if (tooltipRef.current && document.body.contains(tooltipRef.current)) {
        document.body.removeChild(tooltipRef.current)
        tooltipRef.current = null
      }
      if (timelineInstance.current) {
        timelineInstance.current.destroy()
        timelineInstance.current = null
      }
      if (fullscreenTimelineInstance.current) {
        fullscreenTimelineInstance.current.destroy()
        fullscreenTimelineInstance.current = null
      }
    }
  }, [])

  // Handle Escape key for exiting fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      }
    }
    
    if (isFullscreen) {
      document.addEventListener('keydown', handleEscape)
      // Prevent body scroll when fullscreen
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      if (!isFullscreen) {
        document.body.style.overflow = ''
      }
    }
  }, [isFullscreen])

  // Functions for fullscreen mode
  const enterFullscreen = () => {
    // Save current timeline state (range/zoom)
    if (timelineInstance.current) {
      const range = timelineInstance.current.getWindow()
      timelineStateRef.current = { range }
    }
    setIsFullscreen(true)
  }

  const exitFullscreen = () => {
    // Save fullscreen timeline state before exiting
    if (fullscreenTimelineInstance.current) {
      const range = fullscreenTimelineInstance.current.getWindow()
      timelineStateRef.current = { range }
      
      // Destroy fullscreen timeline instance to ensure clean re-initialization
      fullscreenTimelineInstance.current.destroy()
      fullscreenTimelineInstance.current = null
    }
    setIsFullscreen(false)
    
    // Force regular timeline to redraw after exiting fullscreen
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
      if (timelineInstance.current && timelineRef.current && timelineData && timelineData.events.length > 0) {
        timelineInstance.current.redraw()
        // Restore saved state if available
        if (timelineStateRef.current.range) {
          timelineInstance.current.setWindow(
            timelineStateRef.current.range.start,
            timelineStateRef.current.range.end
          )
        } else {
          timelineInstance.current.fit()
        }
      }
    }, 200)
  }

  // Все фильтры применяются на сервере
  const filteredDocuments = documents

  // Группировка документов по календарным периодам (для текущей страницы)
  const groupedDocuments = useMemo(() => {
    if (!filteredDocuments || filteredDocuments.length === 0) return []
    const now = new Date()
    const groups: Array<{ label: string; docs: typeof filteredDocuments }> = []
    for (const doc of filteredDocuments) {
      const dateField = sortBy === 'created_at' ? doc.created_at : doc.document_date
      const label = getDocumentGroupLabel(dateField, now)
      const last = groups[groups.length - 1]
      if (last && last.label === label) {
        last.docs.push(doc)
      } else {
        groups.push({ label, docs: [doc] })
      }
    }
    return groups
  }, [filteredDocuments, sortBy])

  return (
    <div className="space-y-3 sm:space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-semibold text-gray-900 tracking-tight">Медкарта</h1>
          <p className="text-[13px] text-gray-500 hidden sm:block mt-0.5">
            Управляйте вашими медицинскими документами
          </p>
        </div>
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="flex min-h-11 min-w-11 items-center justify-center gap-2 px-3 py-2.5 sm:px-5 sm:py-2.5 bg-emerald-500 text-white rounded-xl font-medium text-[14px] hover:bg-emerald-600 transition-colors flex-shrink-0"
          aria-label="Загрузить документы"
        >
          <Upload className="h-4 w-4 flex-shrink-0" />
          <span className="hidden sm:inline">Загрузить документы</span>
        </button>
      </div>

      {/* Filters */}
      <DocumentFilters
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters({})}
        sortBy={sortBy}
        onSortChange={setSortBy}
      />

      {/* Semantic search */}
      <div className="bg-white rounded-2xl border border-gray-100 p-3 sm:p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Поиск по смыслу"
            className="w-full pl-9 pr-9 py-2.5 text-[14px] border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label="Очистить поиск"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {isSearchActive && (
          <div className="mt-3">
            {isSearching ? (
              <p className="text-[13px] text-gray-500 px-1 py-3">Ищу…</p>
            ) : !searchResults || searchResults.length === 0 ? (
              <p className="text-[13px] text-gray-500 px-1 py-3">
                По запросу «{searchQuery}» ничего не найдено. Попробуйте переформулировать.
              </p>
            ) : (
              <>
                <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider px-1 mb-2">
                  Найдено по смыслу: {searchResults.length}
                </p>
                <ul className="divide-y divide-gray-100 border border-gray-100 rounded-xl overflow-hidden">
                  {searchResults.map((hit) => (
                    <li
                      key={hit.document_id}
                      onClick={() => setSelectedDocumentId(hit.document_id)}
                      className="px-3 sm:px-4 py-3 hover:bg-gray-50 cursor-pointer"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 text-[12px] text-gray-500 mb-1">
                            {hit.document_type && <span className="font-medium">{hit.document_type}</span>}
                            {hit.document_date && <span>· {new Date(hit.document_date).toLocaleDateString('ru-RU')}</span>}
                            {hit.medical_facility && <span className="hidden sm:inline truncate">· {hit.medical_facility}</span>}
                          </div>
                          <p className="text-[14px] text-gray-700 line-clamp-1 sm:line-clamp-2">{hit.snippet || '—'}</p>
                        </div>
                        <span className="hidden sm:inline flex-shrink-0 text-[11px] font-mono text-gray-400 mt-1">
                          {(hit.score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>

      {/* View Mode Tabs */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="hidden border-b border-gray-100 lg:block">
          <nav className="flex gap-2 p-2">
            <button
              onClick={() => setViewMode('list')}
              className={`
                flex items-center gap-1.5 sm:gap-2 px-3 sm:px-6 py-2 sm:py-2.5 rounded-xl font-medium text-[13px] sm:text-[14px] transition-colors flex-1 sm:flex-initial justify-center
                ${viewMode === 'list'
                  ? 'bg-emerald-500 text-white'
                  : 'text-gray-600 hover:bg-gray-50'
                }
              `}
            >
              <List className="h-4 w-4" />
              Список
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={`
                hidden lg:flex items-center gap-1.5 sm:gap-2 px-3 sm:px-6 py-2 sm:py-2.5 rounded-xl font-medium text-[13px] sm:text-[14px] transition-colors sm:flex-initial justify-center
                ${viewMode === 'timeline'
                  ? 'bg-emerald-500 text-white'
                  : 'text-gray-600 hover:bg-gray-50'
                }
              `}
            >
              <Clock className="h-4 w-4" />
              Timeline
            </button>
          </nav>
        </div>

        {/* List View */}
        {viewMode === 'list' && (
          <>
            <div className="hidden px-3 sm:px-6 py-3 border-b border-gray-100 lg:block">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[13px] font-medium text-gray-500">
                  {totalCount} {totalCount === 1 ? 'документ' : totalCount < 5 ? 'документа' : 'документов'}
                </p>
                <div className="flex rounded-xl border border-gray-200 overflow-hidden text-[12px] font-medium">
                  <button
                    onClick={() => setSortBy('document_date')}
                    className={`min-h-11 px-2.5 py-2 transition-colors ${
                      sortBy === 'document_date'
                        ? 'bg-emerald-500 text-white'
                        : 'bg-white text-gray-600'
                    }`}
                  >
                    По документу
                  </button>
                  <button
                    onClick={() => setSortBy('created_at')}
                    className={`min-h-11 px-2.5 py-2 border-l border-gray-200 transition-colors ${
                      sortBy === 'created_at'
                        ? 'bg-emerald-500 text-white'
                        : 'bg-white text-gray-600'
                    }`}
                  >
                    По загрузке
                  </button>
                </div>
              </div>
            </div>

            {/* Top Pagination */}
            {totalPages > 1 && (
              <div className="hidden px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-100 bg-gray-50/50">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0">
                  <div>
                    <p className="text-xs sm:text-sm text-gray-600">
                      <span className="hidden sm:inline">Страница </span>
                      <span className="font-semibold text-gray-900">{currentPage}</span> / <span className="font-semibold text-gray-900">{totalPages}</span>
                      <span className="mx-1 sm:mx-2">•</span>
                      <span className="hidden sm:inline">Показано </span>
                      <span className="font-semibold text-gray-900">{filteredDocuments?.length || 0}</span> / <span className="font-semibold text-gray-900">{totalCount}</span>
                    </p>
                  </div>
                  <div>
                    <nav className="inline-flex rounded-lg shadow-sm" aria-label="Pagination">
                      <button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="relative inline-flex min-h-11 min-w-11 items-center justify-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-l-lg border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="h-4 w-4 sm:h-5 sm:w-5" />
                      </button>
                      <span className="relative inline-flex min-h-11 items-center px-3 sm:px-4 py-1.5 sm:py-2 border-t border-b border-gray-200 bg-white text-xs sm:text-sm font-semibold text-gray-700">
                        {currentPage} / {totalPages}
                      </span>
                      <button
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        disabled={currentPage >= totalPages}
                        className="relative inline-flex min-h-11 min-w-11 items-center justify-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-r-lg border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5" />
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            )}

            <div>
          {isLoading ? (
            <div className="py-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto"></div>
            </div>
          ) : groupedDocuments.length > 0 ? (
            groupedDocuments.map((group) => (
              <section key={group.label}>
                <h3 className="sticky top-0 z-10 px-3 sm:px-4 py-1.5 bg-gray-50/95 backdrop-blur border-y border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {group.label}
                </h3>
                <div className="divide-y divide-gray-50">
                  {group.docs.map((doc) => (
                    <DocumentListItem
                      key={doc.id}
                      doc={doc}
                      labsSummary={labsSummary}
                      showTags={true}
                      onClick={(id) => setSelectedDocumentId(id)}
                      onOpenLabs={(id) => openLabsModal(id)}
                      onDownload={(id, filename) => handleDownload(id, filename)}
                      onDelete={(id) => {
                        if (window.confirm('Удалить этот документ?')) {
                          deleteMutation.mutate(id)
                        }
                      }}
                    />
                  ))}
                </div>
              </section>
            ))
          ) : (
            <div className="py-12 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-gray-50 flex items-center justify-center">
                <FileText className="h-6 w-6 text-gray-300" />
              </div>
              <p className="text-[15px] font-medium text-gray-900 mb-1">Нет документов</p>
              <p className="text-[13px] text-gray-500 mb-5 px-4">
                Загрузите ваш первый медицинский документ
              </p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 text-white rounded-xl font-medium text-[14px] hover:bg-emerald-600 transition-colors"
              >
                <Upload className="h-4 w-4" />
                Загрузить документ
              </button>
            </div>
          )}
          </div>
        
          {/* Bottom Pagination */}
          {totalPages > 1 && (
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-100 bg-gray-50/50">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">
                    <span className="hidden sm:inline">Страница </span>
                    <span className="font-semibold text-gray-900">{currentPage}</span> / <span className="font-semibold text-gray-900">{totalPages}</span>
                    <span className="mx-1 sm:mx-2">•</span>
                    <span className="hidden sm:inline">Показано </span>
                    <span className="font-semibold text-gray-900">{filteredDocuments?.length || 0}</span> / <span className="font-semibold text-gray-900">{totalCount}</span>
                  </p>
                </div>
                <div>
                  <nav className="inline-flex rounded-lg shadow-sm" aria-label="Pagination">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex min-h-11 min-w-11 items-center justify-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-l-lg border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="h-4 w-4 sm:h-5 sm:w-5" />
                    </button>
                    <span className="relative inline-flex min-h-11 items-center px-3 sm:px-4 py-1.5 sm:py-2 border-t border-b border-gray-200 bg-white text-xs sm:text-sm font-semibold text-gray-700">
                      {currentPage} / {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      className="relative inline-flex min-h-11 min-w-11 items-center justify-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-r-lg border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="h-4 w-4 sm:h-5 sm:w-5" />
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
          </>
        )}

        {/* Timeline View */}
        {viewMode === 'timeline' && (
          <>
            <div className="p-3 sm:p-6">
              {/* Interpretation mode controls */}
              <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
                    События ({timelineData?.total_count || 0})
                    {interpretationMode && selectedDocumentsForInterpretation.size > 0 && (
                      <span className="ml-2 text-sm sm:text-base font-normal text-emerald-600">
                        (Выбрано: {selectedDocumentsForInterpretation.size})
                      </span>
                    )}
                  </h3>
                  {timelineData?.date_range && (
                    <p className="text-xs sm:text-sm text-gray-500 mt-1">
                      Период: {new Date(timelineData.date_range.start).toLocaleDateString('ru-RU')}{' '}
                      - {new Date(timelineData.date_range.end).toLocaleDateString('ru-RU')}
                    </p>
                  )}
                </div>
                
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  {!interpretationMode ? (
                    <button
                      onClick={() => setInterpretationMode(true)}
                      className="inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 font-medium text-xs sm:text-sm transition-colors shadow-sm w-full sm:w-auto"
                    >
                      <Brain className="h-4 w-4 sm:h-5 sm:w-5" />
                      <span className="hidden sm:inline">Интерпретировать анализы</span>
                      <span className="sm:hidden">Интерпретировать</span>
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setInterpretationMode(false)
                          setSelectedDocumentsForInterpretation(new Set())
                          if (timelineInstance.current) {
                            timelineInstance.current.setSelection([])
                          }
                        }}
                        className="inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium text-xs sm:text-sm transition-colors"
                      >
                        <X className="h-4 w-4 sm:h-5 sm:w-5" />
                        Отмена
                      </button>
                      <button
                        onClick={() => setShowInterpretationConfirmModal(true)}
                        disabled={selectedDocumentsForInterpretation.size === 0}
                        className="inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 font-medium text-xs sm:text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none flex-1 sm:flex-initial"
                      >
                        <Brain className="h-4 w-4 sm:h-5 sm:w-5" />
                        Отправить ({selectedDocumentsForInterpretation.size})
                      </button>
                    </>
                  )}
                </div>
              </div>
              
              {interpretationMode && (
                <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-purple-50 border border-purple-200 rounded-xl">
                  <p className="text-xs sm:text-sm text-purple-900">
                    <strong>Режим выбора документов для интерпретации:</strong> Нажмите на документы на таймлайне, чтобы выбрать их. 
                    <span className="hidden sm:inline"> Вы можете выбрать несколько документов, зажав Ctrl (Cmd на Mac) и кликая по документам.</span>
                  </p>
                </div>
              )}
              
              {isTimelineLoading ? (
                <div className="flex items-center justify-center h-96">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
                </div>
              ) : timelineData && timelineData.events.length > 0 ? (
                <div className="relative">
                  <div ref={timelineRef} className="timeline-container rounded-xl overflow-hidden"></div>
                  <button
                    onClick={enterFullscreen}
                    className="absolute top-2 right-2 p-2 bg-white/90 hover:bg-white border border-gray-200 rounded-lg shadow-md hover:shadow-lg transition-all z-10 text-gray-600 hover:text-gray-900"
                    title="Полноэкранный режим"
                  >
                    <Maximize2 className="h-5 w-5" />
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-96">
                  <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                    <Clock className="h-8 w-8 text-gray-400" />
                  </div>
                  <p className="text-lg font-semibold text-gray-900">Нет событий для отображения</p>
                  <p className="text-sm text-gray-500 mt-2">Загрузите документы, чтобы увидеть их на временной шкале</p>
                </div>
              )}
            </div>

            {/* Legend */}
            {timelineData && timelineData.events.length > 0 && (
              <div className="px-3 sm:px-6 pb-3 sm:pb-6">
                <h3 className="text-xs sm:text-sm font-semibold text-gray-900 mb-2 sm:mb-3">Легенда</h3>
                <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
                  <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-lg bg-gray-50">
                    <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-green-500 flex-shrink-0"></div>
                    <span className="text-xs sm:text-sm text-gray-700">Прием врача</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-lg bg-gray-50">
                    <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-red-500 flex-shrink-0"></div>
                    <span className="text-xs sm:text-sm text-gray-700">Анализ крови</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-lg bg-gray-50">
                    <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-sky-500 flex-shrink-0"></div>
                    <span className="text-xs sm:text-sm text-gray-700">УЗИ/МРТ</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-lg bg-gray-50">
                    <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-purple-500 flex-shrink-0"></div>
                    <span className="text-xs sm:text-sm text-gray-700">Другое</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Fullscreen Timeline Modal */}
      {isFullscreen && (
        <div 
          className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm"
          onClick={(e) => {
            // Exit fullscreen when clicking outside the timeline container
            if (e.target === e.currentTarget) {
              exitFullscreen()
            }
          }}
        >
          <div className="h-full flex flex-col bg-white">
            {/* Header */}
            <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-white shadow-sm">
              <div className="flex items-center gap-3">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
                  Таймлайн - Полноэкранный режим
                </h3>
                {timelineData?.date_range && (
                  <p className="text-xs sm:text-sm text-gray-500 hidden sm:inline">
                    Период: {new Date(timelineData.date_range.start).toLocaleDateString('ru-RU')}{' '}
                    - {new Date(timelineData.date_range.end).toLocaleDateString('ru-RU')}
                  </p>
                )}
              </div>
              
              <div className="flex items-center gap-2">
                {interpretationMode && (
                  <div className="flex items-center gap-2 mr-2">
                    <button
                      onClick={() => {
                        setInterpretationMode(false)
                        setSelectedDocumentsForInterpretation(new Set())
                        if (fullscreenTimelineInstance.current) {
                          fullscreenTimelineInstance.current.setSelection([])
                        }
                      }}
                      className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium text-xs sm:text-sm transition-colors"
                    >
                      <X className="h-4 w-4" />
                      Отмена
                    </button>
                    <button
                      onClick={() => setShowInterpretationConfirmModal(true)}
                      disabled={selectedDocumentsForInterpretation.size === 0}
                      className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 font-medium text-xs sm:text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Brain className="h-4 w-4" />
                      Отправить ({selectedDocumentsForInterpretation.size})
                    </button>
                  </div>
                )}
                <button
                  onClick={exitFullscreen}
                  className="p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
                  title="Выйти из полноэкранного режима (Esc)"
                >
                  <Minimize2 className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Timeline Container */}
            <div className="flex-1 overflow-hidden p-4 sm:p-6">
              {isTimelineLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
                </div>
              ) : timelineData && timelineData.events.length > 0 ? (
                <div 
                  ref={fullscreenTimelineRef} 
                  className="timeline-container rounded-xl overflow-hidden"
                  style={{ height: 'calc(100vh - 80px)' }}
                  onClick={(e) => e.stopPropagation()}
                ></div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                    <Clock className="h-8 w-8 text-gray-400" />
                  </div>
                  <p className="text-lg font-semibold text-gray-900">Нет событий для отображения</p>
                  <p className="text-sm text-gray-500 mt-2">Загрузите документы, чтобы увидеть их на временной шкале</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Labs Modal */}
      {openLabsFor && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl sm:rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden max-h-[90vh] flex flex-col">
            <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-gray-100 flex items-center justify-between bg-white">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <FlaskConical className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600" />
                </div>
                <h4 className="text-base sm:text-xl font-semibold text-gray-900">Извлеченные анализы</h4>
              </div>
              <button 
                onClick={closeLabsModal}
                className="p-1.5 sm:p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-3 sm:p-6 overflow-auto flex-1">
              {labsByDoc[openLabsFor] && labsByDoc[openLabsFor].length > 0 ? (
                <div className="overflow-x-auto rounded-lg sm:rounded-xl border border-gray-100">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Аналит</th>
                        <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Значение</th>
                        <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider hidden sm:table-cell">Ед.</th>
                        <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider hidden md:table-cell">Референс</th>
                        <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Флаг</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {labsByDoc[openLabsFor].map((r, idx) => (
                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm font-medium text-gray-900">{r.test_name}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm font-semibold text-gray-900">{r.value}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm text-gray-600 hidden sm:table-cell">{r.unit || '-'}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm text-gray-600 hidden md:table-cell">{r.reference_range || '-'}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm">
                            <span className={`inline-flex items-center px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded-full text-xs font-semibold ${
                              r.flag === 'H' ? 'bg-red-100 text-red-700' :
                              r.flag === 'L' ? 'bg-yellow-100 text-yellow-700' :
                              r.flag === 'A' ? 'bg-purple-100 text-purple-700' :
                              'bg-green-100 text-green-700'
                            }`}>
                              {r.flag || 'N'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-8 sm:py-12 text-center">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                    <FlaskConical className="h-6 w-6 sm:h-8 sm:w-8 text-gray-400" />
                  </div>
                  <p className="text-xs sm:text-sm text-gray-500">Нет извлеченных анализов</p>
                </div>
              )}
            </div>
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-100 flex justify-end bg-gray-50">
              <button 
                onClick={closeLabsModal}
                className="px-3 sm:px-4 py-1.5 sm:py-2 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg text-xs sm:text-sm font-medium text-gray-700 transition-colors"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
      
      {/* Interpretation Confirm Modal */}
      <InterpretationConfirmModal
        isOpen={showInterpretationConfirmModal}
        onClose={() => {
          setShowInterpretationConfirmModal(false)
          setInterpretationMode(false)
          setSelectedDocumentsForInterpretation(new Set())
          if (timelineInstance.current) {
            timelineInstance.current.setSelection([])
          }
        }}
        selectedDocuments={
          Array.from(selectedDocumentsForInterpretation).map(docId => {
            const event = eventsMapRef.current.get(docId)
            return {
              id: docId,
              original_filename: event?.original_filename || 'Документ',
              document_date: event?.date,
              document_type: event?.document_type
            }
          })
        }
      />

      {/* Document Details Modal */}
      <DocumentModal
        documentId={selectedDocumentId}
        onClose={() => setSelectedDocumentId(null)}
      />
    </div>
  )
}
