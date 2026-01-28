import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'
import type { PrinterPreset, BoundingBox } from '@/types'
import * as api from '@/services/api'

const STORAGE_KEY = 'cad3d_printer'

interface PrinterSettings {
  presetId: string
  customVolume: BoundingBox
  showBuildVolume: boolean
  alertOnOverflow: boolean
}

function loadPrinterSettings(): PrinterSettings {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      // Ignore
    }
  }
  return {
    presetId: 'bambulab-p1s',
    customVolume: { x: 200, y: 200, z: 200 },
    showBuildVolume: true,
    alertOnOverflow: true,
  }
}

export const usePrinterStore = defineStore('printer', () => {
  const initialSettings = loadPrinterSettings()
  
  const presets = ref<PrinterPreset[]>([])
  const presetId = ref(initialSettings.presetId)
  const customVolume = ref<BoundingBox>(initialSettings.customVolume)
  const showBuildVolume = ref(initialSettings.showBuildVolume)
  const alertOnOverflow = ref(initialSettings.alertOnOverflow)
  const loading = ref(false)

  const currentPreset = computed(() => {
    return presets.value.find(p => p.id === presetId.value) || null
  })

  const buildVolume = computed<BoundingBox>(() => {
    if (presetId.value === 'custom') {
      return customVolume.value
    }
    return currentPreset.value?.build_volume || { x: 200, y: 200, z: 200 }
  })

  function saveSettings() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      presetId: presetId.value,
      customVolume: customVolume.value,
      showBuildVolume: showBuildVolume.value,
      alertOnOverflow: alertOnOverflow.value,
    }))
  }

  watch([presetId, customVolume, showBuildVolume, alertOnOverflow], saveSettings, { deep: true })

  async function fetchPresets() {
    loading.value = true
    try {
      presets.value = await api.getPrinterPresets()
    } catch (e) {
      console.error('Failed to fetch printer presets:', e)
    } finally {
      loading.value = false
    }
  }

  function setPreset(id: string) {
    presetId.value = id
  }

  function setCustomVolume(volume: BoundingBox) {
    customVolume.value = volume
  }

  function setShowBuildVolume(show: boolean) {
    showBuildVolume.value = show
  }

  function setAlertOnOverflow(alert: boolean) {
    alertOnOverflow.value = alert
  }

  function checkFits(partBoundingBox: BoundingBox | null): boolean {
    if (!partBoundingBox) {
      return true
    }
    const vol = buildVolume.value
    return (
      partBoundingBox.x <= vol.x &&
      partBoundingBox.y <= vol.y &&
      partBoundingBox.z <= vol.z
    )
  }

  return {
    presets,
    presetId,
    customVolume,
    showBuildVolume,
    alertOnOverflow,
    loading,
    currentPreset,
    buildVolume,
    fetchPresets,
    setPreset,
    setCustomVolume,
    setShowBuildVolume,
    setAlertOnOverflow,
    checkFits,
  }
})
