<script setup lang="ts">
import { getExportStlUrl, getExport3mfUrl, getProjectExport3mfUrl } from '@/services/api'
import type { Part, Project } from '@/types'

const props = defineProps<{
  part: Part
  project: Project | null
}>()

function downloadStl() {
  if (!props.part) return
  window.open(getExportStlUrl(props.part.id), '_blank')
}

function download3mf() {
  if (!props.part) return
  window.open(getExport3mfUrl(props.part.id), '_blank')
}

function downloadProject3mf() {
  if (!props.project) return
  window.open(getProjectExport3mfUrl(props.project.id), '_blank')
}
</script>

<template>
  <div class="p-4">
    <div v-if="part.status !== 'generated'" class="text-sm text-slate-500 text-center py-4">
      Générez d'abord la pièce pour l'exporter
    </div>

    <div v-else class="space-y-3">
      <!-- Part exports -->
      <div class="text-xs text-slate-400 mb-3">Morceau: <span class="text-slate-200">{{ part.name }}</span></div>
      
      <button
        @click="downloadStl"
        class="w-full px-4 py-3 text-sm glass cyber-border text-slate-300 rounded-xl hover:text-cyber-400 hover:border-cyber-500/50 flex items-center gap-3 transition-all"
      >
        <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Télécharger STL
      </button>
      
      <button
        @click="download3mf"
        class="w-full px-4 py-3 text-sm bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-xl hover:from-cyber-500 hover:to-primary-500 flex items-center gap-3 shadow-cyber transition-all"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Télécharger 3MF
        <span class="text-xs opacity-75 ml-auto">(Bambu Studio)</span>
      </button>

      <!-- Project export -->
      <div v-if="project && project.parts.filter(p => p.status === 'generated').length > 1" class="pt-4 border-t border-white/5 mt-4">
        <div class="text-xs text-slate-400 mb-3">Projet complet</div>
        <button
          @click="downloadProject3mf"
          class="w-full px-4 py-3 text-sm glass rounded-xl text-accent-400 border border-accent-500/30 hover:bg-accent-500/10 hover:border-accent-500/50 flex items-center gap-3 transition-all"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          Exporter tout le projet (3MF)
        </button>
      </div>
    </div>
  </div>
</template>
