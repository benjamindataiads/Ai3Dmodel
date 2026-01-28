<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterView } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { getAvailableModels } from '@/services/api'

const settingsStore = useSettingsStore()
const showSettings = ref(false)

// Load available models on app start
onMounted(async () => {
  try {
    const models = await getAvailableModels()
    settingsStore.setAvailableModels(models)
  } catch (e) {
    console.error('Failed to load available models:', e)
  }
})

// Get models for current provider
const currentProviderModels = computed(() => {
  if (!settingsStore.availableModels) return []
  if (settingsStore.llmProvider === 'openai') {
    return settingsStore.availableModels.openai.models
  }
  return settingsStore.availableModels.anthropic.models
})

const currentSelectedModel = computed(() => {
  if (settingsStore.llmProvider === 'openai') {
    return settingsStore.openaiModel
  }
  return settingsStore.anthropicModel
})

function selectModel(modelId: string) {
  if (settingsStore.llmProvider === 'openai') {
    settingsStore.setOpenAIModel(modelId)
  } else {
    settingsStore.setAnthropicModel(modelId)
  }
}
</script>

<template>
  <div class="min-h-screen bg-dark-950 bg-grid">
    <!-- Header -->
    <header class="glass border-b border-white/5 px-6 py-3 sticky top-0 z-40">
      <div class="flex items-center justify-between max-w-[1920px] mx-auto">
        <router-link to="/" class="flex items-center gap-3 group">
          <img src="/logo.png" alt="VoxelMind AI" class="h-10 w-auto" />
          <div class="hidden sm:block">
            <span class="text-lg font-semibold text-gradient">VoxelMind</span>
            <span class="text-lg font-light text-slate-400 ml-1">AI</span>
          </div>
        </router-link>
        
        <nav class="flex items-center gap-2">
          <router-link 
            to="/docs" 
            class="hidden sm:flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-cyber-400 text-sm rounded-lg hover:bg-white/5 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Docs
          </router-link>
          <button
            @click="showSettings = true"
            class="p-2.5 text-slate-400 hover:text-cyber-400 rounded-lg hover:bg-white/5 cyber-border transition-all group"
            title="Paramètres"
          >
            <svg class="w-5 h-5 group-hover:rotate-45 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </nav>
      </div>
    </header>
    
    <!-- Main content -->
    <main>
      <RouterView />
    </main>

    <!-- Settings Modal -->
    <Teleport to="body">
      <div 
        v-if="showSettings" 
        class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in" 
        @click="showSettings = false"
      >
        <div class="glass rounded-2xl w-full max-w-md mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <!-- Modal Header -->
          <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-cyber-900/20 to-accent-900/20">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500 to-accent-500 flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div>
                  <h2 class="text-lg font-semibold text-white">Paramètres</h2>
                  <p class="text-xs text-slate-400">Configuration IA</p>
                </div>
              </div>
              <button @click="showSettings = false" class="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <div class="p-6 space-y-6">
            <!-- LLM Provider -->
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-3">Provider IA</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  :class="[
                    'relative px-4 py-4 rounded-xl text-sm font-medium transition-all border overflow-hidden group',
                    settingsStore.llmProvider === 'openai'
                      ? 'bg-cyber-500/10 text-cyber-400 border-cyber-500/50 cyber-glow'
                      : 'bg-dark-700/50 text-slate-400 border-white/5 hover:border-white/20 hover:bg-dark-600/50'
                  ]"
                  @click="settingsStore.setLLMProvider('openai')"
                >
                  <div class="relative z-10">
                    <div class="font-semibold text-base">OpenAI</div>
                    <div class="text-xs opacity-60 mt-1">GPT-5 Series</div>
                  </div>
                  <div v-if="settingsStore.llmProvider === 'openai'" class="absolute top-2 right-2">
                    <div class="w-2 h-2 rounded-full bg-cyber-400 animate-pulse"></div>
                  </div>
                </button>
                <button
                  :class="[
                    'relative px-4 py-4 rounded-xl text-sm font-medium transition-all border overflow-hidden group',
                    settingsStore.llmProvider === 'anthropic'
                      ? 'bg-accent-500/10 text-accent-400 border-accent-500/50 accent-glow'
                      : 'bg-dark-700/50 text-slate-400 border-white/5 hover:border-white/20 hover:bg-dark-600/50'
                  ]"
                  @click="settingsStore.setLLMProvider('anthropic')"
                >
                  <div class="relative z-10">
                    <div class="font-semibold text-base">Claude</div>
                    <div class="text-xs opacity-60 mt-1">Anthropic</div>
                  </div>
                  <div v-if="settingsStore.llmProvider === 'anthropic'" class="absolute top-2 right-2">
                    <div class="w-2 h-2 rounded-full bg-accent-400 animate-pulse"></div>
                  </div>
                </button>
              </div>
            </div>

            <!-- Model Selection -->
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-3">Modèle</label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="model in currentProviderModels"
                  :key="model.id"
                  :class="[
                    'px-3 py-2.5 rounded-lg text-sm transition-all border text-left',
                    currentSelectedModel === model.id
                      ? settingsStore.llmProvider === 'openai' 
                        ? 'bg-cyber-500/10 text-cyber-400 border-cyber-500/30 font-medium'
                        : 'bg-accent-500/10 text-accent-400 border-accent-500/30 font-medium'
                      : 'bg-dark-700/30 text-slate-400 border-white/5 hover:border-white/10 hover:bg-dark-600/30'
                  ]"
                  @click="selectModel(model.id)"
                >
                  {{ model.name }}
                </button>
              </div>
              <p v-if="!currentProviderModels.length" class="text-xs text-slate-500 mt-2 flex items-center gap-2">
                <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Chargement des modèles...
              </p>
            </div>

            <!-- Unit -->
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-3">Unité de mesure</label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  :class="[
                    'px-4 py-3 rounded-xl text-sm font-medium transition-all border',
                    settingsStore.unit === 'mm'
                      ? 'bg-primary-500/10 text-primary-400 border-primary-500/30'
                      : 'bg-dark-700/30 text-slate-400 border-white/5 hover:border-white/10'
                  ]"
                  @click="settingsStore.setUnit('mm')"
                >
                  Millimètres (mm)
                </button>
                <button
                  :class="[
                    'px-4 py-3 rounded-xl text-sm font-medium transition-all border',
                    settingsStore.unit === 'cm'
                      ? 'bg-primary-500/10 text-primary-400 border-primary-500/30'
                      : 'bg-dark-700/30 text-slate-400 border-white/5 hover:border-white/10'
                  ]"
                  @click="settingsStore.setUnit('cm')"
                >
                  Centimètres (cm)
                </button>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t border-white/5 bg-dark-900/50">
            <p class="text-xs text-slate-500 text-center flex items-center justify-center gap-2">
              <svg class="w-4 h-4 text-cyber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Sauvegarde automatique
            </p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
