import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'
import type { LLMProvider } from '@/types'

const STORAGE_KEY = 'cad3d_settings'

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

interface Settings {
  llmProvider: LLMProvider
  openaiModel: string | null
  anthropicModel: string | null
  unit: 'mm' | 'cm'
}

function loadSettings(): Settings {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      // Ignore
    }
  }
  return {
    llmProvider: 'openai',
    openaiModel: null,
    anthropicModel: null,
    unit: 'mm',
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const initialSettings = loadSettings()
  
  const llmProvider = ref<LLMProvider>(initialSettings.llmProvider)
  const openaiModel = ref<string | null>(initialSettings.openaiModel)
  const anthropicModel = ref<string | null>(initialSettings.anthropicModel)
  const unit = ref<'mm' | 'cm'>(initialSettings.unit)
  
  // Available models loaded from API
  const availableModels = ref<AvailableModels | null>(null)

  // Current model based on provider
  const currentModel = computed(() => {
    if (llmProvider.value === 'openai') {
      return openaiModel.value || availableModels.value?.openai.default || null
    }
    return anthropicModel.value || availableModels.value?.anthropic.default || null
  })

  function saveSettings() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      llmProvider: llmProvider.value,
      openaiModel: openaiModel.value,
      anthropicModel: anthropicModel.value,
      unit: unit.value,
    }))
  }

  watch([llmProvider, openaiModel, anthropicModel, unit], saveSettings)

  function setLLMProvider(provider: LLMProvider) {
    llmProvider.value = provider
  }

  function setOpenAIModel(model: string) {
    openaiModel.value = model
  }

  function setAnthropicModel(model: string) {
    anthropicModel.value = model
  }

  function setAvailableModels(models: AvailableModels) {
    availableModels.value = models
    // Set defaults if not already set
    if (!openaiModel.value && models.openai.default) {
      openaiModel.value = models.openai.default
    }
    if (!anthropicModel.value && models.anthropic.default) {
      anthropicModel.value = models.anthropic.default
    }
  }

  function setUnit(newUnit: 'mm' | 'cm') {
    unit.value = newUnit
  }

  function convertToDisplay(valueMm: number): number {
    if (unit.value === 'cm') {
      return valueMm / 10
    }
    return valueMm
  }

  function convertFromDisplay(value: number): number {
    if (unit.value === 'cm') {
      return value * 10
    }
    return value
  }

  return {
    llmProvider,
    openaiModel,
    anthropicModel,
    currentModel,
    availableModels,
    unit,
    setLLMProvider,
    setOpenAIModel,
    setAnthropicModel,
    setAvailableModels,
    setUnit,
    convertToDisplay,
    convertFromDisplay,
  }
})
