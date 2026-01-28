<script setup lang="ts">
import { ref, onMounted, watch, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { usePrinterStore } from '@/stores/printer'
import ThreeViewer from './ThreeViewer.vue'
import AssemblyViewer from './AssemblyViewer.vue'
import PartEditor from './PartEditor.vue'
import ParameterPanel from './ParameterPanel.vue'
import PrinterSettings from './PrinterSettings.vue'
import ExportPanel from './ExportPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()
const printerStore = usePrinterStore()

const showNewPartModal = ref(false)
const newPartName = ref('')
const selectedPartId = ref<string | null>(null)
const showPrinterSettings = ref(false)

// Page mode: 'edit' for individual parts, 'assembly' for positioning parts
const pageMode = ref<'edit' | 'assembly'>('edit')

// Panel collapse states (edit mode)
const editorCollapsed = ref(false)
const parametersCollapsed = ref(false)
const exportCollapsed = ref(false)

// Resizable panel
const editorHeight = ref(350)
const isResizing = ref(false)
const minHeight = 100
const maxHeight = 600

function startResize(e: MouseEvent) {
  isResizing.value = true
  document.body.classList.add('resizing')
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  e.preventDefault()
}

function onResize(e: MouseEvent) {
  if (!isResizing.value) return
  const container = document.querySelector('.main-content-area') as HTMLElement
  if (!container) return
  const containerRect = container.getBoundingClientRect()
  const newHeight = containerRect.bottom - e.clientY
  editorHeight.value = Math.max(minHeight, Math.min(maxHeight, newHeight))
}

function stopResize() {
  isResizing.value = false
  document.body.classList.remove('resizing')
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

onUnmounted(() => {
  document.body.classList.remove('resizing')
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})

const projectId = computed(() => route.params.id as string)

const hasGeneratedParts = computed(() => 
  (store.currentProject?.parts || []).some((p: { status: string }) => p.status === 'generated')
)

onMounted(async () => {
  await store.fetchProject(projectId.value)
  await printerStore.fetchPresets()
  
  // Auto-select first part if exists
  if (store.currentProject?.parts.length) {
    selectPart(store.currentProject.parts[0].id)
  }
})

watch(projectId, async (newId: string) => {
  await store.fetchProject(newId)
})

async function selectPart(partId: string) {
  selectedPartId.value = partId
  await store.fetchPart(partId)
}

async function createPart() {
  if (!newPartName.value.trim()) {
    return
  }
  
  try {
    const part = await store.createPart(projectId.value, newPartName.value.trim())
    showNewPartModal.value = false
    newPartName.value = ''
    selectPart(part.id)
    pageMode.value = 'edit'
  } catch (e) {
    console.error('Failed to create part:', e)
  }
}

async function deletePart(partId: string) {
  if (confirm('Êtes-vous sûr de vouloir supprimer ce morceau ?')) {
    await store.deletePart(partId)
    if (selectedPartId.value === partId) {
      selectedPartId.value = null
      store.currentPart = null
    }
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'generated':
      return 'bg-cyber-500/20 text-cyber-400 border border-cyber-500/30'
    case 'error':
      return 'bg-red-500/20 text-red-400 border border-red-500/30'
    default:
      return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'generated':
      return 'OK'
    case 'error':
      return 'Erreur'
    default:
      return 'Brouillon'
  }
}

const fitsInPrinter = computed(() => {
  if (!store.currentPart?.bounding_box) {
    return true
  }
  return printerStore.checkFits(store.currentPart.bounding_box)
})

const generatedPartsInProject = computed(() => 
  (store.currentProject?.parts || []).filter((p: { status: string }) => p.status === 'generated')
)

function switchToEditMode(partId: string) {
  selectPart(partId)
  pageMode.value = 'edit'
}

// Handle code generated from 3D editor
async function handleEditorCode(code: string) {
  // If no part is selected, create a new one
  if (!selectedPartId.value) {
    newPartName.value = 'Forme 3D'
    await createPart()
  }
  
  // Execute the code on the current part
  if (selectedPartId.value) {
    try {
      await store.executePartCode(selectedPartId.value, code)
      // Reload the project to update the UI
      await store.fetchProject(route.params.id as string)
    } catch (e) {
      console.error('Failed to execute editor code:', e)
    }
  }
}
</script>

<template>
  <div class="h-[calc(100vh-57px)] flex bg-dark-950">
    <!-- Sidebar -->
    <div class="w-64 glass border-r border-white/5 flex flex-col">
      <!-- Project header -->
      <div class="p-4 border-b border-white/5">
        <button
          @click="router.push('/')"
          class="flex items-center gap-2 text-slate-400 hover:text-cyber-400 text-sm mb-3 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          Retour
        </button>
        <h2 class="text-lg font-semibold text-white truncate">
          {{ store.currentProject?.name || 'Chargement...' }}
        </h2>
      </div>

      <!-- Mode toggle -->
      <div class="p-3 border-b border-white/5">
        <div class="flex rounded-xl bg-dark-800 p-1">
          <button
            @click="pageMode = 'edit'"
            :class="[
              'flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all',
              pageMode === 'edit' 
                ? 'bg-cyber-500/20 text-cyber-400 border border-cyber-500/30' 
                : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            <div class="flex items-center justify-center gap-1.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Édition
            </div>
          </button>
          <button
            @click="pageMode = 'assembly'"
            :disabled="!hasGeneratedParts"
            :class="[
              'flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all',
              pageMode === 'assembly' 
                ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30' 
                : 'text-slate-400 hover:text-slate-200',
              !hasGeneratedParts ? 'opacity-50 cursor-not-allowed' : ''
            ]"
          >
            <div class="flex items-center justify-center gap-1.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Assemblage
            </div>
          </button>
        </div>
      </div>

      <!-- Parts list (edit mode) -->
      <div v-if="pageMode === 'edit'" class="flex-1 overflow-y-auto p-2">
        <div
          v-for="part in store.currentProject?.parts"
          :key="part.id"
          :class="[
            'p-3 rounded-xl cursor-pointer mb-2 group transition-all',
            selectedPartId === part.id
              ? 'bg-cyber-500/10 border border-cyber-500/30 cyber-glow'
              : 'hover:bg-white/5 border border-transparent'
          ]"
          @click="selectPart(part.id)"
        >
          <div class="flex items-center justify-between">
            <span class="font-medium text-slate-200 truncate">{{ part.name }}</span>
            <button
              @click.stop="deletePart(part.id)"
              class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all p-1 hover:bg-red-500/10 rounded"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <span 
            :class="['text-xs px-2 py-0.5 rounded-full mt-2 inline-block cursor-help', getStatusColor(part.status)]"
            :title="part.status === 'draft' ? 'Utilisez le Composer IA ou cliquez Exécuter pour générer' : ''"
          >
            {{ getStatusLabel(part.status) }}
          </span>
        </div>

        <!-- Add part button -->
        <button
          @click="showNewPartModal = true"
          class="w-full p-3 border border-dashed border-white/10 rounded-xl text-slate-500 hover:border-cyber-500/50 hover:text-cyber-400 transition-all flex items-center justify-center gap-2"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Ajouter un morceau
        </button>
      </div>

      <!-- Assembly info (assembly mode) -->
      <div v-else class="flex-1 overflow-y-auto p-3">
        <div class="glass-light rounded-xl p-3 mb-3 border border-accent-500/20">
          <div class="flex items-start gap-2">
            <svg class="w-5 h-5 text-accent-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div class="text-sm text-slate-300">
              <p class="font-medium mb-1 text-accent-400">Mode Assemblage</p>
              <ul class="text-xs space-y-1 text-slate-400">
                <li>• Cliquez sur une pièce pour la sélectionner</li>
                <li>• Déplacez avec les flèches 3D</li>
                <li>• Changez de mode (Translate/Rotate)</li>
                <li>• Double-clic pour éditer une pièce</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="text-xs text-slate-500 uppercase font-medium mb-2">Pièces dans l'assemblage</div>
        <div
          v-for="part in generatedPartsInProject"
          :key="part.id"
          class="p-2 rounded-xl hover:bg-white/5 cursor-pointer flex items-center gap-2 group"
          @dblclick="switchToEditMode(part.id)"
        >
          <span class="w-3 h-3 rounded-full bg-accent-400"></span>
          <span class="text-sm text-slate-300 flex-1 truncate">{{ part.name }}</span>
          <button
            @click="switchToEditMode(part.id)"
            class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-accent-400 text-xs transition-all"
          >
            Éditer
          </button>
        </div>

        <div v-if="!hasGeneratedParts" class="text-center text-slate-500 py-4 text-sm">
          Aucune pièce générée
        </div>
      </div>

      <!-- Printer settings button -->
      <div class="p-4 border-t border-white/5">
        <button
          @click="showPrinterSettings = true"
          class="w-full px-3 py-2.5 text-sm text-slate-400 hover:text-cyber-400 glass-light cyber-border rounded-xl flex items-center gap-2 transition-all"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          {{ printerStore.currentPreset?.name || 'Imprimante' }}
        </button>
      </div>
    </div>

    <!-- EDIT MODE: Main content area -->
    <div v-if="pageMode === 'edit'" class="flex-1 flex flex-col main-content-area overflow-hidden">
      <div v-if="!selectedPartId" class="flex-1 flex items-center justify-center bg-dark-900">
        <div class="text-center">
          <div class="w-20 h-20 glass cyber-border rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse-cyber">
            <svg class="w-10 h-10 text-cyber-400/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-white mb-2">Sélectionnez un morceau</h3>
          <p class="text-slate-500">ou créez-en un nouveau pour commencer</p>
        </div>
      </div>

      <div v-else class="flex-1 flex min-h-0 overflow-hidden">
        <!-- 3D Viewer -->
        <div class="flex-1 relative overflow-hidden p-2">
          <ThreeViewer
            :key="selectedPartId || 'none'"
            :part-id="store.currentPart?.status === 'generated' ? selectedPartId : null"
            :bounding-box="store.currentPart?.bounding_box || null"
            :show-build-volume="printerStore.showBuildVolume"
            :build-volume="printerStore.buildVolume"
            :fits="fitsInPrinter"
            :update-key="store.currentPart?.updated_at"
            @generate-code="handleEditorCode"
          />
          
          <!-- Warning badge if doesn't fit -->
          <div
            v-if="!fitsInPrinter && printerStore.alertOnOverflow"
            class="absolute top-6 left-6 bg-red-500/90 backdrop-blur text-white px-4 py-2 rounded-xl flex items-center gap-2 shadow-lg z-10 border border-red-400/30"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Dépasse le volume d'impression
          </div>
        </div>

        <!-- Right panel -->
        <div class="w-80 glass border-l border-white/5 flex flex-col overflow-y-auto shrink-0">
          <!-- Parameter panel -->
          <div v-if="store.currentPart" class="border-b border-white/5">
            <button
              @click="parametersCollapsed = !parametersCollapsed"
              class="w-full px-4 py-3 flex items-center justify-between bg-dark-800/50 hover:bg-dark-700/50 transition-colors"
            >
              <span class="text-sm font-medium text-slate-300">Paramètres</span>
              <svg 
                :class="['w-4 h-4 text-slate-500 transition-transform', parametersCollapsed ? '' : 'rotate-180']" 
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <ParameterPanel
              v-show="!parametersCollapsed"
              :part="store.currentPart"
            />
          </div>
          
          <!-- Export panel -->
          <div v-if="store.currentPart" class="border-b border-white/5">
            <button
              @click="exportCollapsed = !exportCollapsed"
              class="w-full px-4 py-3 flex items-center justify-between bg-dark-800/50 hover:bg-dark-700/50 transition-colors"
            >
              <span class="text-sm font-medium text-slate-300">Export</span>
              <svg 
                :class="['w-4 h-4 text-slate-500 transition-transform', exportCollapsed ? '' : 'rotate-180']" 
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <ExportPanel
              v-show="!exportCollapsed"
              :part="store.currentPart"
              :project="store.currentProject"
            />
          </div>
        </div>
      </div>

      <!-- Resize handle -->
      <div 
        v-if="selectedPartId && !editorCollapsed"
        @mousedown="startResize"
        class="h-2 bg-dark-700 hover:bg-cyber-600/50 cursor-ns-resize flex items-center justify-center group transition-colors shrink-0 z-20"
      >
        <div class="w-12 h-1 bg-slate-600 group-hover:bg-cyber-400 rounded-full transition-colors"></div>
      </div>

      <!-- Code editor panel (bottom) -->
      <div v-if="selectedPartId" class="border-t border-white/5 flex flex-col bg-dark-850 shrink-0 z-10">
        <!-- Collapse header -->
        <button
          @click="editorCollapsed = !editorCollapsed"
          class="px-4 py-2 flex items-center justify-between bg-dark-800/50 hover:bg-dark-700/50 transition-colors shrink-0"
        >
          <span class="text-sm font-medium text-slate-300">Éditeur de code</span>
          <svg 
            :class="['w-4 h-4 text-slate-500 transition-transform', editorCollapsed ? 'rotate-180' : '']" 
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
          </svg>
        </button>
        
        <!-- Editor content -->
        <div 
          v-show="!editorCollapsed" 
          :style="{ height: editorHeight + 'px' }"
          class="overflow-hidden"
        >
          <PartEditor
            :part="store.currentPart"
            @update="store.fetchPart(selectedPartId!)"
          />
        </div>
      </div>
    </div>

    <!-- ASSEMBLY MODE: Full screen 3D view -->
    <div v-else class="flex-1 relative overflow-hidden">
      <AssemblyViewer
        :parts="store.currentProject?.parts || []"
        :show-build-volume="printerStore.showBuildVolume"
        :build-volume="printerStore.buildVolume"
        @edit-part="switchToEditMode"
      />
    </div>

    <!-- New Part Modal -->
    <Teleport to="body">
      <div v-if="showNewPartModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
        <div class="glass rounded-2xl w-full max-w-md mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-cyber-900/20 to-primary-900/20">
            <h2 class="text-xl font-semibold text-white">Nouveau Morceau</h2>
          </div>
          
          <form @submit.prevent="createPart" class="p-6">
            <div class="mb-6">
              <label class="block text-sm font-medium text-slate-300 mb-2">Nom du morceau</label>
              <input
                v-model="newPartName"
                type="text"
                placeholder="Ex: Face avant"
                class="w-full px-4 py-3 rounded-xl"
                autofocus
              />
            </div>
            
            <div class="flex gap-3">
              <button
                type="button"
                @click="showNewPartModal = false"
                class="flex-1 px-4 py-3 glass cyber-border text-slate-300 rounded-xl hover:bg-white/5 transition-colors"
              >
                Annuler
              </button>
              <button
                type="submit"
                :disabled="!newPartName.trim()"
                class="flex-1 px-4 py-3 bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-xl hover:from-cyber-500 hover:to-primary-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Créer
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Printer Settings Modal -->
    <PrinterSettings
      v-if="showPrinterSettings"
      @close="showPrinterSettings = false"
    />
  </div>
</template>
