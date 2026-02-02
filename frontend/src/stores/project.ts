import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project, ProjectListItem, Part, Section } from '@/types'
import * as api from '@/services/api'

export const useProjectStore = defineStore('project', () => {
  const sections = ref<Section[]>([])
  const unsectionedProjects = ref<ProjectListItem[]>([])
  const projects = ref<ProjectListItem[]>([])
  const currentProject = ref<Project | null>(null)
  const currentPart = ref<Part | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchSections() {
    try {
      sections.value = await api.getSections()
    } catch (e: any) {
      console.error('Failed to fetch sections:', e)
    }
  }

  async function fetchUnsectionedProjects() {
    try {
      unsectionedProjects.value = await api.getProjects(null, true)
    } catch (e: any) {
      console.error('Failed to fetch unsectioned projects:', e)
    }
  }

  async function fetchAllData() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([
        fetchSections(),
        fetchUnsectionedProjects(),
      ])
      // Also fetch all projects for backward compatibility
      projects.value = await api.getProjects()
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch data'
    } finally {
      loading.value = false
    }
  }

  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      await fetchAllData()
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch projects'
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: string) {
    loading.value = true
    error.value = null
    try {
      currentProject.value = await api.getProject(id)
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch project'
    } finally {
      loading.value = false
    }
  }

  async function createSection(name: string, color?: string) {
    try {
      const section = await api.createSection(name, color)
      await fetchSections()
      return section
    } catch (e: any) {
      error.value = e.message || 'Failed to create section'
      throw e
    }
  }

  async function updateSection(id: string, data: { name?: string; color?: string }) {
    try {
      await api.updateSection(id, data)
      await fetchSections()
    } catch (e: any) {
      error.value = e.message || 'Failed to update section'
      throw e
    }
  }

  async function deleteSection(id: string) {
    try {
      await api.deleteSection(id)
      await fetchAllData()
    } catch (e: any) {
      error.value = e.message || 'Failed to delete section'
      throw e
    }
  }

  async function duplicateSection(id: string) {
    try {
      const section = await api.duplicateSection(id)
      await fetchSections()
      return section
    } catch (e: any) {
      error.value = e.message || 'Failed to duplicate section'
      throw e
    }
  }

  async function createProject(name: string, description?: string, sectionId?: string | null) {
    loading.value = true
    error.value = null
    try {
      const project = await api.createProject(name, description, sectionId)
      await fetchAllData()
      return project
    } catch (e: any) {
      error.value = e.message || 'Failed to create project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.deleteProject(id)
      await fetchAllData()
    } catch (e: any) {
      error.value = e.message || 'Failed to delete project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function duplicateProject(id: string) {
    try {
      const project = await api.duplicateProject(id)
      await fetchAllData()
      return project
    } catch (e: any) {
      error.value = e.message || 'Failed to duplicate project'
      throw e
    }
  }

  async function moveProject(id: string, sectionId?: string | null) {
    try {
      await api.moveProject(id, sectionId)
      await fetchAllData()
    } catch (e: any) {
      error.value = e.message || 'Failed to move project'
      throw e
    }
  }

  async function createPart(projectId: string, name: string) {
    loading.value = true
    error.value = null
    try {
      const part = await api.createPart(projectId, name)
      if (currentProject.value && currentProject.value.id === projectId) {
        await fetchProject(projectId)
      }
      return part
    } catch (e: any) {
      error.value = e.message || 'Failed to create part'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchPart(id: string) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.getPart(id)
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch part'
    } finally {
      loading.value = false
    }
  }

  // Helper to sync part data in the project's parts list
  function syncPartInProject(part: Part | null) {
    if (!part || !currentProject.value) return
    
    const index = currentProject.value.parts.findIndex((p: { id: string }) => p.id === part.id)
    if (index !== -1) {
      // Update the part summary in the project's parts list
      currentProject.value.parts[index] = {
        ...currentProject.value.parts[index],
        name: part.name,
        status: part.status,
      }
    }
  }

  async function updatePartCode(id: string, code: string) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.updatePart(id, { code })
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to update part'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function executePartCode(id: string, code: string) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.executePart(id, code)
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to execute code'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function generateCode(
    partId: string, 
    prompt: string, 
    provider?: string,
    model?: string | null,
    existingCode?: string | null,
    contextParts?: { name: string; code: string }[]
  ) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.generatePartCode(
        partId,
        prompt,
        provider as any,
        model,
        existingCode,
        contextParts
      )
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to generate code'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function generateCodeWithAgents(
    partId: string, 
    prompt: string, 
    provider?: string,
    model?: string | null,
    existingCode?: string | null,
    contextParts?: { name: string; code: string }[]
  ) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.generatePartWithAgents(
        partId,
        prompt,
        provider as any,
        model,
        existingCode,
        contextParts,
        true,  // use optimization
        false  // use review (only with image)
      )
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to generate code with agents'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateParameters(partId: string, parameters: Record<string, number>) {
    loading.value = true
    error.value = null
    try {
      currentPart.value = await api.updatePartParameters(partId, parameters)
      syncPartInProject(currentPart.value)
    } catch (e: any) {
      error.value = e.message || 'Failed to update parameters'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deletePart(id: string) {
    loading.value = true
    error.value = null
    try {
      await api.deletePart(id)
      if (currentProject.value) {
        await fetchProject(currentProject.value.id)
      }
      if (currentPart.value?.id === id) {
        currentPart.value = null
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to delete part'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    sections,
    unsectionedProjects,
    projects,
    currentProject,
    currentPart,
    loading,
    error,
    fetchSections,
    fetchUnsectionedProjects,
    fetchAllData,
    fetchProjects,
    fetchProject,
    createSection,
    updateSection,
    deleteSection,
    duplicateSection,
    createProject,
    deleteProject,
    duplicateProject,
    moveProject,
    createPart,
    fetchPart,
    updatePartCode,
    executePartCode,
    generateCode,
    generateCodeWithAgents,
    updateParameters,
    deletePart,
  }
})
