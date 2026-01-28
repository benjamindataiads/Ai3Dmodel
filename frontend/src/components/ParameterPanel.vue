<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useSettingsStore } from '@/stores/settings'
import type { Part, Parameter } from '@/types'

const props = defineProps<{
  part: Part
}>()

const store = useProjectStore()
const settingsStore = useSettingsStore()

const localParams = ref<Record<string, number>>({})
const applying = ref(false)

const parameters = computed((): Parameter[] => {
  return props.part?.parameters || []
})

const hasChanges = computed(() => {
  return parameters.value.some(p => localParams.value[p.name] !== p.value)
})

const hasInvalidParams = computed(() => {
  return Object.values(localParams.value).some(v => v <= 0 || v > 10000)
})

// Initialize local params from part
watch(() => props.part?.parameters, (params) => {
  if (params) {
    localParams.value = {}
    params.forEach(p => {
      localParams.value[p.name] = p.value
    })
  }
}, { immediate: true, deep: true })

function formatParamName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .toLowerCase()
    .replace(/^./, s => s.toUpperCase())
}

function getDisplayValue(valueMm: number): number {
  return settingsStore.convertToDisplay(valueMm)
}

function setDisplayValue(name: string, displayValue: number) {
  localParams.value[name] = settingsStore.convertFromDisplay(displayValue)
}

async function applyChanges() {
  if (!hasChanges.value) return
  
  applying.value = true
  
  try {
    await store.updateParameters(props.part.id, localParams.value)
  } catch (e) {
    console.error('Failed to apply parameters:', e)
  } finally {
    applying.value = false
  }
}

function resetChanges() {
  if (props.part?.parameters) {
    localParams.value = {}
    props.part.parameters.forEach(p => {
      localParams.value[p.name] = p.value
    })
  }
}
</script>

<template>
  <div class="p-4">
    <div class="flex items-center justify-end mb-3">
      <span class="text-xs text-cyber-400 bg-cyber-500/10 border border-cyber-500/30 px-2 py-1 rounded-lg font-mono">
        {{ settingsStore.unit }}
      </span>
    </div>

    <div v-if="parameters.length === 0" class="text-sm text-slate-500 text-center py-4">
      Aucun paramètre détecté
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="param in parameters"
        :key="param.name"
        class="flex items-center justify-between"
      >
        <label class="text-sm text-slate-300">
          {{ formatParamName(param.name) }}
        </label>
        <div class="flex items-center gap-2">
          <input
            type="number"
            :value="getDisplayValue(localParams[param.name] || param.value)"
            @input="setDisplayValue(param.name, parseFloat(($event.target as HTMLInputElement).value) || 0.1)"
            :step="settingsStore.unit === 'mm' ? 1 : 0.1"
            :min="settingsStore.unit === 'mm' ? 0.1 : 0.01"
            :max="10000"
            :class="[
              'w-24 px-3 py-2 text-right text-sm rounded-lg font-mono transition-all',
              'bg-dark-800 border focus:ring-2 focus:ring-cyber-500/50 focus:border-cyber-500/50',
              (localParams[param.name] || 0) <= 0 
                ? 'border-red-500/50 text-red-400' 
                : 'border-white/10 text-slate-200'
            ]"
          />
          <span class="text-xs text-slate-500 w-6">{{ settingsStore.unit }}</span>
        </div>
      </div>

      <!-- Validation error message -->
      <div v-if="hasInvalidParams" class="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400">
        Les paramètres doivent être supérieurs à 0
      </div>

      <div v-if="hasChanges && !hasInvalidParams" class="pt-4 flex gap-2">
        <button
          @click="resetChanges"
          :disabled="applying"
          class="flex-1 px-3 py-2.5 text-sm glass cyber-border text-slate-300 rounded-xl hover:bg-white/5 disabled:opacity-50 transition-all"
        >
          Annuler
        </button>
        <button
          @click="applyChanges"
          :disabled="applying"
          class="flex-1 px-3 py-2.5 text-sm bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-xl hover:from-cyber-500 hover:to-primary-500 disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
        >
          <svg v-if="applying" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Appliquer
        </button>
      </div>
    </div>
  </div>
</template>
