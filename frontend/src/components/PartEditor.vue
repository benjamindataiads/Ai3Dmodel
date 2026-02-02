<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as monaco from 'monaco-editor'
import { useProjectStore } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import { autosavePart, getPartVersions, getVersion, restoreVersion, generatePartWithImage, analyzeImageForDesign } from '@/services/api'
import type { Part, VersionSummary } from '@/types'
import ShapeBuilder from './ShapeBuilder.vue'
import DesignChat from './DesignChat.vue'

const props = defineProps<{
  part: Part | null
}>()

const emit = defineEmits<{
  update: []
}>()

const store = useProjectStore()
const settingsStore = useSettingsStore()

const editorContainer = ref<HTMLDivElement | null>(null)
const activeTab = ref<'code' | 'ai' | 'chat' | 'shapes'>('code')
const aiPrompt = ref('')
const generating = ref(false)
const aiMode = ref<'new' | 'edit'>('new')
const includeContext = ref(false)

// Image upload state
const imageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)
const analyzingImage = ref(false)
const imageAnalysis = ref<any>(null)
const useAgents = ref(true)  // Use multi-agent system by default

// Autosave state
const autosaveEnabled = ref(true)
const autosaveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
let autosaveTimeout: ReturnType<typeof setTimeout> | null = null
const AUTOSAVE_DELAY = 2000 // 2 seconds after typing stops

// Version state
const showVersions = ref(false)
const versions = ref<VersionSummary[]>([])
const loadingVersions = ref(false)
const restoringVersion = ref(false)

let editor: monaco.editor.IStandaloneCodeEditor | null = null
let localCode = ref('')

// Get other parts from the current project that have code
const otherPartsWithCode = computed(() => {
  if (!store.currentProject || !props.part) return []
  return store.currentProject.parts.filter(
    p => p.id !== props.part!.id && p.code && p.code.trim()
  )
})

// Auto-select edit mode if part already has code
watch(() => props.part?.code, (code) => {
  if (code && code.trim()) {
    aiMode.value = 'edit'
  } else {
    aiMode.value = 'new'
  }
}, { immediate: true })

// Initialize editor
onMounted(() => {
  if (!editorContainer.value) return

  editor = monaco.editor.create(editorContainer.value, {
    value: props.part?.code || '',
    language: 'python',
    theme: 'vs-dark',
    minimap: { enabled: false },
    fontSize: 13,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 4,
    wordWrap: 'on',
    padding: { top: 12, bottom: 12 },
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    cursorBlinking: 'smooth',
    smoothScrolling: true,
    renderLineHighlight: 'gutter',
  })

  editor.onDidChangeModelContent(() => {
    localCode.value = editor?.getValue() || ''
    // Trigger autosave
    if (autosaveEnabled.value && props.part) {
      triggerAutosave()
    }
  })
})

onUnmounted(() => {
  editor?.dispose()
  if (autosaveTimeout) {
    clearTimeout(autosaveTimeout)
  }
})

// Update editor when part changes
watch(() => props.part?.code, (newCode) => {
  if (editor && newCode !== editor.getValue()) {
    editor.setValue(newCode || '')
  }
}, { immediate: true })

// Watch for part changes to refresh versions
watch(() => props.part?.id, () => {
  if (showVersions.value) {
    loadVersions()
  }
})

// Autosave function
function triggerAutosave() {
  if (autosaveTimeout) {
    clearTimeout(autosaveTimeout)
  }
  
  autosaveStatus.value = 'idle'
  
  autosaveTimeout = setTimeout(async () => {
    if (!props.part || !editor) return
    
    const code = editor.getValue()
    if (code === props.part.code) return // No changes
    
    autosaveStatus.value = 'saving'
    
    try {
      await autosavePart(props.part.id, code)
      autosaveStatus.value = 'saved'
      
      // Reset to idle after 2 seconds
      setTimeout(() => {
        if (autosaveStatus.value === 'saved') {
          autosaveStatus.value = 'idle'
        }
      }, 2000)
    } catch (e) {
      console.error('Autosave failed:', e)
      autosaveStatus.value = 'error'
    }
  }, AUTOSAVE_DELAY)
}

// Load versions
async function loadVersions() {
  if (!props.part) return
  
  loadingVersions.value = true
  try {
    versions.value = await getPartVersions(props.part.id)
  } catch (e) {
    console.error('Failed to load versions:', e)
  } finally {
    loadingVersions.value = false
  }
}

// Toggle versions panel
function toggleVersions() {
  showVersions.value = !showVersions.value
  if (showVersions.value) {
    loadVersions()
  }
}

// Restore a version
async function handleRestoreVersion(versionId: string) {
  if (!props.part || restoringVersion.value) return
  
  restoringVersion.value = true
  try {
    const version = await getVersion(versionId)
    
    // Update the editor with the restored code
    if (editor && version.code) {
      editor.setValue(version.code)
    }
    
    // Restore through API
    await restoreVersion(versionId)
    
    // Refresh the part data
    emit('update')
    
    // Reload versions
    await loadVersions()
  } catch (e) {
    console.error('Failed to restore version:', e)
  } finally {
    restoringVersion.value = false
  }
}

// Save and execute code
async function saveCode() {
  if (!props.part || !editor) return
  
  const code = editor.getValue()
  
  try {
    await store.executePartCode(props.part.id, code)
    emit('update')
  } catch (e) {
    console.error('Failed to execute code:', e)
  }
}

// Handle code from Shape Builder
function handleShapeCode(code: string) {
  if (editor) {
    editor.setValue(code)
  }
  activeTab.value = 'code'
}

// Handle code from Design Chat
function handleChatCode(code: string) {
  if (editor) {
    editor.setValue(code)
  }
  activeTab.value = 'code'
  emit('update')
}

// Image upload handlers
function triggerImageUpload() {
  imageInput.value?.click()
}

function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  
  if (file) {
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      alert('Format non supporté. Utilisez JPG, PNG, GIF ou WebP.')
      return
    }
    
    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('Image trop volumineuse (max 10 Mo)')
      return
    }
    
    imageFile.value = file
    
    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      imagePreview.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
    
    // Auto-analyze image
    analyzeImage()
  }
}

function removeImage() {
  imageFile.value = null
  imagePreview.value = null
  imageAnalysis.value = null
  if (imageInput.value) {
    imageInput.value.value = ''
  }
}

async function analyzeImage() {
  if (!imageFile.value) return
  
  analyzingImage.value = true
  imageAnalysis.value = null
  
  try {
    const result = await analyzeImageForDesign(
      imageFile.value,
      aiPrompt.value || undefined,
      settingsStore.llmProvider,
      settingsStore.currentModel
    )
    
    if (result.success && 'shape_description' in result.analysis) {
      imageAnalysis.value = result.analysis
      
      // Auto-fill prompt if empty
      if (!aiPrompt.value.trim()) {
        aiPrompt.value = result.analysis.shape_description
      }
    }
  } catch (e) {
    console.error('Failed to analyze image:', e)
  } finally {
    analyzingImage.value = false
  }
}

// Generate code via AI
async function generateCode() {
  if (!props.part || !aiPrompt.value.trim()) return
  
  generating.value = true
  
  try {
    // If image is provided, use image-based generation
    if (imageFile.value) {
      await generatePartWithImage(
        props.part.id,
        aiPrompt.value.trim(),
        imageFile.value,
        settingsStore.llmProvider,
        settingsStore.currentModel,
        true // use optimization
      )
      
      // Clear image after successful generation
      removeImage()
    } else {
      // Standard text-based generation
      const currentCode = aiMode.value === 'edit' ? props.part.code : undefined
      const contextParts = includeContext.value 
        ? otherPartsWithCode.value.map(p => ({ name: p.name, code: p.code! }))
        : undefined
      
      if (useAgents.value) {
        // Use agent-based generation for better quality
        await store.generateCodeWithAgents(
          props.part.id, 
          aiPrompt.value.trim(), 
          settingsStore.llmProvider,
          settingsStore.currentModel,
          currentCode,
          contextParts
        )
      } else {
        // Standard generation
        await store.generateCode(
          props.part.id, 
          aiPrompt.value.trim(), 
          settingsStore.llmProvider,
          settingsStore.currentModel,
          currentCode,
          contextParts
        )
      }
    }
    
    aiPrompt.value = ''
    activeTab.value = 'code'
    emit('update')
  } catch (e) {
    console.error('Failed to generate code:', e)
  } finally {
    generating.value = false
  }
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault()
    saveCode()
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'z' && showVersions.value && versions.value.length > 0) {
    e.preventDefault()
    // Restore the most recent version (index 0 is most recent)
    if (versions.value.length > 1) {
      handleRestoreVersion(versions.value[1].id) // Restore to one before current
    }
  }
}

// Format version source for display
function formatSource(source: string): string {
  const labels: Record<string, string> = {
    manual: 'Exécution',
    autosave: 'Auto-save',
    ai_generate: 'IA',
    parameter_update: 'Paramètres',
    restore: 'Restauration',
    before_restore: 'Avant restauration',
    initial: 'Initial',
  }
  return labels[source] || source
}

// Format date for display
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return 'À l\'instant'
  if (diff < 3600000) return `Il y a ${Math.floor(diff / 60000)} min`
  if (diff < 86400000) return `Il y a ${Math.floor(diff / 3600000)}h`
  
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

</script>

<template>
  <div class="h-full flex flex-col bg-dark-900" @keydown="handleKeydown">
    <!-- Tabs -->
    <div class="flex items-center justify-between border-b border-white/5 px-4 bg-dark-850">
      <div class="flex">
        <button
          :class="[
            'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-all',
            activeTab === 'code'
              ? 'border-cyber-500 text-cyber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          ]"
          @click="activeTab = 'code'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            Code
          </span>
        </button>
        <button
          :class="[
            'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-all',
            activeTab === 'ai'
              ? 'border-accent-500 text-accent-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          ]"
          @click="activeTab = 'ai'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            IA
          </span>
        </button>
        <button
          :class="[
            'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-all',
            activeTab === 'chat'
              ? 'border-green-500 text-green-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          ]"
          @click="activeTab = 'chat'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Chat IA
            <span class="px-1.5 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">Pro</span>
          </span>
        </button>
        <button
          :class="[
            'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-all',
            activeTab === 'shapes'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          ]"
          @click="activeTab = 'shapes'"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            Formes
          </span>
        </button>
      </div>

      <div class="flex items-center gap-2">
        <!-- Autosave status -->
        <div v-if="autosaveEnabled" class="flex items-center gap-1.5 text-xs">
          <span v-if="autosaveStatus === 'saving'" class="text-amber-400 flex items-center gap-1">
            <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Sauvegarde...
          </span>
          <span v-else-if="autosaveStatus === 'saved'" class="text-cyber-400 flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Sauvegardé
          </span>
          <span v-else-if="autosaveStatus === 'error'" class="text-red-400">
            Erreur
          </span>
        </div>

        <!-- Version button -->
        <button
          v-if="activeTab === 'code'"
          @click="toggleVersions"
          :class="[
            'px-3 py-1.5 text-sm rounded-lg flex items-center gap-1.5 transition-all',
            showVersions
              ? 'bg-primary-500/10 text-primary-400 border border-primary-500/30'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          ]"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Versions
        </button>

        <!-- Save button (code tab) -->
        <button
          v-if="activeTab === 'code'"
          @click="saveCode"
          :disabled="store.loading"
          class="px-4 py-1.5 text-sm bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-lg hover:from-cyber-500 hover:to-primary-500 disabled:opacity-50 flex items-center gap-2 shadow-cyber transition-all"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Exécuter
        </button>
      </div>
    </div>

    <!-- Code editor with version panel -->
    <div v-if="activeTab === 'code'" class="flex-1 flex relative">
      <!-- Editor -->
      <div class="flex-1 relative">
        <div ref="editorContainer" class="absolute inset-0"></div>
        
        <!-- Error display -->
        <div
          v-if="part?.status === 'error' && part?.error_message"
          class="absolute bottom-0 left-0 right-0 bg-red-500/10 border-t border-red-500/30 p-3 backdrop-blur-sm"
        >
          <div class="flex items-start gap-2">
            <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <pre class="text-sm text-red-400 whitespace-pre-wrap font-mono">{{ part.error_message }}</pre>
          </div>
        </div>
      </div>

      <!-- Versions panel -->
      <div
        v-if="showVersions"
        class="w-64 border-l border-white/5 bg-dark-850 overflow-hidden flex flex-col"
      >
        <div class="p-3 border-b border-white/5">
          <h3 class="text-sm font-medium text-white flex items-center gap-2">
            <svg class="w-4 h-4 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Historique
          </h3>
          <p class="text-xs text-slate-500 mt-1">Cmd+Z pour annuler</p>
        </div>

        <div v-if="loadingVersions" class="p-4 text-center text-slate-400 text-sm">
          <svg class="w-5 h-5 animate-spin mx-auto mb-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Chargement...
        </div>

        <div v-else-if="versions.length === 0" class="p-4 text-center text-slate-500 text-sm">
          Aucune version enregistrée
        </div>

        <div v-else class="flex-1 overflow-y-auto">
          <button
            v-for="(version, index) in versions"
            :key="version.id"
            @click="handleRestoreVersion(version.id)"
            :disabled="restoringVersion || index === 0"
            :class="[
              'w-full p-3 text-left hover:bg-white/5 border-b border-white/5 transition-all',
              index === 0 ? 'bg-cyber-500/5' : '',
              restoringVersion ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            ]"
          >
            <div class="flex items-center justify-between mb-1">
              <span :class="[
                'text-xs font-medium px-2 py-0.5 rounded',
                version.source === 'manual' ? 'bg-cyber-500/20 text-cyber-400' :
                version.source === 'autosave' ? 'bg-amber-500/20 text-amber-400' :
                version.source === 'ai_generate' ? 'bg-accent-500/20 text-accent-400' :
                version.source === 'initial' ? 'bg-primary-500/20 text-primary-400' :
                'bg-slate-500/20 text-slate-400'
              ]">
                {{ formatSource(version.source) }}
              </span>
              <span v-if="index === 0" class="text-xs text-cyber-400">Actuel</span>
            </div>
            <div class="text-xs text-slate-500">
              {{ formatDate(version.created_at) }}
            </div>
            <div v-if="!version.has_code" class="text-xs text-slate-600 mt-1 italic">
              (code vide)
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- AI Composer -->
    <div v-if="activeTab === 'ai'" class="flex-1 p-4 flex flex-col overflow-y-auto bg-dark-850">
      <!-- Hidden file input -->
      <input
        ref="imageInput"
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        class="hidden"
        @change="handleImageSelect"
      />

      <!-- Mode toggle -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-300 mb-2">Mode</label>
        <div class="flex gap-2">
          <button
            :class="[
              'flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-all border',
              aiMode === 'new'
                ? 'bg-cyber-500/10 text-cyber-400 border-cyber-500/30'
                : 'bg-dark-700 text-slate-400 border-white/5 hover:border-white/10'
            ]"
            @click="aiMode = 'new'"
          >
            <div class="flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Nouveau
            </div>
          </button>
          <button
            :class="[
              'flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-all border',
              aiMode === 'edit'
                ? 'bg-accent-500/10 text-accent-400 border-accent-500/30'
                : 'bg-dark-700 text-slate-400 border-white/5 hover:border-white/10',
              !part?.code ? 'opacity-50 cursor-not-allowed' : ''
            ]"
            :disabled="!part?.code"
            @click="aiMode = 'edit'"
          >
            <div class="flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Modifier
            </div>
          </button>
        </div>
      </div>

      <!-- Image upload section -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-300 mb-2">Image de référence (optionnel)</label>
        
        <div v-if="!imagePreview" class="relative">
          <button
            @click="triggerImageUpload"
            :disabled="generating"
            class="w-full p-4 border-2 border-dashed border-white/10 rounded-xl hover:border-primary-500/50 transition-all flex flex-col items-center gap-2 text-slate-400 hover:text-slate-200"
          >
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span class="text-sm">Cliquez ou glissez une image</span>
            <span class="text-xs text-slate-500">JPG, PNG, GIF, WebP (max 10 Mo)</span>
          </button>
        </div>
        
        <div v-else class="relative">
          <div class="relative rounded-xl overflow-hidden border border-white/10">
            <img :src="imagePreview" alt="Reference image" class="w-full h-48 object-contain bg-dark-900" />
            <button
              @click="removeImage"
              class="absolute top-2 right-2 p-1.5 bg-dark-900/80 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-all"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <!-- Analysis status -->
            <div v-if="analyzingImage" class="absolute bottom-2 left-2 px-2 py-1 bg-dark-900/80 rounded-lg text-xs text-amber-400 flex items-center gap-1.5">
              <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              Analyse en cours...
            </div>
            <div v-else-if="imageAnalysis" class="absolute bottom-2 left-2 px-2 py-1 bg-dark-900/80 rounded-lg text-xs text-cyber-400 flex items-center gap-1.5">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Image analysée
            </div>
          </div>
          
          <!-- Analysis results -->
          <div v-if="imageAnalysis" class="mt-2 p-3 bg-dark-800/50 rounded-lg border border-white/5">
            <div class="text-xs text-slate-400 space-y-1">
              <p><span class="text-slate-500">Forme:</span> {{ imageAnalysis.shape_description }}</p>
              <p v-if="imageAnalysis.estimated_dimensions">
                <span class="text-slate-500">Dimensions:</span> 
                ~{{ imageAnalysis.estimated_dimensions.length }}×{{ imageAnalysis.estimated_dimensions.width }}×{{ imageAnalysis.estimated_dimensions.height }} mm
              </p>
              <p><span class="text-slate-500">Complexité:</span> 
                <span :class="{
                  'text-cyber-400': imageAnalysis.complexity === 'simple',
                  'text-amber-400': imageAnalysis.complexity === 'medium',
                  'text-red-400': imageAnalysis.complexity === 'complex'
                }">{{ imageAnalysis.complexity }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Agent mode toggle -->
      <div class="mb-4">
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            v-model="useAgents"
            class="w-4 h-4 text-primary-500 bg-dark-700 border-white/20 rounded focus:ring-primary-500/50"
          />
          <span class="text-sm text-slate-300">
            Mode agents (qualité optimisée)
          </span>
        </label>
        <p class="text-xs text-slate-500 mt-1 ml-7">
          Plusieurs IA collaborent pour un meilleur résultat
        </p>
      </div>

      <!-- Context toggle -->
      <div v-if="otherPartsWithCode.length > 0" class="mb-4">
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            v-model="includeContext"
            class="w-4 h-4 text-cyber-500 bg-dark-700 border-white/20 rounded focus:ring-cyber-500/50"
          />
          <span class="text-sm text-slate-300">
            Contexte des autres pièces
          </span>
        </label>
      </div>

      <div class="flex-1 flex flex-col min-h-0">
        <textarea
          v-model="aiPrompt"
          :disabled="generating"
          :placeholder="imageFile 
            ? 'Décrivez ou affinez la pièce à créer à partir de l\'image...'
            : aiMode === 'new' 
              ? 'Décrivez la pièce à créer...'
              : 'Décrivez les modifications...'"
          class="flex-1 w-full p-4 bg-dark-800 border border-white/10 rounded-xl resize-none text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-cyber-500/50 focus:border-cyber-500/50 disabled:opacity-50 transition-all"
        ></textarea>
      </div>

      <div class="mt-4 flex justify-end gap-3">
        <button
          v-if="imageFile && !imageAnalysis && !analyzingImage"
          @click="analyzeImage"
          class="px-4 py-2.5 text-slate-400 hover:text-white border border-white/10 rounded-xl hover:border-white/20 transition-all flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Analyser
        </button>
        <button
          @click="generateCode"
          :disabled="generating || !aiPrompt.trim()"
          class="px-5 py-2.5 bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-xl hover:from-cyber-500 hover:to-accent-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-cyber transition-all"
        >
          <svg v-if="generating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          {{ generating ? 'Génération...' : imageFile ? 'Générer depuis image' : 'Générer' }}
        </button>
      </div>
    </div>

    <!-- Design Chat (Conversational AI) -->
    <DesignChat
      v-if="activeTab === 'chat'"
      class="flex-1"
      :part-id="part?.id"
      @code-generated="handleChatCode"
      @close="activeTab = 'code'"
    />

    <!-- Shape Builder -->
    <ShapeBuilder
      v-if="activeTab === 'shapes'"
      class="flex-1"
      @generate-code="handleShapeCode"
      @close="activeTab = 'code'"
    />
  </div>
</template>
