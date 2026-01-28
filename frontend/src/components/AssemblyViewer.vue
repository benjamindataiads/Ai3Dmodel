<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, reactive } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { TransformControls } from 'three/examples/jsm/controls/TransformControls.js'
import { getPreviewUrl, generateAssemblyPositions, type PartPositionInfo } from '@/services/api'
import { useSettingsStore } from '@/stores/settings'
import type { Part, PartSummary, BoundingBox, LLMProvider } from '@/types'

const settingsStore = useSettingsStore()

const props = defineProps<{
  parts: (Part | PartSummary)[]
  showBuildVolume: boolean
  buildVolume: { x: number; y: number; z: number }
}>()

const emit = defineEmits<{
  editPart: [partId: string]
}>()

const container = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const selectedPartId = ref<string | null>(null)
const transformMode = ref<'translate' | 'rotate'>('translate')

// Position/rotation for selected part (updated reactively)
const selectedPartTransform = reactive({
  posX: 0,
  posY: 0,
  posZ: 0,
  rotX: 0,
  rotY: 0,
  rotZ: 0,
})

// AI Composer state
const aiPrompt = ref('')
const aiGenerating = ref(false)
const aiError = ref<string | null>(null)

// Store bounding boxes for each part (needed for AI)
const partBoundingBoxes = new Map<string, BoundingBox>()

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let transformControls: TransformControls
let animationId: number
let resizeObserver: ResizeObserver | null = null
let buildVolumeBox: THREE.LineSegments | null = null

// Store meshes with their part IDs
const meshes = new Map<string, THREE.Mesh>()

// Color palette for parts
const PART_COLORS = [
  0x3b82f6, // blue
  0x22c55e, // green
  0xf59e0b, // amber
  0xef4444, // red
  0x8b5cf6, // violet
  0x06b6d4, // cyan
  0xf97316, // orange
  0xec4899, // pink
]

function getPartColor(index: number): number {
  return PART_COLORS[index % PART_COLORS.length]
}

function initScene() {
  if (!container.value) return

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1122) // Dark theme

  camera = new THREE.PerspectiveCamera(
    45,
    container.value.clientWidth / container.value.clientHeight,
    0.1,
    10000
  )
  camera.position.set(300, 300, 300)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // Transform controls for moving parts
  transformControls = new TransformControls(camera, renderer.domElement)
  transformControls.setMode('translate')
  transformControls.addEventListener('dragging-changed', (event) => {
    controls.enabled = !event.value
  })
  // Update position values when transform controls change
  transformControls.addEventListener('objectChange', () => {
    updateSelectedPartTransform()
  })
  scene.add(transformControls)

  // Lights - Dark theme with cyber glow
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0x06b6d4, 0.6) // Cyber tint
  directionalLight.position.set(100, 200, 100)
  scene.add(directionalLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 0.8)
  mainLight.position.set(-100, 100, 50)
  scene.add(mainLight)

  const backLight = new THREE.DirectionalLight(0xf97316, 0.2) // Accent orange
  backLight.position.set(-100, -100, -100)
  scene.add(backLight)

  // Grid - Cyber style
  const gridHelper = new THREE.GridHelper(500, 50, 0x1e3a5f, 0x0d1526)
  scene.add(gridHelper)

  // Raycaster for selection
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2()

  // Handle click for selection (single click = select only)
  renderer.domElement.addEventListener('click', (event) => {
    const rect = renderer.domElement.getBoundingClientRect()
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

    raycaster.setFromCamera(mouse, camera)
    const meshArray = Array.from(meshes.values())
    const intersects = raycaster.intersectObjects(meshArray)

    if (intersects.length > 0) {
      const mesh = intersects[0].object as THREE.Mesh
      const partId = Array.from(meshes.entries()).find(([_, m]) => m === mesh)?.[0]
      if (partId) {
        selectPartInScene(partId)
      }
    } else {
      deselectAll()
    }
  })

  // Keyboard shortcuts
  function onKeyDown(event: KeyboardEvent) {
    switch (event.key.toLowerCase()) {
      case 'g':
        setTransformMode('translate')
        break
      case 'r':
        setTransformMode('rotate')
        break
      case 'escape':
        deselectAll()
        break
    }
  }
  window.addEventListener('keydown', onKeyDown)

  function animate() {
    animationId = requestAnimationFrame(animate)
    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  resizeObserver = new ResizeObserver(onResize)
  resizeObserver.observe(container.value)
}

function onResize() {
  if (!container.value || !renderer || !camera) return
  
  const width = container.value.clientWidth
  const height = container.value.clientHeight
  
  if (width === 0 || height === 0) return
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

async function loadAllParts() {
  loading.value = true
  
  // Clear existing meshes
  meshes.forEach((mesh) => {
    scene.remove(mesh)
    mesh.geometry.dispose()
    ;(mesh.material as THREE.Material).dispose()
  })
  meshes.clear()
  transformControls?.detach()
  selectedPartId.value = null
  
  // Filter only generated parts
  const generatedParts = props.parts.filter(p => p.status === 'generated')
  console.log('Assembly: Loading', generatedParts.length, 'generated parts')
  
  if (generatedParts.length === 0) {
    loading.value = false
    return
  }
  
  let loadedCount = 0
  for (let i = 0; i < generatedParts.length; i++) {
    const part = generatedParts[i]
    try {
      await loadPartMesh(part, i)
      loadedCount++
    } catch (e) {
      console.error(`Assembly: Failed to load ${part.name}:`, e)
    }
  }
  
  console.log('Assembly: Loaded', loadedCount, 'meshes')
  loading.value = false
  
  if (meshes.size > 0) {
    resetPositions()
  }
}

async function loadPartMesh(part: Part | PartSummary, colorIndex: number) {
  const loader = new STLLoader()
  const url = `${getPreviewUrl(part.id)}?t=${Date.now()}&r=${Math.random()}`
  
  const geometry = await new Promise<THREE.BufferGeometry>((resolve, reject) => {
    loader.load(
      url, 
      resolve, 
      undefined, 
      (error) => reject(new Error(`Failed to load STL: ${error}`))
    )
  })

  geometry.computeBoundingBox()
  const bbox = geometry.boundingBox!
  const size = bbox.getSize(new THREE.Vector3())
  
  // Store bounding box dimensions for AI
  partBoundingBoxes.set(part.id, {
    x: Math.round(size.x * 10) / 10,
    y: Math.round(size.y * 10) / 10,
    z: Math.round(size.z * 10) / 10,
  })
  
  const center = new THREE.Vector3()
  bbox.getCenter(center)
  geometry.translate(-center.x, -center.y, -center.z)

  const material = new THREE.MeshPhongMaterial({
    color: getPartColor(colorIndex),
    specular: 0x444444,
    shininess: 30,
    transparent: true,
    opacity: 0.9,
  })
  
  const mesh = new THREE.Mesh(geometry, material)
  mesh.userData.partId = part.id
  mesh.userData.partName = part.name
  mesh.userData.colorIndex = colorIndex
  
  scene.add(mesh)
  meshes.set(part.id, mesh)
}

function updateSelectedPartTransform() {
  if (!selectedPartId.value) return
  const mesh = meshes.get(selectedPartId.value)
  if (!mesh) return
  
  selectedPartTransform.posX = Math.round(mesh.position.x * 10) / 10
  selectedPartTransform.posY = Math.round(mesh.position.y * 10) / 10
  selectedPartTransform.posZ = Math.round(mesh.position.z * 10) / 10
  selectedPartTransform.rotX = Math.round(THREE.MathUtils.radToDeg(mesh.rotation.x) * 10) / 10
  selectedPartTransform.rotY = Math.round(THREE.MathUtils.radToDeg(mesh.rotation.y) * 10) / 10
  selectedPartTransform.rotZ = Math.round(THREE.MathUtils.radToDeg(mesh.rotation.z) * 10) / 10
}

function applyPositionFromInputs() {
  if (!selectedPartId.value) return
  const mesh = meshes.get(selectedPartId.value)
  if (!mesh) return
  
  mesh.position.set(
    selectedPartTransform.posX,
    selectedPartTransform.posY,
    selectedPartTransform.posZ
  )
  mesh.rotation.set(
    THREE.MathUtils.degToRad(selectedPartTransform.rotX),
    THREE.MathUtils.degToRad(selectedPartTransform.rotY),
    THREE.MathUtils.degToRad(selectedPartTransform.rotZ)
  )
}

function selectPartInScene(partId: string) {
  selectedPartId.value = partId
  
  // Highlight selected part
  meshes.forEach((mesh, id) => {
    const material = mesh.material as THREE.MeshPhongMaterial
    material.opacity = id === partId ? 1 : 0.5
    material.emissive.setHex(id === partId ? 0x222222 : 0x000000)
  })
  
  // Attach transform controls
  const selectedMesh = meshes.get(partId)
  if (selectedMesh) {
    transformControls.attach(selectedMesh)
    updateSelectedPartTransform()
  }
}

function deselectAll() {
  selectedPartId.value = null
  transformControls?.detach()
  
  meshes.forEach((mesh) => {
    const material = mesh.material as THREE.MeshPhongMaterial
    material.opacity = 0.9
    material.emissive.setHex(0x000000)
  })
}

function setTransformMode(mode: 'translate' | 'rotate') {
  transformMode.value = mode
  transformControls?.setMode(mode)
}

function fitCameraToScene() {
  if (meshes.size === 0) return

  const box = new THREE.Box3()
  meshes.forEach((mesh) => {
    box.expandByObject(mesh)
  })

  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = camera.fov * (Math.PI / 180)
  const distance = maxDim / (2 * Math.tan(fov / 2)) * 2

  const center = box.getCenter(new THREE.Vector3())
  camera.position.set(center.x + distance, center.y + distance, center.z + distance)
  controls.target.copy(center)
  controls.update()
}

function updateBuildVolume() {
  if (buildVolumeBox) {
    scene.remove(buildVolumeBox)
    buildVolumeBox.geometry.dispose()
    ;(buildVolumeBox.material as THREE.Material).dispose()
    buildVolumeBox = null
  }

  if (!props.showBuildVolume) return

  const { x, y, z } = props.buildVolume
  const geometry = new THREE.BoxGeometry(x, z, y)
  const edges = new THREE.EdgesGeometry(geometry)
  const material = new THREE.LineBasicMaterial({ color: 0x94a3b8, opacity: 0.5, transparent: true })
  
  buildVolumeBox = new THREE.LineSegments(edges, material)
  buildVolumeBox.position.y = z / 2
  scene.add(buildVolumeBox)
}

function resetPositions() {
  const partsArray = Array.from(meshes.values())
  
  // Calculate total width needed
  let totalWidth = 0
  partsArray.forEach((mesh) => {
    const bbox = new THREE.Box3().setFromObject(mesh)
    totalWidth += bbox.getSize(new THREE.Vector3()).x
  })
  totalWidth += (partsArray.length - 1) * 30 // spacing
  
  // Position parts in a row, centered
  let xOffset = -totalWidth / 2
  partsArray.forEach((mesh) => {
    const bbox = new THREE.Box3().setFromObject(mesh)
    const size = bbox.getSize(new THREE.Vector3())
    
    mesh.position.x = xOffset + size.x / 2
    mesh.position.y = size.y / 2
    mesh.position.z = 0
    mesh.rotation.set(0, 0, 0)
    
    xOffset += size.x + 30
  })
  
  deselectAll()
  fitCameraToScene()
}

function stackParts() {
  const partsArray = Array.from(meshes.values())
  
  let yOffset = 0
  partsArray.forEach((mesh) => {
    const bbox = new THREE.Box3().setFromObject(mesh)
    const size = bbox.getSize(new THREE.Vector3())
    
    mesh.position.set(0, yOffset + size.y / 2, 0)
    mesh.rotation.set(0, 0, 0)
    yOffset += size.y + 5
  })
  
  deselectAll()
  fitCameraToScene()
}

function alignOnGround() {
  meshes.forEach((mesh) => {
    const bbox = new THREE.Box3().setFromObject(mesh)
    const size = bbox.getSize(new THREE.Vector3())
    mesh.position.y = size.y / 2
  })
  
  if (selectedPartId.value) {
    updateSelectedPartTransform()
  }
  fitCameraToScene()
}

function centerSelected() {
  if (!selectedPartId.value) return
  const mesh = meshes.get(selectedPartId.value)
  if (!mesh) return
  
  const bbox = new THREE.Box3().setFromObject(mesh)
  const size = bbox.getSize(new THREE.Vector3())
  mesh.position.set(0, size.y / 2, 0)
  mesh.rotation.set(0, 0, 0)
  updateSelectedPartTransform()
}

async function generateAIPositions() {
  if (!aiPrompt.value.trim() || aiGenerating.value) return
  
  aiGenerating.value = true
  aiError.value = null
  
  try {
    // Build parts info for the API
    const partsInfo: PartPositionInfo[] = []
    
    meshes.forEach((mesh, partId) => {
      const part = generatedParts.value.find(p => p.id === partId)
      if (!part) return
      
      const bbox = partBoundingBoxes.get(partId)
      if (!bbox) return
      
      partsInfo.push({
        id: partId,
        name: part.name,
        bounding_box: bbox,
        current_position: {
          x: mesh.position.x,
          y: mesh.position.y,
          z: mesh.position.z,
          rotX: THREE.MathUtils.radToDeg(mesh.rotation.x),
          rotY: THREE.MathUtils.radToDeg(mesh.rotation.y),
          rotZ: THREE.MathUtils.radToDeg(mesh.rotation.z),
        }
      })
    })
    
    if (partsInfo.length === 0) {
      aiError.value = "Aucune pièce à positionner"
      return
    }
    
    // Call AI API
    const response = await generateAssemblyPositions(
      aiPrompt.value,
      partsInfo,
      settingsStore.llmProvider as LLMProvider,
      settingsStore.currentModel
    )
    
    // Apply positions
    for (const [partId, pos] of Object.entries(response.positions)) {
      const mesh = meshes.get(partId)
      if (!mesh) continue
      
      mesh.position.set(pos.x, pos.y, pos.z)
      mesh.rotation.set(
        THREE.MathUtils.degToRad(pos.rotX),
        THREE.MathUtils.degToRad(pos.rotY),
        THREE.MathUtils.degToRad(pos.rotZ)
      )
    }
    
    // Update selected part transform if any
    if (selectedPartId.value) {
      updateSelectedPartTransform()
    }
    
    fitCameraToScene()
    aiPrompt.value = ''
    
  } catch (e: any) {
    console.error('AI assembly error:', e)
    aiError.value = e.response?.data?.detail || e.message || "Erreur lors de la génération"
  } finally {
    aiGenerating.value = false
  }
}

onMounted(() => {
  initScene()
  loadAllParts()
  updateBuildVolume()
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  window.removeEventListener('keydown', () => {})
  transformControls?.dispose()
  renderer?.dispose()
})

watch(() => props.parts, () => {
  loadAllParts()
}, { deep: true })

watch([() => props.showBuildVolume, () => props.buildVolume], () => {
  updateBuildVolume()
}, { deep: true })

const generatedParts = computed(() => 
  props.parts.filter(p => p.status === 'generated')
)

const selectedPartName = computed(() => {
  if (!selectedPartId.value) return null
  return generatedParts.value.find(p => p.id === selectedPartId.value)?.name
})
</script>

<template>
  <div class="relative w-full h-full bg-dark-900 flex">
    <!-- 3D Viewer -->
    <div ref="container" class="flex-1 h-full"></div>
    
    <!-- Right Panel - Part List & Selected Part Controls -->
    <div class="w-80 glass border-l border-white/5 flex flex-col h-full overflow-hidden">
      <!-- Parts list -->
      <div class="border-b border-white/5">
        <div class="px-4 py-3 bg-dark-800/50 border-b border-white/5">
          <h3 class="font-semibold text-slate-200">Pièces</h3>
        </div>
        <div class="max-h-48 overflow-y-auto">
          <button
            v-for="(part, idx) in generatedParts"
            :key="part.id"
            @click="selectPartInScene(part.id)"
            :class="[
              'w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors border-b border-white/5 last:border-0',
              selectedPartId === part.id ? 'bg-cyber-500/10' : 'hover:bg-white/5'
            ]"
          >
            <span 
              class="w-4 h-4 rounded shrink-0"
              :style="{ backgroundColor: '#' + getPartColor(idx).toString(16).padStart(6, '0') }"
            ></span>
            <span class="truncate text-sm" :class="selectedPartId === part.id ? 'text-cyber-400 font-medium' : 'text-slate-300'">
              {{ part.name }}
            </span>
          </button>
        </div>
      </div>
      
      <!-- AI Composer -->
      <div class="border-b border-white/5">
        <div class="px-4 py-3 bg-gradient-to-r from-cyber-900/30 to-accent-900/30 border-b border-white/5">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 class="font-semibold text-slate-200 text-sm">Composer IA</h3>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">Positionnez les pièces en langage naturel</p>
        </div>
        <div class="p-3">
          <textarea
            v-model="aiPrompt"
            placeholder="Ex: Empile toutes les pièces verticalement avec 5mm d'espacement..."
            class="w-full px-3 py-2 text-sm bg-dark-800 border border-white/10 rounded-xl text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-accent-500/50 focus:border-accent-500/50 resize-none"
            rows="2"
            :disabled="aiGenerating || generatedParts.length === 0"
            @keydown.ctrl.enter="generateAIPositions"
          ></textarea>
          
          <div v-if="aiError" class="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400">
            {{ aiError }}
          </div>
          
          <button
            @click="generateAIPositions"
            :disabled="!aiPrompt.trim() || aiGenerating || generatedParts.length === 0"
            class="mt-2 w-full px-3 py-2 text-sm bg-gradient-to-r from-cyber-600 to-accent-600 text-white rounded-xl hover:from-cyber-500 hover:to-accent-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-cyber"
          >
            <svg v-if="aiGenerating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {{ aiGenerating ? 'Génération...' : 'Appliquer' }}
          </button>
          
          <p class="mt-2 text-xs text-slate-500 text-center">Ctrl+Entrée pour valider</p>
        </div>
      </div>
      
      <!-- Selected Part Controls -->
      <div v-if="selectedPartId" class="flex-1 overflow-y-auto">
        <div class="px-4 py-3 bg-cyber-500/10 border-b border-cyber-500/20">
          <h4 class="font-medium text-cyber-400">{{ selectedPartName }}</h4>
          <p class="text-xs text-slate-500 mt-0.5">Position et rotation</p>
        </div>
        
        <!-- Transform mode toggle -->
        <div class="px-4 py-3 border-b border-white/5">
          <div class="flex rounded-xl bg-dark-800 p-1">
            <button
              @click="setTransformMode('translate')"
              :class="[
                'flex-1 px-3 py-1.5 text-xs rounded-lg transition-all',
                transformMode === 'translate' 
                  ? 'bg-cyber-500/20 text-cyber-400 border border-cyber-500/30 font-medium' 
                  : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Déplacer
            </button>
            <button
              @click="setTransformMode('rotate')"
              :class="[
                'flex-1 px-3 py-1.5 text-xs rounded-lg transition-all',
                transformMode === 'rotate' 
                  ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30 font-medium' 
                  : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Rotation
            </button>
          </div>
        </div>
        
        <!-- Position inputs -->
        <div class="px-4 py-3 border-b border-white/5">
          <div class="text-xs font-medium text-slate-500 uppercase mb-2">Position (mm)</div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-xs text-slate-500 mb-1">X</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.posX"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="1"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Y</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.posY"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="1"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Z</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.posZ"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="1"
              />
            </div>
          </div>
        </div>
        
        <!-- Rotation inputs -->
        <div class="px-4 py-3 border-b border-white/5">
          <div class="text-xs font-medium text-slate-500 uppercase mb-2">Rotation (degrés)</div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-xs text-slate-500 mb-1">X</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.rotX"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="15"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Y</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.rotY"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="15"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Z</label>
              <input 
                type="number" 
                v-model.number="selectedPartTransform.rotZ"
                @change="applyPositionFromInputs"
                class="w-full px-2 py-1.5 text-sm bg-dark-800 border border-white/10 rounded-lg text-slate-200"
                step="15"
              />
            </div>
          </div>
        </div>
        
        <!-- Quick actions for selected part -->
        <div class="px-4 py-3 space-y-2">
          <button
            @click="centerSelected"
            class="w-full px-3 py-2 text-sm text-slate-400 hover:text-cyber-400 hover:bg-white/5 border border-white/10 rounded-xl flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            Centrer sur l'origine
          </button>
          <button
            @click="emit('editPart', selectedPartId)"
            class="w-full px-3 py-2 text-sm bg-cyber-500/10 text-cyber-400 hover:bg-cyber-500/20 border border-cyber-500/30 rounded-xl flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Éditer le code
          </button>
        </div>
      </div>
      
      <!-- No selection message -->
      <div v-else class="flex-1 flex items-center justify-center p-4">
        <div class="text-center text-slate-400">
          <svg class="w-12 h-12 mx-auto mb-2 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
          <p class="text-sm">Cliquez sur une pièce pour la sélectionner</p>
        </div>
      </div>
      
      <!-- Global actions -->
      <div class="border-t border-white/5 px-4 py-3 bg-dark-800/50">
        <div class="text-xs font-medium text-slate-500 uppercase mb-2">Actions globales</div>
        <div class="space-y-1">
          <button
            @click="resetPositions"
            class="w-full px-3 py-1.5 text-xs text-slate-400 hover:text-cyber-400 hover:bg-white/5 rounded-lg flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Réinitialiser les positions
          </button>
          <button
            @click="stackParts"
            class="w-full px-3 py-1.5 text-xs text-slate-400 hover:text-cyber-400 hover:bg-white/5 rounded-lg flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Empiler verticalement
          </button>
          <button
            @click="alignOnGround"
            class="w-full px-3 py-1.5 text-xs text-slate-400 hover:text-cyber-400 hover:bg-white/5 rounded-lg flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            Aligner sur le sol
          </button>
          <button
            @click="fitCameraToScene"
            class="w-full px-3 py-1.5 text-xs text-slate-400 hover:text-cyber-400 hover:bg-white/5 rounded-lg flex items-center gap-2 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
            </svg>
            Recadrer la vue
          </button>
        </div>
      </div>
    </div>
    
    <!-- Loading overlay -->
    <div v-if="loading" class="absolute inset-0 bg-dark-900/90 backdrop-blur-sm flex items-center justify-center z-10">
      <div class="glass rounded-xl p-4 flex items-center gap-3 cyber-border">
        <svg class="w-6 h-6 animate-spin text-cyber-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span class="text-slate-300">Chargement des pièces...</span>
      </div>
    </div>
    
    <!-- No parts message -->
    <div v-if="generatedParts.length === 0 && !loading" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center glass rounded-2xl p-8 cyber-border">
        <svg class="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <p class="text-lg font-medium text-slate-300">Aucune pièce générée</p>
        <p class="text-sm mt-1 text-slate-500">Passez en mode Édition pour créer des pièces</p>
      </div>
    </div>
    
    <!-- Keyboard shortcuts hint -->
    <div class="absolute bottom-4 left-4 text-xs text-slate-400 glass cyber-border rounded-xl px-3 py-2">
      <div class="flex gap-4">
        <span><kbd class="px-1.5 py-0.5 bg-dark-700 rounded text-cyber-400">G</kbd> Déplacer</span>
        <span><kbd class="px-1.5 py-0.5 bg-dark-700 rounded text-cyber-400">R</kbd> Rotation</span>
        <span><kbd class="px-1.5 py-0.5 bg-dark-700 rounded text-cyber-400">Echap</kbd> Désélectionner</span>
      </div>
    </div>
  </div>
</template>
