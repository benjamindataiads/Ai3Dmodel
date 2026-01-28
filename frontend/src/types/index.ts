export interface BoundingBox {
  x: number
  y: number
  z: number
}

export interface Parameter {
  name: string
  value: number
  unit: string
  line?: number
  min_value?: number
  max_value?: number
}

export interface Part {
  id: string
  project_id: string
  name: string
  code: string | null
  prompt: string | null
  parameters: Parameter[] | null
  bounding_box: BoundingBox | null
  status: 'draft' | 'generated' | 'error'
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  section_id: string | null
  position: number
  created_at: string
  updated_at: string
  parts: PartSummary[]
}

export interface PartSummary {
  id: string
  name: string
  status: string
}

export interface ProjectListItem {
  id: string
  name: string
  description: string | null
  section_id: string | null
  position: number
  created_at: string
  updated_at: string
  parts_count: number
}

export interface Section {
  id: string
  name: string
  color: string | null
  position: number
  projects_count: number
  projects: ProjectListItem[]
  created_at: string
  updated_at: string
}

export interface PrinterPreset {
  id: string
  name: string
  build_volume: BoundingBox
  bed_shape: string
}

export interface ValidationResult {
  fits_build_volume: boolean
  part_dimensions: BoundingBox
  build_volume: BoundingBox
  overflow: BoundingBox
  suggestions: string[]
}

export interface VersionSummary {
  id: string
  source: string
  status: string
  created_at: string
  has_code: boolean
}

export interface Version {
  id: string
  part_id: string
  code: string | null
  prompt: string | null
  parameters: Parameter[] | null
  bounding_box: BoundingBox | null
  status: string
  error_message: string | null
  source: string
  created_at: string
}

export type LLMProvider = 'openai' | 'anthropic'
