<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useProjectStore } from '@/stores/project'
import AttachmentManager from './AttachmentManager.vue'
import SketchCanvas from './SketchCanvas.vue'
import type { LLMProvider } from '@/types'

interface Attachment {
  id: string
  type: 'image' | 'sketch'
  dataUrl: string
  name: string
  mimeType: string
}

interface Message {
  id: string
  role: 'user' | 'agent'
  agent?: string
  content: string
  timestamp: Date
  attachments?: Attachment[]
}

interface Requirements {
  dimensions?: string
  material?: string
  features?: string[]
  constraints?: string[]
  use_case?: string
}

const router = useRouter()
const settingsStore = useSettingsStore()
const projectStore = useProjectStore()

// Session state
const sessionId = ref<string | null>(null)
const messages = ref<Message[]>([])
const phase = ref<string>('idle')
const requirements = ref<Requirements>({})
const generatedCode = ref<string | null>(null)
const generatedProjectId = ref<string | null>(null)

// UI state
const userInput = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const activeTab = ref<'chat' | 'sketch' | 'attachments'>('chat')
const showSketchModal = ref(false)

// Attachments
const attachments = ref<Attachment[]>([])
const attachmentManager = ref<InstanceType<typeof AttachmentManager> | null>(null)
const sketchCanvas = ref<InstanceType<typeof SketchCanvas> | null>(null)

// Chat container for auto-scroll
const chatContainer = ref<HTMLElement | null>(null)

// Agent colors and icons
const agentStyles: Record<string, { color: string; icon: string; gradient: string }> = {
  coordinator: { color: 'text-cyber-400', icon: '🎯', gradient: 'from-cyber-500/20 to-cyber-600/10' },
  requirements: { color: 'text-blue-400', icon: '📋', gradient: 'from-blue-500/20 to-blue-600/10' },
  designer: { color: 'text-purple-400', icon: '🎨', gradient: 'from-purple-500/20 to-purple-600/10' },
  engineer: { color: 'text-green-400', icon: '⚙️', gradient: 'from-green-500/20 to-green-600/10' },
  physics: { color: 'text-orange-400', icon: '🔬', gradient: 'from-orange-500/20 to-orange-600/10' },
  manufacturing: { color: 'text-yellow-400', icon: '🏭', gradient: 'from-yellow-500/20 to-yellow-600/10' },
  validator: { color: 'text-red-400', icon: '✅', gradient: 'from-red-500/20 to-red-600/10' },
  review: { color: 'text-pink-400', icon: '👁️', gradient: 'from-pink-500/20 to-pink-600/10' },
}

// Phase labels
const phaseLabels: Record<string, string> = {
  idle: 'Prêt à démarrer',
  gathering: 'Collecte des informations',
  analyzing: 'Analyse du projet',
  designing: 'Conception en cours',
  reviewing: 'Revue du design',
  finalizing: 'Finalisation',
  complete: 'Terminé'
}

function handleAttachmentsChange(newAttachments: Attachment[]) {
  attachments.value = newAttachments
}

function addSketchToAttachments() {
  if (!sketchCanvas.value) return
  
  const dataUrl = sketchCanvas.value.toDataURL()
  if (!dataUrl) return
  
  const newAttachment: Attachment = {
    id: `sketch-${Date.now()}`,
    type: 'sketch',
    dataUrl,
    name: `Croquis ${attachments.value.filter(a => a.type === 'sketch').length + 1}`,
    mimeType: 'image/png'
  }
  
  attachments.value.push(newAttachment)
  showSketchModal.value = false
  sketchCanvas.value.clear()
}

async function startConversation() {
  if (loading.value) return
  if (!userInput.value.trim() && attachments.value.length === 0) return
  
  loading.value = true
  error.value = null
  
  try {
    // Prepare attachments data
    const attachmentData = attachments.value.map(a => ({
      type: a.type,
      data: a.dataUrl.split(',')[1],
      mime_type: a.mimeType,
      name: a.name
    }))
    
    const res = await fetch('/api/conversations/create-with-attachments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        initial_message: userInput.value.trim() || 'Voici mon projet',
        attachments: attachmentData,
        provider: settingsStore.llmProvider
      })
    })
    
    if (!res.ok) {
      throw new Error('Failed to start conversation')
    }
    
    const response = await res.json()
    
    sessionId.value = response.session_id
    messages.value = response.messages.map((m: any) => ({
      ...m,
      id: m.id || `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date(m.timestamp || Date.now())
    }))
    phase.value = response.phase
    requirements.value = response.requirements || {}
    
    // Clear input after starting
    userInput.value = ''
    
    scrollToBottom()
    
  } catch (e: any) {
    console.error('Failed to start conversation:', e)
    error.value = e.message || 'Erreur lors du démarrage de la conversation'
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  if (!sessionId.value || loading.value || !userInput.value.trim()) return
  
  loading.value = true
  error.value = null
  
  // Add user message immediately
  const userMessage: Message = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: userInput.value.trim(),
    timestamp: new Date()
  }
  messages.value.push(userMessage)
  
  const messageText = userInput.value.trim()
  userInput.value = ''
  
  scrollToBottom()
  
  try {
    const res = await fetch(`/api/conversations/${sessionId.value}/message?provider=${settingsStore.llmProvider}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: messageText })
    })
    
    if (!res.ok) {
      throw new Error('Failed to send message')
    }
    
    const response = await res.json()
    
    messages.value = response.messages.map((m: any) => ({
      ...m,
      id: m.id || `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date(m.timestamp || Date.now())
    }))
    phase.value = response.phase
    requirements.value = response.requirements || {}
    generatedCode.value = response.code
    
    if (response.complete && response.project_id) {
      generatedProjectId.value = response.project_id
    }
    
    scrollToBottom()
    
  } catch (e: any) {
    console.error('Failed to send message:', e)
    error.value = e.message || 'Erreur lors de l\'envoi'
  } finally {
    loading.value = false
  }
}

async function generateNow() {
  if (!sessionId.value || loading.value) return
  
  loading.value = true
  error.value = null
  
  try {
    const res = await fetch(`/api/conversations/${sessionId.value}/quick-action?action=generate&provider=${settingsStore.llmProvider}`, {
      method: 'POST'
    })
    
    if (!res.ok) {
      throw new Error('Failed to generate')
    }
    
    const response = await res.json()
    
    messages.value = response.messages.map((m: any) => ({
      ...m,
      id: m.id || `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date(m.timestamp || Date.now())
    }))
    phase.value = response.phase
    generatedCode.value = response.code
    
    if (response.complete && response.project_id) {
      generatedProjectId.value = response.project_id
    }
    
    scrollToBottom()
    
  } catch (e: any) {
    console.error('Failed to generate:', e)
    error.value = e.message || 'Erreur lors de la génération'
  } finally {
    loading.value = false
  }
}

function openProject() {
  if (generatedProjectId.value) {
    router.push(`/project/${generatedProjectId.value}`)
  }
}

function resetComposer() {
  sessionId.value = null
  messages.value = []
  phase.value = 'idle'
  requirements.value = {}
  generatedCode.value = null
  generatedProjectId.value = null
  userInput.value = ''
  attachments.value = []
  error.value = null
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

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

function getAgentStyle(agent: string) {
  return agentStyles[agent] || agentStyles.coordinator
}

// Keyboard shortcut for sketch modal
function handleGlobalKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && showSketchModal.value) {
    showSketchModal.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div class="min-h-screen bg-dark-950">
    <!-- Hero header -->
    <div class="relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-cyber-900/20 via-transparent to-accent-900/20"></div>
      <div class="absolute inset-0 bg-grid opacity-30"></div>
      
      <div class="relative max-w-7xl mx-auto px-6 py-12">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-4 mb-4">
              <div class="w-16 h-16 bg-gradient-to-br from-cyber-500 to-accent-500 rounded-2xl flex items-center justify-center shadow-cyber-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h1 class="text-3xl font-bold text-white">Composer IA</h1>
                <p class="text-slate-400">Créez votre projet 3D avec l'aide de nos agents intelligents</p>
              </div>
            </div>
          </div>
          
          <router-link 
            to="/" 
            class="flex items-center gap-2 px-4 py-2 glass cyber-border rounded-xl text-slate-300 hover:text-white transition-all"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Retour
          </router-link>
        </div>
        
        <!-- Phase indicator -->
        <div v-if="sessionId" class="mt-6 flex items-center gap-3">
          <div class="flex items-center gap-2 px-4 py-2 glass rounded-full">
            <div :class="['w-2 h-2 rounded-full', phase === 'complete' ? 'bg-green-400' : 'bg-cyber-400 animate-pulse']"></div>
            <span class="text-sm text-slate-300">{{ phaseLabels[phase] || phase }}</span>
          </div>
          
          <div v-if="Object.keys(requirements).length > 0" class="flex items-center gap-2 flex-wrap">
            <span v-if="requirements.dimensions" class="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-xs text-blue-400">
              📐 {{ requirements.dimensions }}
            </span>
            <span v-if="requirements.material" class="px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full text-xs text-green-400">
              🧱 {{ requirements.material }}
            </span>
            <span v-if="requirements.use_case" class="px-3 py-1 bg-purple-500/10 border border-purple-500/20 rounded-full text-xs text-purple-400">
              🎯 {{ requirements.use_case }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Main content -->
    <div class="max-w-7xl mx-auto px-6 pb-12">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Left panel: Attachments & Sketch -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Sketch button -->
          <div class="glass rounded-2xl p-6 border border-white/5">
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span class="text-2xl">✏️</span>
              Dessiner un croquis
            </h3>
            <p class="text-sm text-slate-400 mb-4">
              Dessinez votre idée à main levée. Compatible Apple Pencil et stylet.
            </p>
            <button
              @click="showSketchModal = true"
              class="w-full px-4 py-4 bg-gradient-to-r from-cyber-600/20 to-accent-600/20 border-2 border-dashed border-cyber-500/30 rounded-xl text-cyber-400 hover:border-cyber-400 hover:bg-cyber-500/10 transition-all flex items-center justify-center gap-3"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Ouvrir le canvas
            </button>
          </div>
          
          <!-- Attachments -->
          <div class="glass rounded-2xl p-6 border border-white/5">
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span class="text-2xl">📎</span>
              Images de référence
            </h3>
            <AttachmentManager
              ref="attachmentManager"
              :max-attachments="5"
              @change="handleAttachmentsChange"
            />
          </div>
          
          <!-- Current attachments preview -->
          <div v-if="attachments.length > 0" class="glass rounded-2xl p-4 border border-white/5">
            <h4 class="text-sm font-medium text-slate-300 mb-3">{{ attachments.length }} fichier(s) joint(s)</h4>
            <div class="grid grid-cols-3 gap-2">
              <div 
                v-for="att in attachments" 
                :key="att.id"
                class="relative aspect-square rounded-lg overflow-hidden border border-white/10"
              >
                <img :src="att.dataUrl" :alt="att.name" class="w-full h-full object-cover" />
                <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-1">
                  <span class="text-[10px] text-white truncate block">{{ att.type === 'sketch' ? '✏️' : '🖼️' }} {{ att.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Right panel: Chat -->
        <div class="lg:col-span-2">
          <div class="glass rounded-2xl border border-white/5 overflow-hidden flex flex-col" style="height: calc(100vh - 320px); min-height: 500px;">
            
            <!-- Chat messages -->
            <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
              <!-- Welcome message if no session -->
              <div v-if="!sessionId && messages.length === 0" class="text-center py-12">
                <div class="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-cyber-500/20 to-accent-500/20 rounded-full flex items-center justify-center">
                  <svg class="w-10 h-10 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 class="text-xl font-semibold text-white mb-2">Bienvenue dans le Composer IA</h3>
                <p class="text-slate-400 max-w-md mx-auto mb-6">
                  Décrivez votre projet, ajoutez des croquis ou images de référence, et nos agents vous guideront pour créer le modèle 3D parfait.
                </p>
                <div class="flex flex-wrap justify-center gap-3">
                  <div class="px-4 py-2 glass rounded-full text-sm text-slate-300 flex items-center gap-2">
                    <span class="text-cyber-400">🎯</span> Coordinateur
                  </div>
                  <div class="px-4 py-2 glass rounded-full text-sm text-slate-300 flex items-center gap-2">
                    <span class="text-purple-400">🎨</span> Designer
                  </div>
                  <div class="px-4 py-2 glass rounded-full text-sm text-slate-300 flex items-center gap-2">
                    <span class="text-green-400">⚙️</span> Ingénieur
                  </div>
                  <div class="px-4 py-2 glass rounded-full text-sm text-slate-300 flex items-center gap-2">
                    <span class="text-orange-400">🔬</span> Physicien
                  </div>
                </div>
              </div>
              
              <!-- Messages -->
              <template v-for="msg in messages" :key="msg.id">
                <!-- User message -->
                <div v-if="msg.role === 'user'" class="flex justify-end">
                  <div class="max-w-[80%]">
                    <div class="bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-2xl rounded-br-md px-4 py-3">
                      <p class="whitespace-pre-wrap">{{ msg.content }}</p>
                    </div>
                    <div class="text-xs text-slate-500 mt-1 text-right">Vous</div>
                  </div>
                </div>
                
                <!-- Agent message -->
                <div v-else class="flex gap-3">
                  <div 
                    :class="['w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-gradient-to-br', getAgentStyle(msg.agent || 'coordinator').gradient]"
                  >
                    <span class="text-lg">{{ getAgentStyle(msg.agent || 'coordinator').icon }}</span>
                  </div>
                  <div class="flex-1 max-w-[85%]">
                    <div class="glass rounded-2xl rounded-tl-md px-4 py-3 border border-white/5">
                      <p class="whitespace-pre-wrap text-slate-200">{{ msg.content }}</p>
                    </div>
                    <div :class="['text-xs mt-1', getAgentStyle(msg.agent || 'coordinator').color]">
                      {{ msg.agent ? msg.agent.charAt(0).toUpperCase() + msg.agent.slice(1) : 'Agent' }}
                    </div>
                  </div>
                </div>
              </template>
              
              <!-- Loading indicator -->
              <div v-if="loading" class="flex gap-3">
                <div class="w-10 h-10 rounded-full bg-cyber-500/20 flex items-center justify-center">
                  <svg class="w-5 h-5 animate-spin text-cyber-400" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                </div>
                <div class="glass rounded-2xl rounded-tl-md px-4 py-3 border border-white/5">
                  <div class="flex gap-1">
                    <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0ms"></span>
                    <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 150ms"></span>
                    <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 300ms"></span>
                  </div>
                </div>
              </div>
              
              <!-- Error message -->
              <div v-if="error" class="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
                {{ error }}
              </div>
            </div>
            
            <!-- Success banner -->
            <div v-if="generatedProjectId" class="px-6 py-4 bg-gradient-to-r from-green-500/10 to-cyber-500/10 border-t border-green-500/20">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                    <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <div class="font-medium text-green-400">Projet créé avec succès !</div>
                    <div class="text-sm text-slate-400">Votre modèle 3D est prêt</div>
                  </div>
                </div>
                <div class="flex gap-3">
                  <button
                    @click="resetComposer"
                    class="px-4 py-2 glass cyber-border rounded-lg text-slate-300 hover:text-white transition-all"
                  >
                    Nouveau projet
                  </button>
                  <button
                    @click="openProject"
                    class="px-6 py-2 bg-gradient-to-r from-green-600 to-cyber-600 text-white rounded-lg hover:from-green-500 hover:to-cyber-500 transition-all flex items-center gap-2"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Ouvrir le projet
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Input area -->
            <div class="p-4 border-t border-white/5 bg-dark-900/50">
              <!-- Quick action buttons -->
              <div v-if="sessionId && !generatedProjectId && phase !== 'complete'" class="flex gap-2 mb-3">
                <button
                  @click="generateNow"
                  :disabled="loading"
                  class="px-4 py-2 bg-accent-500/10 border border-accent-500/30 rounded-lg text-accent-400 hover:bg-accent-500/20 disabled:opacity-50 text-sm flex items-center gap-2"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Générer maintenant
                </button>
              </div>
              
              <div class="flex gap-3">
                <div class="flex-1">
                  <textarea
                    v-model="userInput"
                    @keydown="handleKeydown"
                    :disabled="loading || !!generatedProjectId"
                    :placeholder="sessionId ? 'Répondez aux questions ou ajoutez des détails...' : 'Décrivez votre projet 3D... (ex: Un support de téléphone avec une base de 80x100mm)'"
                    rows="2"
                    class="w-full px-4 py-3 bg-dark-800 border border-white/10 rounded-xl resize-none text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-cyber-500/50 focus:border-cyber-500/50 disabled:opacity-50"
                  ></textarea>
                </div>
                <button
                  @click="sessionId ? sendMessage() : startConversation()"
                  :disabled="loading || !!generatedProjectId || (!userInput.trim() && !sessionId && attachments.length === 0)"
                  class="px-6 py-3 bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-xl hover:from-cyber-500 hover:to-accent-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-cyber transition-all self-end"
                >
                  <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  {{ sessionId ? 'Envoyer' : 'Démarrer' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Sketch Modal -->
    <Teleport to="body">
      <div 
        v-if="showSketchModal" 
        class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="showSketchModal = false"
      >
        <div class="bg-dark-900 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-white/10">
          <!-- Header -->
          <div class="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-cyber-900/20 to-accent-900/20">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-r from-cyber-500 to-accent-500 rounded-xl flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-semibold text-white">Dessiner un croquis</h2>
                <p class="text-xs text-slate-400">Utilisez votre souris ou stylet pour dessiner</p>
              </div>
            </div>
            <button 
              @click="showSketchModal = false"
              class="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Canvas -->
          <div class="flex-1 p-4 bg-dark-950">
            <SketchCanvas
              ref="sketchCanvas"
              :width="800"
              :height="500"
              class="mx-auto"
            />
          </div>
          
          <!-- Footer -->
          <div class="px-6 py-4 border-t border-white/10 flex justify-end gap-3 bg-dark-900">
            <button
              @click="sketchCanvas?.clear()"
              class="px-4 py-2 glass cyber-border rounded-lg text-slate-300 hover:text-white transition-all"
            >
              Effacer
            </button>
            <button
              @click="showSketchModal = false"
              class="px-4 py-2 glass cyber-border rounded-lg text-slate-300 hover:text-white transition-all"
            >
              Annuler
            </button>
            <button
              @click="addSketchToAttachments"
              class="px-6 py-2 bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-lg hover:from-cyber-500 hover:to-accent-500 transition-all flex items-center gap-2"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Ajouter le croquis
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
