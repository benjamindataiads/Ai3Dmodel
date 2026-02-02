import axios from 'axios'
import type {
  Project,
  ProjectListItem,
  Part,
  PrinterPreset,
  ValidationResult,
  BoundingBox,
  LLMProvider,
  Section,
  VersionSummary,
  Version,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Sections
export async function getSections(): Promise<Section[]> {
  const response = await api.get('/sections')
  return response.data
}

export async function createSection(name: string, color?: string): Promise<Section> {
  const response = await api.post('/sections', { name, color })
  return response.data
}

export async function updateSection(id: string, data: { name?: string; color?: string; position?: number }): Promise<Section> {
  const response = await api.patch(`/sections/${id}`, data)
  return response.data
}

export async function deleteSection(id: string): Promise<void> {
  await api.delete(`/sections/${id}`)
}

export async function duplicateSection(id: string): Promise<Section> {
  const response = await api.post(`/sections/${id}/duplicate`)
  return response.data
}

// Projects
export async function getProjects(sectionId?: string | null, unsectioned?: boolean): Promise<ProjectListItem[]> {
  const params: Record<string, any> = {}
  if (sectionId) params.section_id = sectionId
  if (unsectioned) params.unsectioned = true
  const response = await api.get('/projects', { params })
  return response.data
}

export async function getProject(id: string): Promise<Project> {
  const response = await api.get(`/projects/${id}`)
  return response.data
}

export async function createProject(name: string, description?: string, sectionId?: string | null): Promise<Project> {
  const response = await api.post('/projects', { name, description, section_id: sectionId })
  return response.data
}

export async function updateProject(id: string, data: { name?: string; description?: string; section_id?: string | null; position?: number }): Promise<Project> {
  const response = await api.put(`/projects/${id}`, data)
  return response.data
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`)
}

export async function duplicateProject(id: string): Promise<Project> {
  const response = await api.post(`/projects/${id}/duplicate`)
  return response.data
}

export async function moveProject(id: string, sectionId?: string | null, position?: number): Promise<Project> {
  const response = await api.patch(`/projects/${id}/move`, { 
    section_id: sectionId,
    position 
  })
  return response.data
}

// Parts
export async function createPart(projectId: string, name: string, code?: string): Promise<Part> {
  const response = await api.post(`/projects/${projectId}/parts`, { name, code })
  return response.data
}

export async function getPart(id: string): Promise<Part> {
  const response = await api.get(`/parts/${id}`)
  return response.data
}

export async function updatePart(id: string, data: { name?: string; code?: string }): Promise<Part> {
  const response = await api.put(`/parts/${id}`, data)
  return response.data
}

export async function executePart(id: string, code: string): Promise<Part> {
  const response = await api.post(`/parts/${id}/execute`, { code })
  return response.data
}

export async function autosavePart(id: string, code: string): Promise<Part> {
  const response = await api.post(`/parts/${id}/autosave`, { code })
  return response.data
}

export async function deletePart(id: string): Promise<void> {
  await api.delete(`/parts/${id}`)
}

// Import 3D files
export async function importFile(projectId: string, file: File): Promise<Part> {
  const formData = new FormData()
  formData.append('project_id', projectId)
  formData.append('file', file)
  
  const response = await api.post('/import/file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export interface ImportedMesh {
  vertices: number[][]
  faces: number[][]
  source_file: string
}

export async function getImportedMesh(partId: string): Promise<ImportedMesh> {
  const response = await api.get(`/import/mesh/${partId}`)
  return response.data
}

// Versions
export async function getPartVersions(partId: string): Promise<VersionSummary[]> {
  const response = await api.get(`/versions/part/${partId}`)
  return response.data
}

export async function getVersion(versionId: string): Promise<Version> {
  const response = await api.get(`/versions/${versionId}`)
  return response.data
}

export async function restoreVersion(versionId: string): Promise<Version> {
  const response = await api.post(`/versions/${versionId}/restore`)
  return response.data
}

// AI Generation
export interface ModelInfo {
  id: string
  name: string
}

export interface ProviderModels {
  models: ModelInfo[]
  default: string
}

export interface AvailableModels {
  openai: ProviderModels
  anthropic: ProviderModels
}

export async function getAvailableModels(): Promise<AvailableModels> {
  const response = await api.get('/models')
  return response.data
}

export async function generatePartCode(
  partId: string,
  prompt: string,
  provider?: LLMProvider,
  model?: string | null,
  existingCode?: string | null,
  contextParts?: { name: string; code: string }[]
): Promise<Part> {
  const response = await api.post(`/parts/${partId}/generate`, { 
    prompt, 
    provider,
    model: model || undefined,
    existing_code: existingCode || undefined,
    context_parts: contextParts || undefined
  })
  return response.data
}

// Parameters
export async function getPartParameters(id: string): Promise<{ parameters: any[]; bounding_box: BoundingBox | null }> {
  const response = await api.get(`/parts/${id}/parameters`)
  return response.data
}

export async function updatePartParameters(id: string, parameters: Record<string, number>): Promise<Part> {
  const response = await api.put(`/parts/${id}/parameters`, { parameters })
  return response.data
}

// Validation
export async function validatePart(id: string, buildVolume: BoundingBox): Promise<ValidationResult> {
  const response = await api.post(`/parts/${id}/validate`, { build_volume: buildVolume })
  return response.data
}

// Export
export function getPreviewUrl(partId: string): string {
  return `/api/parts/${partId}/preview`
}

export function getExportStlUrl(partId: string): string {
  return `/api/parts/${partId}/export/stl`
}

export function getExport3mfUrl(partId: string): string {
  return `/api/parts/${partId}/export/3mf`
}

export function getProjectExport3mfUrl(projectId: string): string {
  return `/api/projects/${projectId}/export/3mf`
}

// Printers
export async function getPrinterPresets(): Promise<PrinterPreset[]> {
  const response = await api.get('/printers/presets')
  return response.data
}

// Assembly AI
export interface PartPositionInfo {
  id: string
  name: string
  bounding_box: BoundingBox
  current_position: {
    x: number
    y: number
    z: number
    rotX: number
    rotY: number
    rotZ: number
  }
}

export interface PartPosition {
  x: number
  y: number
  z: number
  rotX: number
  rotY: number
  rotZ: number
}

export interface AssemblyResponse {
  positions: Record<string, PartPosition>
}

export async function generateAssemblyPositions(
  prompt: string,
  parts: PartPositionInfo[],
  provider?: LLMProvider,
  model?: string | null
): Promise<AssemblyResponse> {
  const response = await api.post('/assembly/position', {
    prompt,
    parts,
    provider,
    model: model || undefined
  })
  return response.data
}

// Project generation
export interface GeneratedPartInfo {
  name: string
  description: string
  status: string
  error?: string
}

export interface ProjectGenerateResponse {
  project_id: string
  project_name: string
  parts: GeneratedPartInfo[]
}

export async function generateProject(
  prompt: string,
  provider?: LLMProvider,
  model?: string | null
): Promise<ProjectGenerateResponse> {
  const response = await api.post('/projects/generate', {
    prompt,
    provider,
    model: model || undefined
  })
  return response.data
}

export interface ImageData {
  data: string
  mime_type: string
  name: string
}

export async function generateProjectWithImages(
  prompt: string,
  images: ImageData[],
  provider?: LLMProvider,
  model?: string | null
): Promise<ProjectGenerateResponse> {
  const response = await api.post('/projects/generate-with-images', {
    prompt,
    images,
    provider,
    model: model || undefined
  })
  return response.data
}

// Agent-based generation
export interface AgentMessage {
  role: string
  content: string
  data: Record<string, any>
}

export interface AgentGenerateResponse {
  success: boolean
  code: string | null
  bounding_box: BoundingBox | null
  validation: {
    valid: boolean
    errors: string[]
    warnings: string[]
  } | null
  suggestions: string[]
  iterations: number
  messages: AgentMessage[]
  error: string | null
}

export async function generatePartWithAgents(
  partId: string,
  prompt: string,
  provider?: LLMProvider,
  model?: string | null,
  existingCode?: string | null,
  contextParts?: { name: string; code: string }[],
  useOptimization: boolean = true,
  useReview: boolean = false,
  printerSettings?: Record<string, any>
): Promise<Part> {
  const response = await api.post(`/parts/${partId}/generate-with-agents`, {
    prompt,
    provider,
    model: model || undefined,
    existing_code: existingCode || undefined,
    context_parts: contextParts || undefined,
    use_optimization: useOptimization,
    use_review: useReview,
    printer_settings: printerSettings || undefined
  })
  return response.data
}

export async function generatePartWithImage(
  partId: string,
  prompt: string,
  image: File,
  provider?: LLMProvider,
  model?: string | null,
  useOptimization: boolean = true
): Promise<Part> {
  const formData = new FormData()
  formData.append('prompt', prompt)
  formData.append('image', image)
  if (provider) formData.append('provider', provider)
  if (model) formData.append('model', model)
  formData.append('use_optimization', String(useOptimization))
  
  const response = await api.post(`/parts/${partId}/generate-with-image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export interface ImageAnalysis {
  shape_description: string
  estimated_dimensions: {
    length: number
    width: number
    height: number
  }
  features: string[]
  complexity: 'simple' | 'medium' | 'complex'
  suggested_primitives: string[]
  printability_notes: string
  recommended_approach: string
}

export async function analyzeImageForDesign(
  image: File,
  prompt?: string,
  provider?: LLMProvider,
  model?: string | null
): Promise<{ success: boolean; analysis: ImageAnalysis | { raw_response: string } }> {
  const formData = new FormData()
  formData.append('image', image)
  if (prompt) formData.append('prompt', prompt)
  if (provider) formData.append('provider', provider)
  if (model) formData.append('model', model)
  
  const response = await api.post('/analyze-image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export default api
