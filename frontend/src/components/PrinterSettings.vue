<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePrinterStore } from '@/stores/printer'

const emit = defineEmits<{
  close: []
}>()

const printerStore = usePrinterStore()

const localCustomVolume = ref({ ...printerStore.customVolume })

const isCustom = computed(() => printerStore.presetId === 'custom')

watch(() => printerStore.customVolume, (vol) => {
  localCustomVolume.value = { ...vol }
}, { deep: true })

function selectPreset(id: string) {
  printerStore.setPreset(id)
}

function updateCustomVolume() {
  printerStore.setCustomVolume({ ...localCustomVolume.value })
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in" @click="emit('close')">
      <div class="glass rounded-2xl w-full max-w-lg mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
        <div class="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-cyber-900/20 to-primary-900/20">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500 to-primary-500 flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-semibold text-white">Imprimante 3D</h2>
                <p class="text-xs text-slate-400">Configuration du build volume</p>
              </div>
            </div>
            <button @click="emit('close')" class="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="p-6 space-y-6">
          <!-- Preset selection -->
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-3">Profil imprimante</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="preset in printerStore.presets"
                :key="preset.id"
                :class="[
                  'px-4 py-3 text-sm rounded-xl border transition-all text-left',
                  printerStore.presetId === preset.id
                    ? 'bg-cyber-500/10 border-cyber-500/30 text-cyber-400'
                    : 'bg-dark-700/50 border-white/5 text-slate-400 hover:border-white/10 hover:bg-dark-600/50'
                ]"
                @click="selectPreset(preset.id)"
              >
                <div class="font-medium text-slate-200">{{ preset.name }}</div>
                <div class="text-xs opacity-75 font-mono mt-0.5">
                  {{ preset.build_volume.x }} × {{ preset.build_volume.y }} × {{ preset.build_volume.z }} mm
                </div>
              </button>
            </div>
          </div>

          <!-- Custom volume (when custom selected) -->
          <div v-if="isCustom" class="p-4 glass-light rounded-xl border border-white/5">
            <label class="block text-sm font-medium text-slate-300 mb-3">Volume de build personnalisé</label>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="block text-xs text-slate-500 mb-1">X (mm)</label>
                <input
                  v-model.number="localCustomVolume.x"
                  type="number"
                  min="1"
                  @change="updateCustomVolume"
                  class="w-full px-3 py-2.5 rounded-lg"
                />
              </div>
              <div>
                <label class="block text-xs text-slate-500 mb-1">Y (mm)</label>
                <input
                  v-model.number="localCustomVolume.y"
                  type="number"
                  min="1"
                  @change="updateCustomVolume"
                  class="w-full px-3 py-2.5 rounded-lg"
                />
              </div>
              <div>
                <label class="block text-xs text-slate-500 mb-1">Z (mm)</label>
                <input
                  v-model.number="localCustomVolume.z"
                  type="number"
                  min="1"
                  @change="updateCustomVolume"
                  class="w-full px-3 py-2.5 rounded-lg"
                />
              </div>
            </div>
          </div>

          <!-- Options -->
          <div class="space-y-3">
            <label class="flex items-center gap-3 cursor-pointer p-3 rounded-xl hover:bg-white/5 transition-colors">
              <input
                type="checkbox"
                :checked="printerStore.showBuildVolume"
                @change="printerStore.setShowBuildVolume(($event.target as HTMLInputElement).checked)"
                class="w-4 h-4 text-cyber-500 bg-dark-700 border-white/20 rounded focus:ring-cyber-500/50"
              />
              <span class="text-sm text-slate-300">Afficher le volume de build dans la vue 3D</span>
            </label>
            
            <label class="flex items-center gap-3 cursor-pointer p-3 rounded-xl hover:bg-white/5 transition-colors">
              <input
                type="checkbox"
                :checked="printerStore.alertOnOverflow"
                @change="printerStore.setAlertOnOverflow(($event.target as HTMLInputElement).checked)"
                class="w-4 h-4 text-cyber-500 bg-dark-700 border-white/20 rounded focus:ring-cyber-500/50"
              />
              <span class="text-sm text-slate-300">Alerter si la pièce dépasse le volume</span>
            </label>
          </div>

          <!-- Current volume summary -->
          <div class="p-4 bg-cyber-500/10 rounded-xl border border-cyber-500/20">
            <div class="text-sm font-medium text-cyber-400 mb-1">Volume actif</div>
            <div class="text-lg font-mono text-white">
              {{ printerStore.buildVolume.x }} × {{ printerStore.buildVolume.y }} × {{ printerStore.buildVolume.z }} mm
            </div>
          </div>
        </div>

        <!-- Close button -->
        <div class="px-6 py-4 border-t border-white/5 bg-dark-900/50">
          <button
            @click="emit('close')"
            class="w-full px-4 py-3 bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-xl hover:from-cyber-500 hover:to-primary-500 transition-all shadow-cyber"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
