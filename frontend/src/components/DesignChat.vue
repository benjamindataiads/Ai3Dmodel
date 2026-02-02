<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import * as api from '@/services/api'
import AttachmentManager from './AttachmentManager.vue'
import type { Attachment } from './AttachmentManager.vue'

const props = defineProps<{
  partId?: string
}>()

const emit = defineEmits<{
  codeGenerated: [code: string]
  close: []
}>()

const settingsStore = useSettingsStore()

// Conversation state
const sessionId = ref<string | null>(null)
const messages = ref<any[]>([])
const requirements = ref<any>({})
const phase = ref<string>('gathering')
const generatedCode = ref<string | null>(null)
const isComplete = ref(false)

// UI state
const userInput = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLDivElement | null>(null)
const showAttachments = ref(true)

// Attachments (sketches + images)
const attachmentManager = ref<InstanceType<typeof AttachmentManager> | null>(null)
const currentAttachments = ref<Attachment[]>([])

// Legacy image upload (for quick single image)
const imageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)

// Agent role colors and icons
const agentStyles: Record<string, { color: string; icon: string; name: string }> = {
  coordinator: { color: 'bg-primary-500/20 text-primary-400', icon: '🎯', name: 'Coordinateur' },
  requirements: { color: 'bg-cyber-500/20 text-cyber-400', icon: '📋', name: 'Analyste' },
  designer: { color: 'bg-accent-500/20 text-accent-400', icon: '🎨', name: 'Designer' },
  engineer: { color: 'bg-amber-500/20 text-amber-400', icon: '⚙️', name: 'Ingénieur' },
  physics: { color: 'bg-blue-500/20 text-blue-400', icon: '🔬', name: 'Mécanicien' },
  manufacturing: { color: 'bg-green-500/20 text-green-400', icon: '🏭', name: 'Fabrication' },
  validator: { color: 'bg-red-500/20 text-red-400', icon: '✓', name: 'Validateur' },
}

// Handle attachment changes
function handleAttachmentsChange(attachments: Attachment[]) {
  currentAttachments.value = attachments
}

// Start conversation
async function startConversation() {
  loading.value = true
  
  try {
    let response: any
    
    // Check if we have attachments (new multi-image system)
    if (currentAttachments.value.length > 0) {
      // Use new attachments endpoint
      const attachmentsData = currentAttachments.value.map(att => ({
        data: att.dataUrl.split(',')[1], // Remove data URL prefix
        mime_type: att.dataUrl.match(/data:([^;]+);/)?.[1] || 'image/png',
        name: att.name,
        is_sketch: att.type === 'sketch',
      }))
      
      const res = await fetch('/api/conversations/create-with-attachments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_id: props.partId,
          initial_prompt: userInput.value || undefined,
          attachments: attachmentsData,
          provider: settingsStore.llmProvider,
          model: settingsStore.currentModel,
        }),
      })
      response = await res.json()
      
      // Clear attachments after starting
      if (attachmentManager.value) {
        attachmentManager.value.clearAll()
      }
      currentAttachments.value = []
      
    } else if (imageFile.value) {
      // Legacy: Start with single image
      const formData = new FormData()
      formData.append('image', imageFile.value)
      if (props.partId) formData.append('part_id', props.partId)
      if (userInput.value) formData.append('initial_prompt', userInput.value)
      formData.append('provider', settingsStore.llmProvider)
      if (settingsStore.currentModel) formData.append('model', settingsStore.currentModel)
      
      const res = await fetch('/api/conversations/create-with-image', {
        method: 'POST',
        body: formData,
      })
      response = await res.json()
      removeImage()
      
    } else {
      // Start without images
      const res = await fetch('/api/conversations/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_id: props.partId,
          initial_prompt: userInput.value || undefined,
          provider: settingsStore.llmProvider,
          model: settingsStore.currentModel,
        }),
      })
      response = await res.json()
    }
    
    sessionId.value = response.session_id
    messages.value = response.messages
    requirements.value = response.requirements
    phase.value = response.phase
    generatedCode.value = response.code
    isComplete.value = response.complete
    
    userInput.value = ''
    showAttachments.value = false // Hide attachments panel after starting
    scrollToBottom()
    
  } catch (e) {
    console.error('Failed to start conversation:', e)
  } finally {
    loading.value = false
  }
}

// Send message
async function sendMessage() {
  if (!sessionId.value || !userInput.value.trim() || loading.value) return
  
  const message = userInput.value.trim()
  userInput.value = ''
  loading.value = true
  
  // Optimistically add user message
  messages.value.push({
    id: Date.now().toString(),
    type: 'user',
    content: message,
    timestamp: new Date().toISOString(),
  })
  scrollToBottom()
  
  try {
    const res = await fetch(`/api/conversations/${sessionId.value}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        provider: settingsStore.llmProvider,
        model: settingsStore.currentModel,
      }),
    })
    const response = await res.json()
    
    // Update with server response
    messages.value = response.messages
    requirements.value = response.requirements
    phase.value = response.phase
    generatedCode.value = response.code
    isComplete.value = response.complete
    
    scrollToBottom()
    
  } catch (e) {
    console.error('Failed to send message:', e)
  } finally {
    loading.value = false
  }
}

// Quick action (for buttons)
async function quickAction(action: string) {
  if (!sessionId.value || loading.value) return
  
  loading.value = true
  
  try {
    const res = await fetch(`/api/conversations/${sessionId.value}/quick-action?action=${action}&provider=${settingsStore.llmProvider}`, {
      method: 'POST',
    })
    const response = await res.json()
    
    messages.value = response.messages
    requirements.value = response.requirements
    phase.value = response.phase
    generatedCode.value = response.code
    isComplete.value = response.complete
    
    scrollToBottom()
    
  } catch (e) {
    console.error('Failed to execute action:', e)
  } finally {
    loading.value = false
  }
}

// Apply generated code to part
async function applyCode() {
  if (!sessionId.value || !generatedCode.value || !props.partId) return
  
  loading.value = true
  
  try {
    const res = await fetch(`/api/conversations/${sessionId.value}/apply-to-part?part_id=${props.partId}`, {
      method: 'POST',
    })
    const response = await res.json()
    
    if (response.status === 'applied') {
      emit('codeGenerated', generatedCode.value)
    }
    
  } catch (e) {
    console.error('Failed to apply code:', e)
  } finally {
    loading.value = false
  }
}

// Image handling
function triggerImageUpload() {
  imageInput.value?.click()
}

function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  
  if (file) {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      alert('Format non supporté. Utilisez JPG, PNG, GIF ou WebP.')
      return
    }
    
    imageFile.value = file
    
    const reader = new FileReader()
    reader.onload = (e) => {
      imagePreview.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

function removeImage() {
  imageFile.value = null
  imagePreview.value = null
  if (imageInput.value) {
    imageInput.value.value = ''
  }
}

// Scroll chat to bottom
function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// Get last question options
const lastQuestionOptions = computed(() => {
  const lastMessage = [...messages.value].reverse().find(m => m.type === 'question')
  return lastMessage?.data?.options || []
})

// Handle Enter key
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (sessionId.value) {
      sendMessage()
    } else {
      startConversation()
    }
  }
}

// Get placeholder text based on state
function getPlaceholder(): string {
  if (sessionId.value) {
    return 'Votre message...'
  }
  if (currentAttachments.value.length > 0) {
    return 'Décrivez ce que vous voyez dans vos dessins/images...'
  }
  return 'Décrivez ce que vous voulez créer, ou ajoutez des dessins...'
}

// Format message content with markdown-like formatting
function formatContent(content: string): string {
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

// Phase indicator
const phaseLabels: Record<string, string> = {
  gathering: 'Collecte des informations',
  analyzing: 'Analyse en cours',
  designing: 'Conception',
  reviewing: 'Révision',
  finalizing: 'Finalisation',
  complete: 'Terminé',
}
</script>

<template>
  <div class="h-full flex flex-col bg-dark-900">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-white/5">
      <div>
        <h2 class="text-lg font-semibold text-white flex items-center gap-2">
          <span class="text-2xl">🤖</span>
          Assistant de Conception
        </h2>
        <p class="text-sm text-slate-400">
          Discutez avec nos agents pour créer votre pièce
        </p>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- Phase indicator -->
        <div v-if="sessionId" class="px-3 py-1.5 rounded-full text-xs font-medium"
          :class="{
            'bg-cyber-500/20 text-cyber-400': phase === 'gathering',
            'bg-amber-500/20 text-amber-400': phase === 'analyzing',
            'bg-accent-500/20 text-accent-400': phase === 'designing',
            'bg-primary-500/20 text-primary-400': phase === 'reviewing',
            'bg-green-500/20 text-green-400': phase === 'finalizing' || phase === 'complete',
          }">
          {{ phaseLabels[phase] || phase }}
        </div>
        
        <button @click="emit('close')" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-white/5">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Chat messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Welcome message if no session -->
      <div v-if="!sessionId && messages.length === 0" class="text-center py-12">
        <div class="text-6xl mb-4">👋</div>
        <h3 class="text-xl font-semibold text-white mb-2">Bienvenue !</h3>
        <p class="text-slate-400 max-w-md mx-auto">
          Décrivez ce que vous souhaitez créer, ou uploadez une image de référence.
          Nos agents spécialisés vous guideront dans la conception.
        </p>
        
        <!-- Agent team preview -->
        <div class="mt-8 flex flex-wrap justify-center gap-3">
          <div v-for="(style, role) in agentStyles" :key="role"
            class="px-3 py-2 rounded-lg text-sm" :class="style.color">
            <span class="mr-1">{{ style.icon }}</span>
            {{ style.name }}
          </div>
        </div>
      </div>
      
      <!-- Messages -->
      <template v-for="msg in messages" :key="msg.id">
        <!-- User message -->
        <div v-if="msg.type === 'user'" class="flex justify-end">
          <div class="max-w-[80%] px-4 py-3 rounded-2xl rounded-br-sm bg-cyber-500/20 text-cyber-100">
            {{ msg.content }}
          </div>
        </div>
        
        <!-- Agent message -->
        <div v-else class="flex gap-3">
          <div v-if="msg.agent_role" 
            class="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
            :class="agentStyles[msg.agent_role]?.color || 'bg-slate-500/20 text-slate-400'">
            {{ agentStyles[msg.agent_role]?.icon || '🤖' }}
          </div>
          <div class="flex-1">
            <div v-if="msg.agent_role" class="text-xs text-slate-500 mb-1">
              {{ agentStyles[msg.agent_role]?.name || msg.agent_role }}
            </div>
            <div class="max-w-[90%] px-4 py-3 rounded-2xl rounded-tl-sm bg-dark-800 border border-white/5">
              <!-- Code block -->
              <div v-if="msg.type === 'code'" class="space-y-2">
                <p class="text-slate-300" v-html="formatContent(msg.content)"></p>
                <pre class="bg-dark-900 p-3 rounded-lg text-sm text-slate-300 overflow-x-auto max-h-64"><code>{{ msg.data?.code }}</code></pre>
                <div v-if="msg.data?.bounding_box" class="text-xs text-slate-500">
                  Dimensions: {{ msg.data.bounding_box.x?.toFixed(1) }} × {{ msg.data.bounding_box.y?.toFixed(1) }} × {{ msg.data.bounding_box.z?.toFixed(1) }} mm
                </div>
              </div>
              
              <!-- Regular message -->
              <p v-else class="text-slate-300" v-html="formatContent(msg.content)"></p>
              
              <!-- Question options -->
              <div v-if="msg.type === 'question' && msg.data?.options?.length" class="mt-3 flex flex-wrap gap-2">
                <button
                  v-for="option in msg.data.options"
                  :key="option"
                  @click="userInput = option; sendMessage()"
                  :disabled="loading"
                  class="px-3 py-1.5 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-all disabled:opacity-50">
                  {{ option }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
      
      <!-- Loading indicator -->
      <div v-if="loading" class="flex gap-3">
        <div class="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 animate-spin text-primary-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
        </div>
        <div class="px-4 py-3 rounded-2xl bg-dark-800 border border-white/5">
          <div class="flex gap-1">
            <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 300ms"></span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Code actions (when complete) -->
    <div v-if="generatedCode && isComplete" class="p-4 border-t border-white/5 bg-green-500/5">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 text-green-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <span class="text-sm font-medium">Design prêt !</span>
        </div>
        <button
          @click="applyCode"
          :disabled="loading || !partId"
          class="px-4 py-2 bg-gradient-to-r from-green-600 to-cyber-600 text-white rounded-lg hover:from-green-500 hover:to-cyber-500 disabled:opacity-50 flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          Appliquer à la pièce
        </button>
      </div>
    </div>
    
    <!-- Input area -->
    <div class="p-4 border-t border-white/5">
      <!-- Attachments panel (before conversation starts) -->
      <div v-if="!sessionId && showAttachments" class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-slate-300 flex items-center gap-2">
            <span class="text-lg">📎</span>
            Dessins & Images de référence
          </span>
          <button
            @click="showAttachments = false"
            class="text-xs text-slate-500 hover:text-slate-300"
          >
            Masquer
          </button>
        </div>
        <AttachmentManager
          ref="attachmentManager"
          :max-attachments="5"
          @change="handleAttachmentsChange"
        />
      </div>
      
      <!-- Show attachments button (when hidden) -->
      <button
        v-if="!sessionId && !showAttachments"
        @click="showAttachments = true"
        class="mb-3 text-sm text-slate-400 hover:text-slate-200 flex items-center gap-2"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
        Ajouter dessins/images ({{ currentAttachments.length }})
      </button>
      
      <!-- Legacy image preview (for quick single upload) -->
      <div v-if="imagePreview && !showAttachments" class="mb-3 relative inline-block">
        <img :src="imagePreview" alt="Reference" class="h-20 rounded-lg border border-white/10" />
        <button @click="removeImage" 
          class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white hover:bg-red-400">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <!-- Hidden file input -->
      <input ref="imageInput" type="file" accept="image/*" class="hidden" @change="handleImageSelect" />
      
      <div class="flex gap-3">
        <!-- Sketch/Image toggle (when conversation active) -->
        <button
          v-if="sessionId"
          @click="showAttachments = !showAttachments"
          :class="[
            'p-3 rounded-xl border transition-all',
            showAttachments 
              ? 'bg-cyber-500/10 border-cyber-500/30 text-cyber-400'
              : 'bg-dark-800 border-white/10 text-slate-400 hover:text-white hover:border-white/20'
          ]"
          :disabled="loading"
          title="Ajouter des dessins/images"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        </button>
        
        <!-- Text input -->
        <div class="flex-1 relative">
          <textarea
            v-model="userInput"
            @keydown="handleKeydown"
            :disabled="loading"
            :placeholder="getPlaceholder()"
            rows="1"
            class="w-full px-4 py-3 bg-dark-800 border border-white/10 rounded-xl resize-none text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-cyber-500/50 focus:border-cyber-500/50 disabled:opacity-50"></textarea>
        </div>
        
        <!-- Send button -->
        <button
          @click="sessionId ? sendMessage() : startConversation()"
          :disabled="loading || (!userInput.trim() && currentAttachments.length === 0)"
          class="px-5 py-3 bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-xl hover:from-cyber-500 hover:to-accent-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-cyber transition-all">
          <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
