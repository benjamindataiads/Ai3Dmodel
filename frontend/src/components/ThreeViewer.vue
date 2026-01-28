<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { TransformControls } from 'three/examples/jsm/controls/TransformControls.js'
import { getPreviewUrl } from '@/services/api'
import { useSettingsStore } from '@/stores/settings'
import type { BoundingBox } from '@/types'

const props = defineProps<{
  partId: string | null
  boundingBox: BoundingBox | null
  showBuildVolume: boolean
  buildVolume: BoundingBox
  fits: boolean
  updateKey?: string // Used to force reload when part is regenerated
  editMode?: boolean
}>()

const emit = defineEmits<{
  'generate-code': [code: string]
  'shapes-changed': [shapes: EditorShape[]]
}>()

// Editor shape interface
interface EditorShape {
  id: string
  type: 'box' | 'cylinder' | 'sphere' | 'cone'
  mesh: THREE.Mesh
  params: Record<string, number>
  position: { x: number; y: number; z: number }
  rotation: { x: number; y: number; z: number }
}

// Editor state
const editorEnabled = ref(false)
const currentTool = ref<'select' | 'box' | 'cylinder' | 'sphere' | 'cone' | 'move' | 'rotate' | 'scale'>('select')
const editorShapes = ref<EditorShape[]>([])
const selectedShapeId = ref<string | null>(null)
const showShapePanel = ref(false)

const settingsStore = useSettingsStore()
const container = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let labelRenderer: CSS2DRenderer
let controls: OrbitControls
let transformControls: TransformControls | null = null
let currentMesh: THREE.Mesh | null = null
let buildVolumeBox: THREE.LineSegments | null = null
let dimensionLabels: CSS2DObject[] = []
let animationId: number
let resizeObserver: ResizeObserver | null = null
let currentLoadId = 0 // Track current load to cancel stale requests
let raycaster = new THREE.Raycaster()
let mouse = new THREE.Vector2()
let gridPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)

const displayUnit = computed(() => settingsStore.unit)

function formatDimension(valueMm: number): string {
  const displayValue = settingsStore.convertToDisplay(valueMm)
  return `${displayValue.toFixed(1)} ${displayUnit.value}`
}

function initScene() {
  if (!container.value) return

  // Scene - Dark theme
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1122)

  // Camera
  camera = new THREE.PerspectiveCamera(
    45,
    container.value.clientWidth / container.value.clientHeight,
    0.1,
    10000
  )
  camera.position.set(200, 200, 200)

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.value.appendChild(renderer.domElement)

  // Label renderer
  labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(container.value.clientWidth, container.value.clientHeight)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.pointerEvents = 'none'
  container.value.appendChild(labelRenderer.domElement)

  // Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // Lights - Adjusted for dark theme with cyber glow
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

  // Axes - Custom colors for dark theme
  const axesHelper = new THREE.AxesHelper(100)
  scene.add(axesHelper)

  // Animation loop
  function animate() {
    animationId = requestAnimationFrame(animate)
    controls.update()
    renderer.render(scene, camera)
    labelRenderer.render(scene, camera)
  }
  animate()

  // Resize handler using ResizeObserver for container changes
  resizeObserver = new ResizeObserver(onResize)
  resizeObserver.observe(container.value)
  window.addEventListener('resize', onResize)
}

function onResize() {
  if (!container.value || !renderer || !camera || !labelRenderer) return
  
  const width = container.value.clientWidth
  const height = container.value.clientHeight
  
  if (width === 0 || height === 0) return
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
  labelRenderer.setSize(width, height)
}

function clearCurrentMesh() {
  if (currentMesh) {
    scene.remove(currentMesh)
    currentMesh.geometry.dispose()
    ;(currentMesh.material as THREE.Material).dispose()
    currentMesh = null
  }
  // Clear dimension labels too
  dimensionLabels.forEach(label => {
    scene.remove(label)
  })
  dimensionLabels = []
  
  // Force render to show cleared scene
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

async function loadSTL(partId: string) {
  // Increment load ID to cancel any pending loads
  const thisLoadId = ++currentLoadId
  
  console.log('ThreeViewer: Loading STL for', partId, 'loadId:', thisLoadId)
  loading.value = true
  error.value = null

  // Remove existing mesh BEFORE loading new one
  clearCurrentMesh()

  try {
    const loader = new STLLoader()
    // Add cache-busting with timestamp AND random to ensure unique URL
    const url = `${getPreviewUrl(partId)}?t=${Date.now()}&r=${Math.random()}`
    console.log('ThreeViewer: Fetching', url)
    
    const geometry = await new Promise<THREE.BufferGeometry>((resolve, reject) => {
      loader.load(
        url,
        resolve,
        undefined,
        reject
      )
    })

    // Check if this load is still current (user might have switched parts)
    if (thisLoadId !== currentLoadId) {
      console.log('ThreeViewer: Ignoring stale load', thisLoadId, 'current is', currentLoadId)
      geometry.dispose()
      return
    }

    // Center geometry
    geometry.computeBoundingBox()
    const center = new THREE.Vector3()
    geometry.boundingBox!.getCenter(center)
    geometry.translate(-center.x, -center.y, -center.z)

    // Create mesh - Cyber style material
    const material = new THREE.MeshPhongMaterial({
      color: 0x06b6d4, // Cyber cyan
      specular: 0x22d3ee,
      shininess: 60,
      emissive: 0x06b6d4,
      emissiveIntensity: 0.05,
    })
    currentMesh = new THREE.Mesh(geometry, material)
    
    // Position on grid
    const bbox = geometry.boundingBox!
    currentMesh.position.y = -bbox.min.y
    
    scene.add(currentMesh)

    // Fit camera to object
    fitCameraToObject()
    
    // Update dimension labels
    updateDimensionLabels()
  } catch (e: any) {
    // Only show error if this is still the current load
    if (thisLoadId === currentLoadId) {
      error.value = 'Impossible de charger le modèle'
      console.error('Failed to load STL:', e)
    }
  } finally {
    // Only update loading state if this is still the current load
    if (thisLoadId === currentLoadId) {
      loading.value = false
    }
  }
}

function fitCameraToObject() {
  if (!currentMesh) return

  const bbox = new THREE.Box3().setFromObject(currentMesh)
  const size = bbox.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = camera.fov * (Math.PI / 180)
  const distance = maxDim / (2 * Math.tan(fov / 2)) * 1.5

  const center = bbox.getCenter(new THREE.Vector3())
  camera.position.set(center.x + distance, center.y + distance, center.z + distance)
  controls.target.copy(center)
  controls.update()
}

function updateBuildVolume() {
  // Remove existing
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
  
  const color = props.fits ? 0x22c55e : 0xef4444
  const material = new THREE.LineBasicMaterial({ color, opacity: 0.5, transparent: true })
  
  buildVolumeBox = new THREE.LineSegments(edges, material)
  buildVolumeBox.position.y = z / 2
  scene.add(buildVolumeBox)
}

function updateDimensionLabels() {
  // Remove existing labels
  dimensionLabels.forEach(label => {
    scene.remove(label)
  })
  dimensionLabels = []

  if (!props.boundingBox) return

  const { x, y, z } = props.boundingBox
  const offset = 20

  // X dimension
  const xLabel = createDimensionLabel(formatDimension(x), 'X')
  xLabel.position.set(0, offset, y / 2 + offset)
  scene.add(xLabel)
  dimensionLabels.push(xLabel)

  // Y dimension
  const yLabel = createDimensionLabel(formatDimension(y), 'Y')
  yLabel.position.set(x / 2 + offset, offset, 0)
  scene.add(yLabel)
  dimensionLabels.push(yLabel)

  // Z dimension
  const zLabel = createDimensionLabel(formatDimension(z), 'Z')
  zLabel.position.set(x / 2 + offset, z / 2, y / 2 + offset)
  scene.add(zLabel)
  dimensionLabels.push(zLabel)
}

function createDimensionLabel(text: string, axis: string): CSS2DObject {
  const div = document.createElement('div')
  div.className = 'dimension-label'
  // Cyber dark theme styling
  const axisColors: Record<string, string> = {
    X: '#ef4444', // Red
    Y: '#22c55e', // Green  
    Z: '#3b82f6', // Blue
  }
  div.style.cssText = `
    background: rgba(13, 21, 38, 0.9);
    border: 1px solid ${axisColors[axis] || '#06b6d4'}40;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    color: ${axisColors[axis] || '#06b6d4'};
    box-shadow: 0 0 10px ${axisColors[axis] || '#06b6d4'}30;
    backdrop-filter: blur(4px);
  `
  div.textContent = `${axis}: ${text}`
  return new CSS2DObject(div)
}

function resetView() {
  fitCameraToObject()
}

function toggleUnit() {
  settingsStore.setUnit(displayUnit.value === 'mm' ? 'cm' : 'mm')
}

// ========== EDITOR FUNCTIONS ==========

function toggleEditor() {
  editorEnabled.value = !editorEnabled.value
  if (editorEnabled.value) {
    initTransformControls()
    currentTool.value = 'select'
  } else {
    if (transformControls) {
      transformControls.detach()
    }
    selectedShapeId.value = null
  }
}

function initTransformControls() {
  if (transformControls) return
  
  transformControls = new TransformControls(camera, renderer.domElement)
  transformControls.addEventListener('dragging-changed', (event: any) => {
    controls.enabled = !event.value
  })
  transformControls.addEventListener('change', () => {
    updateSelectedShapeParams()
  })
  scene.add(transformControls)
}

function setTool(tool: typeof currentTool.value) {
  currentTool.value = tool
  
  if (transformControls && selectedShapeId.value) {
    const shape = editorShapes.value.find(s => s.id === selectedShapeId.value)
    if (shape) {
      if (tool === 'move') {
        transformControls.setMode('translate')
        transformControls.attach(shape.mesh)
      } else if (tool === 'rotate') {
        transformControls.setMode('rotate')
        transformControls.attach(shape.mesh)
      } else if (tool === 'scale') {
        transformControls.setMode('scale')
        transformControls.attach(shape.mesh)
      } else if (tool === 'select') {
        transformControls.setMode('translate')
      }
    }
  }
}

function addEditorShape(type: EditorShape['type']) {
  const id = crypto.randomUUID()
  let geometry: THREE.BufferGeometry
  let params: Record<string, number>
  
  switch (type) {
    case 'box':
      params = { width: 30, height: 30, depth: 30 }
      geometry = new THREE.BoxGeometry(params.width, params.height, params.depth)
      break
    case 'cylinder':
      params = { radius: 15, height: 40, segments: 32 }
      geometry = new THREE.CylinderGeometry(params.radius, params.radius, params.height, params.segments)
      break
    case 'sphere':
      params = { radius: 20, segments: 32 }
      geometry = new THREE.SphereGeometry(params.radius, params.segments, params.segments)
      break
    case 'cone':
      params = { radius: 15, height: 40, segments: 32 }
      geometry = new THREE.ConeGeometry(params.radius, params.height, params.segments)
      break
    default:
      return
  }
  
  const material = new THREE.MeshPhongMaterial({
    color: 0x22d3ee,
    specular: 0x06b6d4,
    shininess: 60,
    transparent: true,
    opacity: 0.9,
  })
  
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.y = type === 'box' ? params.height / 2 : 
                    type === 'cylinder' ? params.height / 2 :
                    type === 'sphere' ? params.radius :
                    type === 'cone' ? params.height / 2 : 20
  mesh.userData.editorShapeId = id
  
  scene.add(mesh)
  
  const shape: EditorShape = {
    id,
    type,
    mesh,
    params,
    position: { x: mesh.position.x, y: mesh.position.y, z: mesh.position.z },
    rotation: { x: 0, y: 0, z: 0 },
  }
  
  editorShapes.value.push(shape)
  selectShape(id)
  currentTool.value = 'select'
}

function selectShape(id: string | null) {
  selectedShapeId.value = id
  
  // Reset all materials
  editorShapes.value.forEach(s => {
    (s.mesh.material as THREE.MeshPhongMaterial).emissive.setHex(0x000000)
  })
  
  if (id) {
    const shape = editorShapes.value.find(s => s.id === id)
    if (shape && transformControls) {
      (shape.mesh.material as THREE.MeshPhongMaterial).emissive.setHex(0x06b6d4)
      ;(shape.mesh.material as THREE.MeshPhongMaterial).emissiveIntensity = 0.3
      transformControls.attach(shape.mesh)
      showShapePanel.value = true
    }
  } else {
    transformControls?.detach()
    showShapePanel.value = false
  }
}

function updateSelectedShapeParams() {
  if (!selectedShapeId.value) return
  const shape = editorShapes.value.find(s => s.id === selectedShapeId.value)
  if (shape) {
    shape.position = {
      x: Math.round(shape.mesh.position.x * 10) / 10,
      y: Math.round(shape.mesh.position.y * 10) / 10,
      z: Math.round(shape.mesh.position.z * 10) / 10,
    }
    shape.rotation = {
      x: Math.round(THREE.MathUtils.radToDeg(shape.mesh.rotation.x)),
      y: Math.round(THREE.MathUtils.radToDeg(shape.mesh.rotation.y)),
      z: Math.round(THREE.MathUtils.radToDeg(shape.mesh.rotation.z)),
    }
  }
}

function updateShapeGeometry() {
  if (!selectedShapeId.value) return
  const shape = editorShapes.value.find(s => s.id === selectedShapeId.value)
  if (!shape) return
  
  shape.mesh.geometry.dispose()
  
  switch (shape.type) {
    case 'box':
      shape.mesh.geometry = new THREE.BoxGeometry(
        shape.params.width, shape.params.height, shape.params.depth
      )
      break
    case 'cylinder':
      shape.mesh.geometry = new THREE.CylinderGeometry(
        shape.params.radius, shape.params.radius, shape.params.height, 32
      )
      break
    case 'sphere':
      shape.mesh.geometry = new THREE.SphereGeometry(shape.params.radius, 32, 32)
      break
    case 'cone':
      shape.mesh.geometry = new THREE.ConeGeometry(
        shape.params.radius, shape.params.height, 32
      )
      break
  }
}

function deleteSelectedShape() {
  if (!selectedShapeId.value) return
  const index = editorShapes.value.findIndex(s => s.id === selectedShapeId.value)
  if (index !== -1) {
    const shape = editorShapes.value[index]
    scene.remove(shape.mesh)
    shape.mesh.geometry.dispose()
    ;(shape.mesh.material as THREE.Material).dispose()
    editorShapes.value.splice(index, 1)
    selectShape(null)
  }
}

function duplicateSelectedShape() {
  if (!selectedShapeId.value) return
  const shape = editorShapes.value.find(s => s.id === selectedShapeId.value)
  if (!shape) return
  
  addEditorShape(shape.type)
  const newShape = editorShapes.value[editorShapes.value.length - 1]
  
  // Copy params
  newShape.params = { ...shape.params }
  updateShapeGeometry()
  
  // Offset position
  newShape.mesh.position.copy(shape.mesh.position)
  newShape.mesh.position.x += 20
  newShape.mesh.rotation.copy(shape.mesh.rotation)
  updateSelectedShapeParams()
}

function onViewerClick(event: MouseEvent) {
  if (!editorEnabled.value) return
  if (!container.value) return
  
  const rect = container.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  
  raycaster.setFromCamera(mouse, camera)
  
  // Check for shape intersection
  const editorMeshes = editorShapes.value.map(s => s.mesh)
  const intersects = raycaster.intersectObjects(editorMeshes)
  
  if (intersects.length > 0) {
    const clickedMesh = intersects[0].object as THREE.Mesh
    const shapeId = clickedMesh.userData.editorShapeId
    if (shapeId) {
      selectShape(shapeId)
    }
  } else if (currentTool.value === 'select') {
    selectShape(null)
  }
}

function generateCodeFromShapes() {
  if (editorShapes.value.length === 0) return
  
  let code = 'import cadquery as cq\n\n'
  code += '# Paramètres générés depuis l\'éditeur visuel\n\n'
  
  editorShapes.value.forEach((shape, i) => {
    const prefix = editorShapes.value.length > 1 ? `shape${i + 1}_` : ''
    
    // Add parameters
    Object.entries(shape.params).forEach(([key, value]) => {
      if (key !== 'segments') {
        code += `${prefix}${key} = ${value}\n`
      }
    })
    code += '\n'
  })
  
  // Generate shapes
  editorShapes.value.forEach((shape, i) => {
    const prefix = editorShapes.value.length > 1 ? `shape${i + 1}_` : ''
    const varName = editorShapes.value.length > 1 ? `shape${i + 1}` : 'result'
    
    code += `${varName} = (\n    cq.Workplane("XY")\n`
    
    switch (shape.type) {
      case 'box':
        code += `    .box(${prefix}width, ${prefix}depth, ${prefix}height)\n`
        break
      case 'cylinder':
        code += `    .cylinder(${prefix}height, ${prefix}radius)\n`
        break
      case 'sphere':
        code += `    .sphere(${prefix}radius)\n`
        break
      case 'cone':
        code += `    .cone(${prefix}radius, 0, ${prefix}height)\n`
        break
    }
    
    if (shape.position.x !== 0 || shape.position.z !== 0) {
      code += `    .translate((${shape.position.x}, ${shape.position.z}, 0))\n`
    }
    
    code += ')\n\n'
  })
  
  // Combine if multiple
  if (editorShapes.value.length > 1) {
    code += '# Assemblage\n'
    code += 'result = shape1'
    for (let i = 2; i <= editorShapes.value.length; i++) {
      code += `.union(shape${i})`
    }
    code += '\n'
  }
  
  emit('generate-code', code)
}

const selectedShape = computed(() => {
  if (!selectedShapeId.value) return null
  return editorShapes.value.find(s => s.id === selectedShapeId.value) || null
})

onMounted(() => {
  initScene()
  if (props.partId) {
    loadSTL(props.partId)
  }
  updateBuildVolume()
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  renderer?.dispose()
})

watch(() => props.partId, (newId: string | null, oldId: string | null) => {
  console.log('ThreeViewer: partId changed from', oldId, 'to', newId)
  
  // Increment load ID to cancel any pending loads
  currentLoadId++
  
  // Clear existing mesh when part changes or becomes null
  clearCurrentMesh()
  
  if (newId) {
    loadSTL(newId)
  }
}, { immediate: false })

watch(() => props.boundingBox, (newBox: BoundingBox | null | undefined, oldBox: BoundingBox | null | undefined) => {
  updateDimensionLabels()
  // Reload STL if bounding box changed (means the model was regenerated)
  if (props.partId && newBox) {
    // Reload if we got a new bounding box (from null) or if dimensions changed
    const shouldReload = !oldBox || 
      newBox.x !== oldBox.x || 
      newBox.y !== oldBox.y || 
      newBox.z !== oldBox.z
    if (shouldReload) {
      console.log('ThreeViewer: boundingBox changed, reloading STL')
      loadSTL(props.partId)
    }
  }
}, { deep: true })

// Watch updateKey to force reload when part is regenerated (even if dimensions don't change)
watch(() => props.updateKey, (newKey: string | undefined, oldKey: string | undefined) => {
  if (props.partId && newKey && oldKey && newKey !== oldKey) {
    console.log('ThreeViewer: updateKey changed, reloading STL')
    loadSTL(props.partId)
  }
})

watch([() => props.showBuildVolume, () => props.buildVolume, () => props.fits], () => {
  updateBuildVolume()
}, { deep: true })

watch(displayUnit, () => {
  updateDimensionLabels()
})
</script>

<template>
  <div class="relative w-full h-full bg-dark-900 rounded-xl overflow-hidden">
    <!-- Editor Toolbar -->
    <div class="absolute left-3 top-3 z-20 flex flex-col gap-1">
      <!-- Toggle Editor -->
      <button
        @click="toggleEditor"
        :class="[
          'w-10 h-10 rounded-lg flex items-center justify-center transition-all',
          editorEnabled
            ? 'bg-accent-500 text-white shadow-accent'
            : 'glass cyber-border text-slate-400 hover:text-white hover:border-cyber-400/50'
        ]"
        title="Mode édition"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
        </svg>
      </button>
      
      <!-- Editor Tools (shown when editor is enabled) -->
      <div v-if="editorEnabled" class="flex flex-col gap-1 mt-2 p-1 glass rounded-lg border border-white/10">
        <!-- Select -->
        <button
          @click="setTool('select')"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'select' ? 'bg-cyber-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10']"
          title="Sélectionner"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
        </button>
        
        <!-- Separator -->
        <div class="h-px bg-white/10 my-1"></div>
        
        <!-- Add Box -->
        <button
          @click="addEditorShape('box')"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'box' ? 'bg-primary-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10']"
          title="Ajouter boîte"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </button>
        
        <!-- Add Cylinder -->
        <button
          @click="addEditorShape('cylinder')"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'cylinder' ? 'bg-primary-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10']"
          title="Ajouter cylindre"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <ellipse cx="12" cy="5" rx="7" ry="2.5" stroke-width="2"/>
            <path d="M5 5v14c0 1.38 3.13 2.5 7 2.5s7-1.12 7-2.5V5" stroke-width="2"/>
          </svg>
        </button>
        
        <!-- Add Sphere -->
        <button
          @click="addEditorShape('sphere')"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'sphere' ? 'bg-primary-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10']"
          title="Ajouter sphère"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="8" stroke-width="2"/>
            <ellipse cx="12" cy="12" rx="8" ry="3" stroke-width="1.5"/>
          </svg>
        </button>
        
        <!-- Add Cone -->
        <button
          @click="addEditorShape('cone')"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'cone' ? 'bg-primary-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10']"
          title="Ajouter cône"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 3L4 19h16L12 3z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        
        <!-- Separator -->
        <div class="h-px bg-white/10 my-1"></div>
        
        <!-- Move -->
        <button
          @click="setTool('move')"
          :disabled="!selectedShapeId"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'move' ? 'bg-cyber-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed']"
          title="Déplacer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
          </svg>
        </button>
        
        <!-- Rotate -->
        <button
          @click="setTool('rotate')"
          :disabled="!selectedShapeId"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'rotate' ? 'bg-cyber-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed']"
          title="Rotation"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
        
        <!-- Scale -->
        <button
          @click="setTool('scale')"
          :disabled="!selectedShapeId"
          :class="['w-8 h-8 rounded flex items-center justify-center transition-all', currentTool === 'scale' ? 'bg-cyber-500 text-white' : 'text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed']"
          title="Échelle"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        
        <!-- Separator -->
        <div class="h-px bg-white/10 my-1"></div>
        
        <!-- Delete -->
        <button
          @click="deleteSelectedShape"
          :disabled="!selectedShapeId"
          class="w-8 h-8 rounded flex items-center justify-center text-red-400 hover:text-red-300 hover:bg-red-500/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          title="Supprimer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
        
        <!-- Duplicate -->
        <button
          @click="duplicateSelectedShape"
          :disabled="!selectedShapeId"
          class="w-8 h-8 rounded flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          title="Dupliquer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      </div>
      
      <!-- Generate Code Button -->
      <button
        v-if="editorEnabled && editorShapes.length > 0"
        @click="generateCodeFromShapes"
        class="mt-2 w-10 h-10 rounded-lg bg-gradient-to-br from-cyber-500 to-accent-500 text-white flex items-center justify-center shadow-cyber hover:from-cyber-400 hover:to-accent-400 transition-all"
        title="Générer le code"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      </button>
    </div>
    
    <!-- Shape Properties Panel -->
    <div
      v-if="editorEnabled && selectedShape && showShapePanel"
      class="absolute right-3 top-3 w-56 glass rounded-xl border border-white/10 overflow-hidden z-20"
    >
      <div class="px-3 py-2 border-b border-white/10 bg-dark-800/50 flex items-center justify-between">
        <span class="text-sm font-medium text-white capitalize">{{ selectedShape.type }}</span>
        <button @click="showShapePanel = false" class="text-slate-400 hover:text-white">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="p-3 space-y-3">
        <!-- Dimensions -->
        <div>
          <label class="text-xs text-slate-400 mb-1 block">Dimensions</label>
          <div class="grid grid-cols-2 gap-2">
            <div v-for="(value, key) in selectedShape.params" :key="key" class="space-y-0.5">
              <label v-if="key !== 'segments'" class="text-[10px] text-slate-500 capitalize">{{ key }}</label>
              <input
                v-if="key !== 'segments'"
                v-model.number="selectedShape.params[key]"
                @change="updateShapeGeometry"
                type="number"
                class="w-full px-2 py-1 text-xs bg-dark-800 border border-white/10 rounded text-white"
              />
            </div>
          </div>
        </div>
        
        <!-- Position -->
        <div>
          <label class="text-xs text-slate-400 mb-1 block">Position</label>
          <div class="grid grid-cols-3 gap-1">
            <div class="text-center">
              <label class="text-[10px] text-red-400">X</label>
              <div class="text-xs text-white bg-dark-800 rounded px-1 py-0.5">{{ selectedShape.position.x }}</div>
            </div>
            <div class="text-center">
              <label class="text-[10px] text-green-400">Y</label>
              <div class="text-xs text-white bg-dark-800 rounded px-1 py-0.5">{{ selectedShape.position.y }}</div>
            </div>
            <div class="text-center">
              <label class="text-[10px] text-blue-400">Z</label>
              <div class="text-xs text-white bg-dark-800 rounded px-1 py-0.5">{{ selectedShape.position.z }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div ref="container" class="w-full h-full" @click="onViewerClick"></div>
    
    <!-- No model placeholder (only when not in editor mode) -->
    <div v-if="!partId && !loading && !error && !editorEnabled && editorShapes.length === 0" class="absolute inset-0 bg-dark-900 flex items-center justify-center pointer-events-none">
      <div class="text-center">
        <div class="w-20 h-20 mx-auto mb-4 rounded-2xl glass cyber-border flex items-center justify-center animate-pulse-cyber">
          <svg class="w-10 h-10 text-cyber-400/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <p class="text-slate-500">Cliquez sur ✏️ pour dessiner ou générez du code</p>
      </div>
    </div>
    
    <!-- Loading overlay -->
    <div v-if="loading" class="absolute inset-0 bg-dark-900/90 backdrop-blur-sm flex items-center justify-center">
      <div class="text-center">
        <div class="w-12 h-12 rounded-xl glass cyber-border flex items-center justify-center mb-3 animate-pulse-cyber">
          <svg class="w-6 h-6 text-cyber-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
        </div>
        <p class="text-slate-400 text-sm">Chargement du modèle...</p>
      </div>
    </div>

    <!-- Error overlay -->
    <div v-if="error" class="absolute inset-0 bg-dark-900/90 backdrop-blur-sm flex items-center justify-center">
      <div class="text-center glass rounded-xl p-6 border border-red-500/30">
        <svg class="w-12 h-12 mx-auto mb-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="text-red-400 text-sm">{{ error }}</p>
      </div>
    </div>

    <!-- Controls -->
    <div class="absolute bottom-4 right-4 flex gap-2">
      <button
        @click="toggleUnit"
        class="glass cyber-border px-3 py-2 rounded-lg text-sm font-medium text-cyber-400 hover:text-cyber-300 hover:border-cyber-400/50 transition-all"
      >
        {{ displayUnit }}
      </button>
      <button
        @click="resetView"
        class="glass cyber-border p-2 rounded-lg text-cyber-400 hover:text-cyber-300 hover:border-cyber-400/50 transition-all"
        title="Réinitialiser la vue"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </div>

    <!-- Dimensions display -->
    <div v-if="boundingBox" class="absolute top-4 right-4 glass cyber-border rounded-xl p-3">
      <div class="text-xs font-medium text-slate-400 mb-2">Dimensions</div>
      <div class="space-y-1.5 text-sm font-mono">
        <div class="flex justify-between gap-4">
          <span class="text-red-400">X:</span>
          <span class="text-slate-300">{{ formatDimension(boundingBox.x) }}</span>
        </div>
        <div class="flex justify-between gap-4">
          <span class="text-green-400">Y:</span>
          <span class="text-slate-300">{{ formatDimension(boundingBox.y) }}</span>
        </div>
        <div class="flex justify-between gap-4">
          <span class="text-blue-400">Z:</span>
          <span class="text-slate-300">{{ formatDimension(boundingBox.z) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
