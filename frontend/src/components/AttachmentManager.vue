<script setup lang="ts">
import { ref, computed } from 'vue'
import SketchCanvas from './SketchCanvas.vue'

export interface Attachment {
  id: string
  type: 'image' | 'sketch'
  dataUrl: string
  name: string
  timestamp: number
}

const props = defineProps<{
  maxAttachments?: number
}>()

const emit = defineEmits<{
  change: [attachments: Attachment[]]
}>()

// State
const attachments = ref<Attachment[]>([])
const showSketchModal = ref(false)
const editingSketch = ref<Attachment | null>(null)
const sketchCanvas = ref<InstanceType<typeof SketchCanvas> | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// Max attachments (default 5)
const maxAttachments = computed(() => props.maxAttachments || 5)
const canAddMore = computed(() => attachments.value.length < maxAttachments.value)

// Generate unique ID
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// Add image from file
function triggerFileUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  
  if (!files) return
  
  Array.from(files).forEach((file, index) => {
    if (attachments.value.length >= maxAttachments.value) return
    
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      alert(`Format non supporté: ${file.name}`)
      return
    }
    
    if (file.size > 10 * 1024 * 1024) {
      alert(`Image trop volumineuse: ${file.name} (max 10 Mo)`)
      return
    }
    
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      addAttachment({
        id: generateId(),
        type: 'image',
        dataUrl,
        name: file.name,
        timestamp: Date.now(),
      })
    }
    reader.readAsDataURL(file)
  })
  
  // Reset input
  if (input) input.value = ''
}

// Add attachment
function addAttachment(attachment: Attachment) {
  if (attachments.value.length >= maxAttachments.value) return
  
  attachments.value.push(attachment)
  emit('change', attachments.value)
}

// Remove attachment
function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
  emit('change', attachments.value)
}

// Open sketch modal
function openSketchModal(existing?: Attachment) {
  if (existing) {
    editingSketch.value = existing
  } else {
    editingSketch.value = null
  }
  showSketchModal.value = true
}

// Save sketch
function saveSketch() {
  if (!sketchCanvas.value) return
  
  const dataUrl = sketchCanvas.value.save()
  
  if (editingSketch.value) {
    // Update existing sketch
    const index = attachments.value.findIndex(a => a.id === editingSketch.value!.id)
    if (index !== -1) {
      attachments.value[index] = {
        ...attachments.value[index],
        dataUrl,
        timestamp: Date.now(),
      }
    }
  } else {
    // Add new sketch
    const sketchNumber = attachments.value.filter(a => a.type === 'sketch').length + 1
    addAttachment({
      id: generateId(),
      type: 'sketch',
      dataUrl,
      name: `Sketch ${sketchNumber}`,
      timestamp: Date.now(),
    })
  }
  
  closeSketchModal()
  emit('change', attachments.value)
}

// Close sketch modal
function closeSketchModal() {
  showSketchModal.value = false
  editingSketch.value = null
}

// Clear all attachments
function clearAll() {
  attachments.value = []
  emit('change', attachments.value)
}

// Get attachment data for API
function getAttachmentsData(): { dataUrl: string; mimeType: string }[] {
  return attachments.value.map(a => ({
    dataUrl: a.dataUrl.split(',')[1], // Remove data URL prefix
    mimeType: a.dataUrl.match(/data:([^;]+);/)?.[1] || 'image/png',
  }))
}

// Expose methods
defineExpose({
  getAttachmentsData,
  clearAll,
  addAttachment,
})

// Drag and drop
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'copy'
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  
  const files = e.dataTransfer?.files
  if (!files) return
  
  // Create a fake event for handleFileSelect
  const fakeInput = { files } as HTMLInputElement
  handleFileSelect({ target: fakeInput } as unknown as Event)
}
</script>

<template>
  <div class="attachment-manager">
    <!-- Hidden file input -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="handleFileSelect"
    />
    
    <!-- Attachments grid -->
    <div v-if="attachments.length > 0" class="mb-4">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm text-slate-400">
          Pièces jointes ({{ attachments.length }}/{{ maxAttachments }})
        </span>
        <button
          @click="clearAll"
          class="text-xs text-red-400 hover:text-red-300"
        >
          Tout supprimer
        </button>
      </div>
      
      <div class="flex flex-wrap gap-2">
        <div
          v-for="attachment in attachments"
          :key="attachment.id"
          class="relative group"
        >
          <img
            :src="attachment.dataUrl"
            :alt="attachment.name"
            class="w-20 h-20 object-cover rounded-lg border border-white/10 cursor-pointer hover:border-white/30 transition-all"
            @click="attachment.type === 'sketch' ? openSketchModal(attachment) : undefined"
          />
          
          <!-- Type badge -->
          <div 
            class="absolute bottom-1 left-1 px-1.5 py-0.5 text-[10px] rounded bg-dark-900/80"
            :class="attachment.type === 'sketch' ? 'text-cyber-400' : 'text-primary-400'"
          >
            {{ attachment.type === 'sketch' ? '✏️' : '📷' }}
          </div>
          
          <!-- Remove button -->
          <button
            @click.stop="removeAttachment(attachment.id)"
            class="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-400"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          
          <!-- Edit badge for sketches -->
          <div
            v-if="attachment.type === 'sketch'"
            class="absolute top-1 right-1 p-1 bg-dark-900/80 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            @click.stop="openSketchModal(attachment)"
          >
            <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Add buttons -->
    <div 
      v-if="canAddMore"
      class="flex gap-2"
      @dragover="handleDragOver"
      @drop="handleDrop"
    >
      <button
        @click="openSketchModal()"
        class="flex-1 p-3 border-2 border-dashed border-white/10 rounded-xl hover:border-cyber-500/50 hover:bg-cyber-500/5 transition-all flex items-center justify-center gap-2 text-slate-400 hover:text-cyber-400"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
        </svg>
        <span class="text-sm">Dessiner</span>
      </button>
      
      <button
        @click="triggerFileUpload"
        class="flex-1 p-3 border-2 border-dashed border-white/10 rounded-xl hover:border-primary-500/50 hover:bg-primary-500/5 transition-all flex items-center justify-center gap-2 text-slate-400 hover:text-primary-400"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span class="text-sm">Image</span>
      </button>
    </div>
    
    <p v-else class="text-xs text-slate-500 text-center">
      Maximum {{ maxAttachments }} pièces jointes atteint
    </p>
    
    <!-- Sketch Modal -->
    <Teleport to="body">
      <div
        v-if="showSketchModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
        @click.self="closeSketchModal"
      >
        <div class="w-full max-w-5xl h-[80vh] bg-dark-900 rounded-2xl shadow-2xl border border-white/10 flex flex-col overflow-hidden">
          <!-- Modal header -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <h3 class="text-lg font-semibold text-white flex items-center gap-2">
              <span class="text-2xl">✏️</span>
              {{ editingSketch ? 'Modifier le dessin' : 'Nouveau dessin' }}
            </h3>
            <div class="flex items-center gap-2">
              <button
                @click="closeSketchModal"
                class="px-4 py-2 text-slate-400 hover:text-white rounded-lg hover:bg-white/5"
              >
                Annuler
              </button>
              <button
                @click="saveSketch"
                class="px-4 py-2 bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-lg hover:from-cyber-500 hover:to-accent-500 flex items-center gap-2"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                Enregistrer
              </button>
            </div>
          </div>
          
          <!-- Canvas -->
          <SketchCanvas
            ref="sketchCanvas"
            class="flex-1"
            :width="1200"
            :height="800"
            :initial-image="editingSketch?.dataUrl"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>
