<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

const props = defineProps<{
  width?: number
  height?: number
  backgroundColor?: string
  initialImage?: string
}>()

const emit = defineEmits<{
  save: [dataUrl: string]
  change: []
}>()

// Canvas refs
const canvasContainer = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const ctx = ref<CanvasRenderingContext2D | null>(null)

// Drawing state
const isDrawing = ref(false)
const lastPoint = ref<{ x: number; y: number } | null>(null)
const currentTool = ref<'pen' | 'eraser' | 'highlighter'>('pen')
const currentColor = ref('#ffffff')
const brushSize = ref(3)
const opacity = ref(1)

// History for undo/redo
const history = ref<ImageData[]>([])
const historyIndex = ref(-1)
const maxHistory = 50

// Pressure sensitivity
const pressureEnabled = ref(true)
const lastPressure = ref(0.5)

// Canvas dimensions
const canvasWidth = computed(() => props.width || 800)
const canvasHeight = computed(() => props.height || 600)

// Colors palette
const colorPalette = [
  '#ffffff', '#000000', '#ff4444', '#44ff44', '#4444ff',
  '#ffff44', '#ff44ff', '#44ffff', '#ff8844', '#8844ff',
]

// Brush sizes
const brushSizes = [1, 2, 3, 5, 8, 12, 20, 30]

onMounted(() => {
  initCanvas()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function initCanvas() {
  if (!canvas.value) return
  
  ctx.value = canvas.value.getContext('2d', { willReadFrequently: true })
  if (!ctx.value) return
  
  // Set canvas size
  canvas.value.width = canvasWidth.value
  canvas.value.height = canvasHeight.value
  
  // Fill with background
  ctx.value.fillStyle = props.backgroundColor || '#1a1a2e'
  ctx.value.fillRect(0, 0, canvas.value.width, canvas.value.height)
  
  // Load initial image if provided
  if (props.initialImage) {
    loadImage(props.initialImage)
  }
  
  // Save initial state
  saveToHistory()
  
  // Setup touch events with passive: false for preventDefault
  canvas.value.addEventListener('touchstart', handleTouchStart, { passive: false })
  canvas.value.addEventListener('touchmove', handleTouchMove, { passive: false })
  canvas.value.addEventListener('touchend', handleTouchEnd, { passive: false })
  canvas.value.addEventListener('touchcancel', handleTouchEnd, { passive: false })
}

function handleResize() {
  // Preserve drawing on resize
  if (!canvas.value || !ctx.value) return
  
  const imageData = ctx.value.getImageData(0, 0, canvas.value.width, canvas.value.height)
  canvas.value.width = canvasWidth.value
  canvas.value.height = canvasHeight.value
  ctx.value.putImageData(imageData, 0, 0)
}

// Get position from mouse/touch event
function getPosition(e: MouseEvent | Touch): { x: number; y: number } {
  if (!canvas.value) return { x: 0, y: 0 }
  
  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height
  
  const clientX = 'clientX' in e ? e.clientX : e.clientX
  const clientY = 'clientY' in e ? e.clientY : e.clientY
  
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

// Get pressure from pointer event
function getPressure(e: PointerEvent | Touch): number {
  if (!pressureEnabled.value) return 0.5
  
  // Check for pressure in touch event
  if ('force' in e && typeof e.force === 'number' && e.force > 0) {
    return Math.min(e.force, 1)
  }
  
  // Check for pressure in pointer event
  if ('pressure' in e && typeof e.pressure === 'number' && e.pressure > 0) {
    return e.pressure
  }
  
  return 0.5
}

// Mouse events
function handleMouseDown(e: MouseEvent) {
  if (e.button !== 0) return // Only left click
  startDrawing(getPosition(e), 0.5)
}

function handleMouseMove(e: MouseEvent) {
  if (!isDrawing.value) return
  draw(getPosition(e), 0.5)
}

function handleMouseUp() {
  stopDrawing()
}

// Pointer events (for pressure sensitivity)
function handlePointerDown(e: PointerEvent) {
  if (e.pointerType === 'touch') return // Handle touch separately
  startDrawing(getPosition(e), getPressure(e))
}

function handlePointerMove(e: PointerEvent) {
  if (!isDrawing.value || e.pointerType === 'touch') return
  draw(getPosition(e), getPressure(e))
}

function handlePointerUp(e: PointerEvent) {
  if (e.pointerType === 'touch') return
  stopDrawing()
}

// Touch events (for iPad/stylus)
function handleTouchStart(e: TouchEvent) {
  e.preventDefault() // Prevent scrolling
  
  const touch = e.touches[0]
  const pressure = getPressure(touch)
  startDrawing(getPosition(touch), pressure)
}

function handleTouchMove(e: TouchEvent) {
  e.preventDefault()
  if (!isDrawing.value) return
  
  const touch = e.touches[0]
  const pressure = getPressure(touch)
  draw(getPosition(touch), pressure)
}

function handleTouchEnd(e: TouchEvent) {
  e.preventDefault()
  stopDrawing()
}

// Drawing functions
function startDrawing(point: { x: number; y: number }, pressure: number) {
  isDrawing.value = true
  lastPoint.value = point
  lastPressure.value = pressure
  
  // Draw initial dot
  drawDot(point, pressure)
}

function draw(point: { x: number; y: number }, pressure: number) {
  if (!ctx.value || !lastPoint.value) return
  
  // Smooth pressure transition
  const smoothPressure = lastPressure.value * 0.7 + pressure * 0.3
  lastPressure.value = smoothPressure
  
  drawLine(lastPoint.value, point, smoothPressure)
  lastPoint.value = point
  
  emit('change')
}

function stopDrawing() {
  if (isDrawing.value) {
    isDrawing.value = false
    lastPoint.value = null
    saveToHistory()
  }
}

function drawDot(point: { x: number; y: number }, pressure: number) {
  if (!ctx.value) return
  
  const size = calculateBrushSize(pressure)
  
  ctx.value.save()
  setupBrush(pressure)
  
  ctx.value.beginPath()
  ctx.value.arc(point.x, point.y, size / 2, 0, Math.PI * 2)
  ctx.value.fill()
  
  ctx.value.restore()
}

function drawLine(from: { x: number; y: number }, to: { x: number; y: number }, pressure: number) {
  if (!ctx.value) return
  
  const size = calculateBrushSize(pressure)
  
  ctx.value.save()
  setupBrush(pressure)
  
  ctx.value.lineWidth = size
  ctx.value.lineCap = 'round'
  ctx.value.lineJoin = 'round'
  
  ctx.value.beginPath()
  ctx.value.moveTo(from.x, from.y)
  ctx.value.lineTo(to.x, to.y)
  ctx.value.stroke()
  
  ctx.value.restore()
}

function setupBrush(pressure: number) {
  if (!ctx.value) return
  
  if (currentTool.value === 'eraser') {
    ctx.value.globalCompositeOperation = 'destination-out'
    ctx.value.strokeStyle = 'rgba(0,0,0,1)'
    ctx.value.fillStyle = 'rgba(0,0,0,1)'
  } else if (currentTool.value === 'highlighter') {
    ctx.value.globalCompositeOperation = 'multiply'
    ctx.value.globalAlpha = 0.3
    ctx.value.strokeStyle = currentColor.value
    ctx.value.fillStyle = currentColor.value
  } else {
    ctx.value.globalCompositeOperation = 'source-over'
    ctx.value.globalAlpha = opacity.value * (0.5 + pressure * 0.5)
    ctx.value.strokeStyle = currentColor.value
    ctx.value.fillStyle = currentColor.value
  }
}

function calculateBrushSize(pressure: number): number {
  if (currentTool.value === 'highlighter') {
    return brushSize.value * 3
  }
  
  // Pressure affects size
  const pressureMultiplier = 0.5 + pressure * 0.5
  return brushSize.value * pressureMultiplier
}

// History management
function saveToHistory() {
  if (!ctx.value || !canvas.value) return
  
  // Remove any redo history
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }
  
  // Add current state
  const imageData = ctx.value.getImageData(0, 0, canvas.value.width, canvas.value.height)
  history.value.push(imageData)
  
  // Limit history size
  if (history.value.length > maxHistory) {
    history.value.shift()
  }
  
  historyIndex.value = history.value.length - 1
}

function undo() {
  if (historyIndex.value > 0) {
    historyIndex.value--
    restoreFromHistory()
  }
}

function redo() {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++
    restoreFromHistory()
  }
}

function restoreFromHistory() {
  if (!ctx.value || !canvas.value) return
  
  const imageData = history.value[historyIndex.value]
  if (imageData) {
    ctx.value.putImageData(imageData, 0, 0)
    emit('change')
  }
}

// Clear canvas
function clear() {
  if (!ctx.value || !canvas.value) return
  
  ctx.value.fillStyle = props.backgroundColor || '#1a1a2e'
  ctx.value.fillRect(0, 0, canvas.value.width, canvas.value.height)
  
  saveToHistory()
  emit('change')
}

// Load image onto canvas
function loadImage(src: string) {
  if (!ctx.value || !canvas.value) return
  
  const img = new Image()
  img.onload = () => {
    if (!ctx.value || !canvas.value) return
    
    // Clear canvas
    ctx.value.fillStyle = props.backgroundColor || '#1a1a2e'
    ctx.value.fillRect(0, 0, canvas.value.width, canvas.value.height)
    
    // Calculate scaling to fit
    const scale = Math.min(
      canvas.value.width / img.width,
      canvas.value.height / img.height
    )
    
    const x = (canvas.value.width - img.width * scale) / 2
    const y = (canvas.value.height - img.height * scale) / 2
    
    ctx.value.drawImage(img, x, y, img.width * scale, img.height * scale)
    saveToHistory()
  }
  img.src = src
}

// Export canvas as data URL
function save(): string {
  if (!canvas.value) return ''
  
  const dataUrl = canvas.value.toDataURL('image/png')
  emit('save', dataUrl)
  return dataUrl
}

// Expose methods
defineExpose({
  save,
  clear,
  undo,
  redo,
  loadImage,
})

// Watch for initial image changes
watch(() => props.initialImage, (newImage) => {
  if (newImage) {
    loadImage(newImage)
  }
})

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
    e.preventDefault()
    if (e.shiftKey) {
      redo()
    } else {
      undo()
    }
  }
}
</script>

<template>
  <div class="sketch-canvas flex flex-col h-full bg-dark-900" @keydown="handleKeydown" tabindex="0">
    <!-- Toolbar -->
    <div class="flex items-center gap-4 p-3 border-b border-white/10 bg-dark-850 flex-wrap">
      <!-- Tools -->
      <div class="flex items-center gap-1 bg-dark-800 rounded-lg p-1">
        <button
          @click="currentTool = 'pen'"
          :class="[
            'p-2 rounded-lg transition-all',
            currentTool === 'pen' ? 'bg-cyber-500/20 text-cyber-400' : 'text-slate-400 hover:text-white hover:bg-white/5'
          ]"
          title="Stylo"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        </button>
        <button
          @click="currentTool = 'highlighter'"
          :class="[
            'p-2 rounded-lg transition-all',
            currentTool === 'highlighter' ? 'bg-amber-500/20 text-amber-400' : 'text-slate-400 hover:text-white hover:bg-white/5'
          ]"
          title="Surligneur"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M18.5 1.5l-14 14 4 4 14-14-4-4zm-16 18l4-4-4 4zm16-4l-4 4 4-4z"/>
          </svg>
        </button>
        <button
          @click="currentTool = 'eraser'"
          :class="[
            'p-2 rounded-lg transition-all',
            currentTool === 'eraser' ? 'bg-red-500/20 text-red-400' : 'text-slate-400 hover:text-white hover:bg-white/5'
          ]"
          title="Gomme"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
      
      <!-- Colors -->
      <div class="flex items-center gap-1">
        <div
          v-for="color in colorPalette"
          :key="color"
          @click="currentColor = color; currentTool = 'pen'"
          :class="[
            'w-6 h-6 rounded-full cursor-pointer border-2 transition-all',
            currentColor === color && currentTool !== 'eraser' ? 'border-white scale-110' : 'border-transparent hover:scale-105'
          ]"
          :style="{ backgroundColor: color }"
        />
        <input
          type="color"
          v-model="currentColor"
          @change="currentTool = 'pen'"
          class="w-6 h-6 rounded cursor-pointer bg-transparent"
          title="Couleur personnalisée"
        />
      </div>
      
      <!-- Brush size -->
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-500">Taille:</span>
        <div class="flex items-center gap-1">
          <button
            v-for="size in brushSizes"
            :key="size"
            @click="brushSize = size"
            :class="[
              'w-7 h-7 rounded flex items-center justify-center transition-all',
              brushSize === size ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-white hover:bg-white/5'
            ]"
          >
            <div 
              class="rounded-full bg-current"
              :style="{ width: `${Math.min(size, 16)}px`, height: `${Math.min(size, 16)}px` }"
            />
          </button>
        </div>
      </div>
      
      <!-- Spacer -->
      <div class="flex-1" />
      
      <!-- Actions -->
      <div class="flex items-center gap-2">
        <button
          @click="undo"
          :disabled="historyIndex <= 0"
          class="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed"
          title="Annuler (Cmd+Z)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
          </svg>
        </button>
        <button
          @click="redo"
          :disabled="historyIndex >= history.length - 1"
          class="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed"
          title="Rétablir (Cmd+Shift+Z)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
          </svg>
        </button>
        <button
          @click="clear"
          class="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10"
          title="Effacer tout"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Canvas area -->
    <div 
      ref="canvasContainer" 
      class="flex-1 flex items-center justify-center overflow-hidden p-4 bg-dark-950"
    >
      <canvas
        ref="canvas"
        :width="canvasWidth"
        :height="canvasHeight"
        class="max-w-full max-h-full rounded-lg shadow-2xl cursor-crosshair touch-none"
        style="image-rendering: pixelated;"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseUp"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
      />
    </div>
    
    <!-- Footer with pressure indicator -->
    <div class="flex items-center justify-between px-4 py-2 border-t border-white/5 bg-dark-850 text-xs text-slate-500">
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            v-model="pressureEnabled"
            class="w-3.5 h-3.5 rounded bg-dark-700 border-white/20 text-cyber-500 focus:ring-cyber-500/50"
          />
          <span>Sensibilité à la pression</span>
        </label>
        <span v-if="pressureEnabled && lastPressure > 0.1">
          Pression: {{ Math.round(lastPressure * 100) }}%
        </span>
      </div>
      <div>
        {{ canvasWidth }} × {{ canvasHeight }}px
      </div>
    </div>
  </div>
</template>

<style scoped>
.sketch-canvas:focus {
  outline: none;
}

canvas {
  touch-action: none;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}
</style>
