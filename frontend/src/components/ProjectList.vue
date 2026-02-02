<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { importFile, createProject as apiCreateProject } from '@/services/api'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()

// UI State
const showNewProjectModal = ref(false)
const showNewSectionModal = ref(false)
const showImportModal = ref(false)
const selectedSectionId = ref<string | null>(null)

// Form state
const newProjectName = ref('')
const newProjectDescription = ref('')
const newSectionName = ref('')
const newSectionColor = ref('#06b6d4')

// Import state
const importFile1 = ref<File | null>(null)
const importProjectName = ref('')
const importing = ref(false)
const importError = ref<string | null>(null)
const importDragOver = ref(false)

// Context menu state
const contextMenu = ref<{ show: boolean; x: number; y: number; type: 'section' | 'project'; id: string } | null>(null)

const createError = ref<string | null>(null)
const creating = ref(false)

const sectionColors = ['#06b6d4', '#f97316', '#22c55e', '#8b5cf6', '#ec4899', '#eab308']

// Refresh data on mount
onMounted(() => {
  store.fetchProjects()
})

// Watch for route changes to refresh when navigating back to this page
watch(
  () => route.path,
  (newPath) => {
    if (newPath === '/') {
      store.fetchProjects()
    }
  }
)

// Get projects for display - either by section or unsectioned
const displayedProjects = computed(() => {
  if (selectedSectionId.value === null) {
    return store.unsectionedProjects
  }
  const section = store.sections.find(s => s.id === selectedSectionId.value)
  return section?.projects || []
})

const currentSectionName = computed(() => {
  if (selectedSectionId.value === null) return 'Sans section'
  const section = store.sections.find(s => s.id === selectedSectionId.value)
  return section?.name || 'Sans section'
})

async function createProject() {
  if (!newProjectName.value.trim() || creating.value) return
  
  creating.value = true
  createError.value = null
  
  try {
    const project = await store.createProject(
      newProjectName.value.trim(),
      newProjectDescription.value.trim() || undefined,
      selectedSectionId.value
    )
    
    if (!project || !project.id) {
      throw new Error('Projet créé mais ID manquant')
    }
    
    showNewProjectModal.value = false
    newProjectName.value = ''
    newProjectDescription.value = ''
    router.push(`/project/${project.id}`)
  } catch (e: any) {
    console.error('Failed to create project:', e)
    createError.value = e.message || 'Erreur lors de la création du projet'
  } finally {
    creating.value = false
  }
}

async function createSection() {
  if (!newSectionName.value.trim()) return
  
  try {
    await store.createSection(newSectionName.value.trim(), newSectionColor.value)
    showNewSectionModal.value = false
    newSectionName.value = ''
    newSectionColor.value = '#06b6d4'
  } catch (e: any) {
    console.error('Failed to create section:', e)
  }
}

// Import functions
function handleFileDrop(e: DragEvent) {
  e.preventDefault()
  importDragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    handleFileSelect(files[0])
  }
}

function handleFileSelect(file: File) {
  const allowedExtensions = ['.stl', '.obj', '.3mf']
  const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
  
  if (!allowedExtensions.includes(ext)) {
    importError.value = `Format non supporté. Formats acceptés: ${allowedExtensions.join(', ')}`
    return
  }
  
  importFile1.value = file
  importError.value = null
  
  // Auto-fill project name from filename
  if (!importProjectName.value) {
    importProjectName.value = file.name.replace(/\.[^/.]+$/, '')
  }
}

function handleFileInputChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    handleFileSelect(target.files[0])
  }
}

async function handleImport() {
  if (!importFile1.value || !importProjectName.value.trim() || importing.value) return
  
  importing.value = true
  importError.value = null
  
  try {
    // Create project first
    const project = await apiCreateProject(
      importProjectName.value.trim(),
      `Imported from: ${importFile1.value.name}`,
      selectedSectionId.value
    )
    
    // Import the file as a part
    await importFile(project.id, importFile1.value)
    
    // Refresh projects list
    await store.fetchProjects()
    
    // Close modal and navigate
    showImportModal.value = false
    importFile1.value = null
    importProjectName.value = ''
    
    router.push(`/project/${project.id}`)
  } catch (e: any) {
    console.error('Failed to import file:', e)
    importError.value = e.response?.data?.detail || e.message || 'Erreur lors de l\'import'
  } finally {
    importing.value = false
  }
}

function resetImportModal() {
  importFile1.value = null
  importProjectName.value = ''
  importError.value = null
  importing.value = false
}

function showContextMenu(e: MouseEvent, type: 'section' | 'project', id: string) {
  e.preventDefault()
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, type, id }
}

function hideContextMenu() {
  contextMenu.value = null
}

async function handleContextAction(action: string) {
  if (!contextMenu.value) return
  
  const { type, id } = contextMenu.value
  hideContextMenu()
  
  if (type === 'section') {
    if (action === 'duplicate') {
      await store.duplicateSection(id)
    } else if (action === 'delete') {
      if (confirm('Supprimer cette section ? Les projets seront déplacés vers "Sans section".')) {
        await store.deleteSection(id)
        if (selectedSectionId.value === id) {
          selectedSectionId.value = null
        }
      }
    }
  } else if (type === 'project') {
    if (action === 'duplicate') {
      const newProject = await store.duplicateProject(id)
      if (newProject) {
        router.push(`/project/${newProject.id}`)
      }
    } else if (action === 'delete') {
      if (confirm('Supprimer ce projet ?')) {
        await store.deleteProject(id)
      }
    } else if (action === 'move') {
      // Move to unsectioned or show move dialog
      await store.moveProject(id, null)
    }
  }
}

async function deleteProject(id: string) {
  if (confirm('Êtes-vous sûr de vouloir supprimer ce projet ?')) {
    await store.deleteProject(id)
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
</script>

<template>
  <div class="h-[calc(100vh-57px)] flex bg-dark-950" @click="hideContextMenu">
    <!-- Left Sidebar - Sections -->
    <div class="w-64 glass border-r border-white/5 flex flex-col">
      <div class="p-4 border-b border-white/5">
        <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Sections</h2>
      </div>
      
      <div class="flex-1 overflow-y-auto p-2">
        <!-- Unsectioned -->
        <button
          @click="selectedSectionId = null"
          :class="[
            'w-full text-left px-3 py-2.5 rounded-xl mb-1 transition-all flex items-center gap-3',
            selectedSectionId === null
              ? 'bg-cyber-500/10 text-cyber-400 border border-cyber-500/30'
              : 'text-slate-400 hover:bg-white/5 border border-transparent'
          ]"
        >
          <span class="w-3 h-3 rounded bg-slate-600"></span>
          <span class="flex-1 truncate">Sans section</span>
          <span class="text-xs text-slate-500">{{ store.unsectionedProjects.length }}</span>
        </button>
        
        <!-- Sections -->
        <div
          v-for="section in store.sections"
          :key="section.id"
          @click="selectedSectionId = section.id"
          @contextmenu="showContextMenu($event, 'section', section.id)"
          :class="[
            'w-full text-left px-3 py-2.5 rounded-xl mb-1 transition-all flex items-center gap-3 cursor-pointer',
            selectedSectionId === section.id
              ? 'bg-cyber-500/10 text-cyber-400 border border-cyber-500/30'
              : 'text-slate-400 hover:bg-white/5 border border-transparent'
          ]"
        >
          <span 
            class="w-3 h-3 rounded"
            :style="{ backgroundColor: section.color || '#06b6d4' }"
          ></span>
          <span class="flex-1 truncate">{{ section.name }}</span>
          <span class="text-xs text-slate-500">{{ section.projects.length }}</span>
        </div>
        
        <!-- Add Section -->
        <button
          @click="showNewSectionModal = true"
          class="w-full px-3 py-2 text-sm text-slate-500 hover:text-cyber-400 hover:bg-white/5 rounded-xl flex items-center gap-2 transition-all mt-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Nouvelle section
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-bold text-white mb-1">{{ currentSectionName }}</h1>
          <p class="text-slate-400 text-sm">{{ displayedProjects.length }} projet{{ displayedProjects.length !== 1 ? 's' : '' }}</p>
        </div>
        <div class="flex gap-3">
          <router-link
            to="/composer"
            class="group bg-gradient-to-r from-cyber-600 to-accent-600 hover:from-cyber-500 hover:to-accent-500 text-white px-4 py-2 rounded-xl flex items-center gap-2 transition-all shadow-cyber"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span class="font-medium">Composer IA</span>
          </router-link>
          <button
            @click="showImportModal = true; resetImportModal()"
            class="glass cyber-border text-slate-200 hover:text-white px-4 py-2 rounded-xl flex items-center gap-2 transition-all hover:border-primary-400/50"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <span class="font-medium">Importer</span>
          </button>
          <button
            @click="showNewProjectModal = true; createError = null"
            class="glass cyber-border text-slate-200 hover:text-white px-4 py-2 rounded-xl flex items-center gap-2 transition-all hover:border-cyber-400/50"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span class="font-medium">Nouveau</span>
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="store.loading" class="text-center py-16">
        <div class="inline-flex items-center justify-center w-12 h-12 rounded-xl glass cyber-border mb-4">
          <svg class="w-6 h-6 text-cyber-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
        </div>
        <p class="text-slate-400">Chargement...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="displayedProjects.length === 0" class="text-center py-16">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-2xl glass cyber-border mb-6 animate-pulse-cyber">
          <svg class="w-10 h-10 text-cyber-400/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-white mb-2">Aucun projet</h3>
        <p class="text-slate-400 mb-6">Créez votre premier projet dans cette section</p>
        <div class="flex gap-3 justify-center">
          <router-link
            to="/composer"
            class="bg-gradient-to-r from-cyber-600 to-accent-600 hover:from-cyber-500 hover:to-accent-500 text-white px-5 py-2.5 rounded-xl flex items-center gap-2 transition-all shadow-cyber"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Générer avec l'IA
          </router-link>
          <button
            @click="showNewProjectModal = true; createError = null"
            class="glass cyber-border text-slate-200 hover:text-white px-5 py-2.5 rounded-xl transition-all"
          >
            Créer manuellement
          </button>
        </div>
      </div>

      <!-- Project grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="project in displayedProjects"
          :key="project.id"
          class="group glass rounded-2xl p-5 cursor-pointer transition-all duration-300 hover:cyber-glow border border-white/5 hover:border-cyber-500/30"
          @click="router.push(`/project/${project.id}`)"
          @contextmenu="showContextMenu($event, 'project', project.id)"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center group-hover:from-cyber-500/30 group-hover:to-accent-500/30 transition-all">
              <svg class="w-6 h-6 text-cyber-400 group-hover:text-cyber-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <button
              @click.stop="deleteProject(project.id)"
              class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all p-1.5 hover:bg-red-500/10 rounded-lg"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
          
          <h3 class="text-base font-semibold text-white mb-1 group-hover:text-cyber-300 transition-colors truncate">{{ project.name }}</h3>
          <p v-if="project.description" class="text-slate-400 text-sm mb-3 line-clamp-2">
            {{ project.description }}
          </p>
          
          <div class="flex items-center justify-between text-xs">
            <span class="text-cyber-400/80 flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              {{ project.parts_count }} pièce{{ project.parts_count !== 1 ? 's' : '' }}
            </span>
            <span class="text-slate-500">{{ formatDate(project.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu?.show"
        class="fixed glass rounded-xl py-1 min-w-40 shadow-cyber-lg border border-white/10 z-50"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <button
          @click="handleContextAction('duplicate')"
          class="w-full px-4 py-2 text-sm text-slate-300 hover:text-cyber-400 hover:bg-white/5 text-left flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Dupliquer
        </button>
        <button
          v-if="contextMenu.type === 'project'"
          @click="handleContextAction('move')"
          class="w-full px-4 py-2 text-sm text-slate-300 hover:text-cyber-400 hover:bg-white/5 text-left flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          Déplacer vers Sans section
        </button>
        <div class="border-t border-white/5 my-1"></div>
        <button
          @click="handleContextAction('delete')"
          class="w-full px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 text-left flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Supprimer
        </button>
      </div>
    </Teleport>

    <!-- New Project Modal -->
    <Teleport to="body">
      <div v-if="showNewProjectModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
        <div class="glass rounded-2xl w-full max-w-md mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-cyber-900/20 to-primary-900/20">
            <h2 class="text-xl font-semibold text-white">Nouveau Projet</h2>
            <p v-if="selectedSectionId" class="text-xs text-slate-400 mt-1">Dans: {{ currentSectionName }}</p>
          </div>
          
          <form @submit.prevent="createProject" class="p-6">
            <div class="mb-4">
              <label class="block text-sm font-medium text-slate-300 mb-2">Nom du projet</label>
              <input
                v-model="newProjectName"
                type="text"
                placeholder="Ex: Boîtier enceinte"
                class="w-full px-4 py-3 rounded-xl"
                autofocus
              />
            </div>
            
            <div class="mb-6">
              <label class="block text-sm font-medium text-slate-300 mb-2">Description (optionnel)</label>
              <textarea
                v-model="newProjectDescription"
                placeholder="Décrivez votre projet..."
                rows="3"
                class="w-full px-4 py-3 rounded-xl resize-none"
              ></textarea>
            </div>
            
            <div v-if="createError" class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
              {{ createError }}
            </div>
            
            <div class="flex gap-3">
              <button
                type="button"
                @click="showNewProjectModal = false"
                :disabled="creating"
                class="flex-1 px-4 py-3 glass cyber-border text-slate-300 rounded-xl hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                type="submit"
                :disabled="!newProjectName.trim() || creating"
                class="flex-1 px-4 py-3 bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-xl hover:from-cyber-500 hover:to-primary-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <svg v-if="creating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                {{ creating ? 'Création...' : 'Créer' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- New Section Modal -->
    <Teleport to="body">
      <div v-if="showNewSectionModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
        <div class="glass rounded-2xl w-full max-w-md mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-accent-900/20 to-primary-900/20">
            <h2 class="text-xl font-semibold text-white">Nouvelle Section</h2>
          </div>
          
          <form @submit.prevent="createSection" class="p-6">
            <div class="mb-4">
              <label class="block text-sm font-medium text-slate-300 mb-2">Nom de la section</label>
              <input
                v-model="newSectionName"
                type="text"
                placeholder="Ex: Projets perso"
                class="w-full px-4 py-3 rounded-xl"
                autofocus
              />
            </div>
            
            <div class="mb-6">
              <label class="block text-sm font-medium text-slate-300 mb-2">Couleur</label>
              <div class="flex gap-2">
                <button
                  v-for="color in sectionColors"
                  :key="color"
                  type="button"
                  @click="newSectionColor = color"
                  :class="[
                    'w-8 h-8 rounded-lg transition-all',
                    newSectionColor === color ? 'ring-2 ring-white ring-offset-2 ring-offset-dark-900' : ''
                  ]"
                  :style="{ backgroundColor: color }"
                ></button>
              </div>
            </div>
            
            <div class="flex gap-3">
              <button
                type="button"
                @click="showNewSectionModal = false"
                class="flex-1 px-4 py-3 glass cyber-border text-slate-300 rounded-xl hover:bg-white/5 transition-colors"
              >
                Annuler
              </button>
              <button
                type="submit"
                :disabled="!newSectionName.trim()"
                class="flex-1 px-4 py-3 bg-gradient-to-r from-accent-600 to-primary-600 text-white rounded-xl hover:from-accent-500 hover:to-primary-500 transition-all disabled:opacity-50"
              >
                Créer
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Import Modal -->
    <Teleport to="body">
      <div v-if="showImportModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
        <div class="glass rounded-2xl w-full max-w-lg mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-primary-900/20 to-accent-900/20">
            <h2 class="text-xl font-semibold text-white">Importer un fichier 3D</h2>
            <p class="text-xs text-slate-400 mt-1">Formats supportés: STL, OBJ, 3MF</p>
          </div>
          
          <div class="p-6">
            <!-- Drop zone -->
            <div
              @dragover.prevent="importDragOver = true"
              @dragleave="importDragOver = false"
              @drop="handleFileDrop"
              :class="[
                'border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer',
                importDragOver 
                  ? 'border-primary-400 bg-primary-500/10' 
                  : importFile1 
                    ? 'border-cyber-500/50 bg-cyber-500/5'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/5'
              ]"
              @click="($refs.fileInput as HTMLInputElement)?.click()"
            >
              <input
                ref="fileInput"
                type="file"
                accept=".stl,.obj,.3mf"
                @change="handleFileInputChange"
                class="hidden"
              />
              
              <div v-if="importFile1" class="text-center">
                <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-cyber-500/20 flex items-center justify-center">
                  <svg class="w-8 h-8 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p class="text-white font-medium">{{ importFile1.name }}</p>
                <p class="text-sm text-slate-400 mt-1">{{ (importFile1.size / 1024).toFixed(1) }} Ko</p>
                <button 
                  @click.stop="importFile1 = null; importProjectName = ''"
                  class="mt-3 text-sm text-slate-400 hover:text-red-400 transition-colors"
                >
                  Changer de fichier
                </button>
              </div>
              
              <div v-else>
                <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-white/5 flex items-center justify-center">
                  <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <p class="text-white font-medium mb-1">Glissez un fichier ici</p>
                <p class="text-sm text-slate-400">ou cliquez pour parcourir</p>
              </div>
            </div>
            
            <!-- Project name -->
            <div v-if="importFile1" class="mt-6">
              <label class="block text-sm font-medium text-slate-300 mb-2">Nom du projet</label>
              <input
                v-model="importProjectName"
                type="text"
                placeholder="Nom du projet importé"
                class="w-full px-4 py-3 rounded-xl"
              />
            </div>
            
            <!-- Error -->
            <div v-if="importError" class="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
              {{ importError }}
            </div>
          </div>
          
          <div class="px-6 py-4 border-t border-white/5 bg-dark-900/50 flex gap-3">
            <button
              @click="showImportModal = false"
              :disabled="importing"
              class="flex-1 px-4 py-3 glass cyber-border text-slate-300 rounded-xl hover:bg-white/5 transition-colors disabled:opacity-50"
            >
              Annuler
            </button>
            <button
              @click="handleImport"
              :disabled="!importFile1 || !importProjectName.trim() || importing"
              class="flex-1 px-4 py-3 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl hover:from-primary-500 hover:to-accent-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <svg v-if="importing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              {{ importing ? 'Import...' : 'Importer' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
