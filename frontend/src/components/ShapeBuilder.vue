<script setup lang="ts">
import { ref, computed } from 'vue'

interface Shape {
  id: string
  type: 'box' | 'cylinder' | 'sphere' | 'polygon' | 'sketch'
  params: Record<string, number>
  operations: Operation[]
  position: { x: number; y: number; z: number }
}

interface Operation {
  type: 'fillet' | 'chamfer' | 'shell' | 'hole'
  params: Record<string, number | string>
}

const emit = defineEmits<{
  'generate-code': [code: string]
  close: []
}>()

// Shape list
const shapes = ref<Shape[]>([])
const selectedShapeId = ref<string | null>(null)

// New shape form
const newShapeType = ref<Shape['type']>('box')
const showAddShape = ref(false)

// Shape parameters by type
const shapeParams: Record<Shape['type'], { name: string; label: string; default: number; unit: string }[]> = {
  box: [
    { name: 'length', label: 'Longueur', default: 50, unit: 'mm' },
    { name: 'width', label: 'Largeur', default: 30, unit: 'mm' },
    { name: 'height', label: 'Hauteur', default: 20, unit: 'mm' },
  ],
  cylinder: [
    { name: 'radius', label: 'Rayon', default: 25, unit: 'mm' },
    { name: 'height', label: 'Hauteur', default: 40, unit: 'mm' },
  ],
  sphere: [
    { name: 'radius', label: 'Rayon', default: 25, unit: 'mm' },
  ],
  polygon: [
    { name: 'sides', label: 'Côtés', default: 6, unit: '' },
    { name: 'radius', label: 'Rayon', default: 25, unit: 'mm' },
    { name: 'height', label: 'Hauteur', default: 20, unit: 'mm' },
  ],
  sketch: [
    { name: 'width', label: 'Largeur', default: 50, unit: 'mm' },
    { name: 'height', label: 'Hauteur', default: 30, unit: 'mm' },
    { name: 'extrude', label: 'Extrusion', default: 20, unit: 'mm' },
  ],
}

const selectedShape = computed(() => {
  if (!selectedShapeId.value) return null
  return shapes.value.find(s => s.id === selectedShapeId.value) || null
})

function addShape() {
  const params: Record<string, number> = {}
  shapeParams[newShapeType.value].forEach(p => {
    params[p.name] = p.default
  })
  
  const shape: Shape = {
    id: crypto.randomUUID(),
    type: newShapeType.value,
    params,
    operations: [],
    position: { x: 0, y: 0, z: 0 },
  }
  
  shapes.value.push(shape)
  selectedShapeId.value = shape.id
  showAddShape.value = false
}

function removeShape(id: string) {
  shapes.value = shapes.value.filter(s => s.id !== id)
  if (selectedShapeId.value === id) {
    selectedShapeId.value = shapes.value[0]?.id || null
  }
}

function addOperation(type: Operation['type']) {
  if (!selectedShape.value) return
  
  const params: Record<string, number | string> = {}
  
  switch (type) {
    case 'fillet':
      params.radius = 2
      params.edges = '>Z or <Z'
      break
    case 'chamfer':
      params.distance = 2
      params.edges = '>Z'
      break
    case 'shell':
      params.thickness = 2
      params.face = '>Z'
      break
    case 'hole':
      params.diameter = 10
      params.depth = 0 // 0 = through
      break
  }
  
  selectedShape.value.operations.push({ type, params })
}

function removeOperation(index: number) {
  if (!selectedShape.value) return
  selectedShape.value.operations.splice(index, 1)
}

function generateCode() {
  if (shapes.value.length === 0) return
  
  let code = 'import cadquery as cq\n\n'
  
  // Generate parameters
  const allParams: string[] = []
  shapes.value.forEach((shape, i) => {
    const prefix = shapes.value.length > 1 ? `shape${i + 1}_` : ''
    Object.entries(shape.params).forEach(([key, value]) => {
      const paramName = `${prefix}${key}`
      allParams.push(`${paramName} = ${value}`)
    })
  })
  
  code += '# Paramètres\n'
  code += allParams.join('\n') + '\n\n'
  
  // Generate shape code
  shapes.value.forEach((shape, i) => {
    const prefix = shapes.value.length > 1 ? `shape${i + 1}_` : ''
    const varName = shapes.value.length > 1 ? `shape${i + 1}` : 'result'
    
    code += `# ${getShapeLabel(shape.type)}\n`
    code += `${varName} = (\n    cq.Workplane("XY")\n`
    
    // Base shape
    switch (shape.type) {
      case 'box':
        code += `    .box(${prefix}length, ${prefix}width, ${prefix}height)\n`
        break
      case 'cylinder':
        code += `    .cylinder(${prefix}height, ${prefix}radius)\n`
        break
      case 'sphere':
        code += `    .sphere(${prefix}radius)\n`
        break
      case 'polygon':
        code += `    .polygon(int(${prefix}sides), ${prefix}radius)\n`
        code += `    .extrude(${prefix}height)\n`
        break
      case 'sketch':
        code += `    .rect(${prefix}width, ${prefix}height)\n`
        code += `    .extrude(${prefix}extrude)\n`
        break
    }
    
    // Operations
    shape.operations.forEach(op => {
      switch (op.type) {
        case 'fillet':
          code += `    .edges("${op.params.edges}").fillet(${op.params.radius})\n`
          break
        case 'chamfer':
          code += `    .edges("${op.params.edges}").chamfer(${op.params.distance})\n`
          break
        case 'shell':
          code += `    .faces("${op.params.face}").shell(-${op.params.thickness})\n`
          break
        case 'hole':
          if (op.params.depth === 0) {
            code += `    .faces(">Z").workplane().hole(${op.params.diameter})\n`
          } else {
            code += `    .faces(">Z").workplane().hole(${op.params.diameter}, ${op.params.depth})\n`
          }
          break
      }
    })
    
    // Position offset
    if (shape.position.x !== 0 || shape.position.y !== 0 || shape.position.z !== 0) {
      code += `    .translate((${shape.position.x}, ${shape.position.y}, ${shape.position.z}))\n`
    }
    
    code += ')\n\n'
  })
  
  // Combine shapes if multiple
  if (shapes.value.length > 1) {
    code += '# Assemblage\n'
    code += 'result = shape1'
    for (let i = 2; i <= shapes.value.length; i++) {
      code += `.union(shape${i})`
    }
    code += '\n'
  }
  
  emit('generate-code', code)
}

function getShapeLabel(type: Shape['type']): string {
  const labels: Record<Shape['type'], string> = {
    box: 'Boîte',
    cylinder: 'Cylindre',
    sphere: 'Sphère',
    polygon: 'Polygone',
    sketch: 'Esquisse',
  }
  return labels[type]
}

function getOperationLabel(type: Operation['type']): string {
  const labels: Record<Operation['type'], string> = {
    fillet: 'Congé',
    chamfer: 'Chanfrein',
    shell: 'Coque',
    hole: 'Perçage',
  }
  return labels[type]
}

const edgeOptions = [
  { value: '>Z', label: 'Arêtes du haut' },
  { value: '<Z', label: 'Arêtes du bas' },
  { value: '>Z or <Z', label: 'Arêtes haut et bas' },
  { value: '|Z', label: 'Arêtes verticales' },
  { value: '>X', label: 'Arêtes face droite' },
  { value: '<X', label: 'Arêtes face gauche' },
]

const faceOptions = [
  { value: '>Z', label: 'Face du haut' },
  { value: '<Z', label: 'Face du bas' },
  { value: '>X', label: 'Face droite' },
  { value: '<X', label: 'Face gauche' },
  { value: '>Y', label: 'Face avant' },
  { value: '<Y', label: 'Face arrière' },
]
</script>

<template>
  <div class="h-full flex flex-col bg-dark-900">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-dark-850">
      <h3 class="text-lg font-semibold text-white flex items-center gap-2">
        <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        Créateur de Formes
      </h3>
      <button @click="$emit('close')" class="text-slate-400 hover:text-white">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Panel - Shape List -->
      <div class="w-56 border-r border-white/5 flex flex-col">
        <div class="p-3 border-b border-white/5">
          <button
            @click="showAddShape = true"
            class="w-full px-3 py-2 bg-gradient-to-r from-accent-600 to-primary-600 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:from-accent-500 hover:to-primary-500 transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Ajouter forme
          </button>
        </div>
        
        <!-- Shape list -->
        <div class="flex-1 overflow-y-auto p-2">
          <div v-if="shapes.length === 0" class="text-center py-8 text-slate-500 text-sm">
            Aucune forme
          </div>
          
          <div
            v-for="(shape, index) in shapes"
            :key="shape.id"
            @click="selectedShapeId = shape.id"
            :class="[
              'p-3 rounded-lg mb-2 cursor-pointer transition-all border',
              selectedShapeId === shape.id
                ? 'bg-accent-500/10 border-accent-500/30'
                : 'bg-white/5 border-transparent hover:border-white/10'
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-slate-500">{{ index + 1 }}</span>
                <span class="text-white text-sm">{{ getShapeLabel(shape.type) }}</span>
              </div>
              <button
                @click.stop="removeShape(shape.id)"
                class="text-slate-500 hover:text-red-400 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div v-if="shape.operations.length > 0" class="mt-2 flex flex-wrap gap-1">
              <span
                v-for="op in shape.operations"
                :key="op.type"
                class="text-xs px-1.5 py-0.5 bg-white/10 rounded text-slate-400"
              >
                {{ getOperationLabel(op.type) }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Right Panel - Shape Editor -->
      <div class="flex-1 overflow-y-auto p-4">
        <div v-if="!selectedShape" class="h-full flex items-center justify-center text-slate-500">
          <div class="text-center">
            <svg class="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <p>Sélectionnez ou ajoutez une forme</p>
          </div>
        </div>
        
        <div v-else class="space-y-6">
          <!-- Shape Parameters -->
          <div>
            <h4 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              Dimensions
            </h4>
            <div class="grid grid-cols-2 gap-3">
              <div
                v-for="param in shapeParams[selectedShape.type]"
                :key="param.name"
                class="space-y-1"
              >
                <label class="text-xs text-slate-400">{{ param.label }}</label>
                <div class="flex">
                  <input
                    v-model.number="selectedShape.params[param.name]"
                    type="number"
                    class="flex-1 px-3 py-2 bg-dark-800 border border-white/10 rounded-l-lg text-white text-sm focus:border-accent-500 focus:outline-none"
                  />
                  <span v-if="param.unit" class="px-3 py-2 bg-dark-700 border border-l-0 border-white/10 rounded-r-lg text-slate-500 text-sm">
                    {{ param.unit }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Position -->
          <div>
            <h4 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              Position
            </h4>
            <div class="grid grid-cols-3 gap-3">
              <div class="space-y-1">
                <label class="text-xs text-slate-400">X</label>
                <input
                  v-model.number="selectedShape.position.x"
                  type="number"
                  class="w-full px-3 py-2 bg-dark-800 border border-white/10 rounded-lg text-white text-sm focus:border-accent-500 focus:outline-none"
                />
              </div>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">Y</label>
                <input
                  v-model.number="selectedShape.position.y"
                  type="number"
                  class="w-full px-3 py-2 bg-dark-800 border border-white/10 rounded-lg text-white text-sm focus:border-accent-500 focus:outline-none"
                />
              </div>
              <div class="space-y-1">
                <label class="text-xs text-slate-400">Z</label>
                <input
                  v-model.number="selectedShape.position.z"
                  type="number"
                  class="w-full px-3 py-2 bg-dark-800 border border-white/10 rounded-lg text-white text-sm focus:border-accent-500 focus:outline-none"
                />
              </div>
            </div>
          </div>
          
          <!-- Operations -->
          <div>
            <h4 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
              Opérations
            </h4>
            
            <!-- Add operation buttons -->
            <div class="flex flex-wrap gap-2 mb-4">
              <button
                @click="addOperation('fillet')"
                class="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-slate-300 transition-colors"
              >
                + Congé
              </button>
              <button
                @click="addOperation('chamfer')"
                class="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-slate-300 transition-colors"
              >
                + Chanfrein
              </button>
              <button
                @click="addOperation('shell')"
                class="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-slate-300 transition-colors"
              >
                + Coque
              </button>
              <button
                @click="addOperation('hole')"
                class="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-slate-300 transition-colors"
              >
                + Perçage
              </button>
            </div>
            
            <!-- Operations list -->
            <div class="space-y-3">
              <div
                v-for="(op, index) in selectedShape.operations"
                :key="index"
                class="p-3 bg-dark-800 rounded-lg border border-white/5"
              >
                <div class="flex items-center justify-between mb-3">
                  <span class="text-sm font-medium text-white">{{ getOperationLabel(op.type) }}</span>
                  <button
                    @click="removeOperation(index)"
                    class="text-slate-500 hover:text-red-400 transition-colors"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <!-- Fillet params -->
                <div v-if="op.type === 'fillet'" class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Rayon</label>
                    <input
                      v-model.number="op.params.radius"
                      type="number"
                      step="0.5"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Arêtes</label>
                    <select
                      v-model="op.params.edges"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    >
                      <option v-for="opt in edgeOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>
                </div>
                
                <!-- Chamfer params -->
                <div v-if="op.type === 'chamfer'" class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Distance</label>
                    <input
                      v-model.number="op.params.distance"
                      type="number"
                      step="0.5"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Arêtes</label>
                    <select
                      v-model="op.params.edges"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    >
                      <option v-for="opt in edgeOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>
                </div>
                
                <!-- Shell params -->
                <div v-if="op.type === 'shell'" class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Épaisseur</label>
                    <input
                      v-model.number="op.params.thickness"
                      type="number"
                      step="0.5"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Face ouverte</label>
                    <select
                      v-model="op.params.face"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    >
                      <option v-for="opt in faceOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>
                </div>
                
                <!-- Hole params -->
                <div v-if="op.type === 'hole'" class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Diamètre</label>
                    <input
                      v-model.number="op.params.diameter"
                      type="number"
                      step="0.5"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs text-slate-400">Profondeur (0=traversant)</label>
                    <input
                      v-model.number="op.params.depth"
                      type="number"
                      step="1"
                      class="w-full px-3 py-2 bg-dark-700 border border-white/10 rounded-lg text-white text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Footer -->
    <div class="px-4 py-3 border-t border-white/5 bg-dark-850 flex justify-between">
      <button
        @click="$emit('close')"
        class="px-4 py-2 text-slate-400 hover:text-white transition-colors"
      >
        Annuler
      </button>
      <button
        @click="generateCode"
        :disabled="shapes.length === 0"
        class="px-6 py-2 bg-gradient-to-r from-cyber-600 to-primary-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:from-cyber-500 hover:to-primary-500 transition-all flex items-center gap-2"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        Générer le code
      </button>
    </div>
    
    <!-- Add Shape Modal -->
    <Teleport to="body">
      <div v-if="showAddShape" class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
        <div class="glass rounded-2xl w-full max-w-md mx-4 overflow-hidden shadow-cyber-lg" @click.stop>
          <div class="px-6 py-4 border-b border-white/5">
            <h3 class="text-lg font-semibold text-white">Ajouter une forme</h3>
          </div>
          
          <div class="p-6">
            <div class="grid grid-cols-2 gap-3">
              <button
                v-for="type in (['box', 'cylinder', 'sphere', 'polygon', 'sketch'] as const)"
                :key="type"
                @click="newShapeType = type"
                :class="[
                  'p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2',
                  newShapeType === type
                    ? 'border-accent-500 bg-accent-500/10'
                    : 'border-white/10 hover:border-white/20 bg-white/5'
                ]"
              >
                <div class="w-12 h-12 rounded-lg bg-white/10 flex items-center justify-center">
                  <!-- Box icon -->
                  <svg v-if="type === 'box'" class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <!-- Cylinder icon -->
                  <svg v-else-if="type === 'cylinder'" class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <ellipse cx="12" cy="6" rx="8" ry="3" stroke-width="2"/>
                    <path d="M4 6v12c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke-width="2"/>
                  </svg>
                  <!-- Sphere icon -->
                  <svg v-else-if="type === 'sphere'" class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="9" stroke-width="2"/>
                    <ellipse cx="12" cy="12" rx="9" ry="4" stroke-width="1.5"/>
                  </svg>
                  <!-- Polygon icon -->
                  <svg v-else-if="type === 'polygon'" class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5" stroke-width="2"/>
                  </svg>
                  <!-- Sketch icon -->
                  <svg v-else class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                  </svg>
                </div>
                <span class="text-sm text-white">{{ getShapeLabel(type) }}</span>
              </button>
            </div>
          </div>
          
          <div class="px-6 py-4 border-t border-white/5 flex gap-3">
            <button
              @click="showAddShape = false"
              class="flex-1 px-4 py-2 glass cyber-border text-slate-300 rounded-xl"
            >
              Annuler
            </button>
            <button
              @click="addShape"
              class="flex-1 px-4 py-2 bg-gradient-to-r from-accent-600 to-primary-600 text-white rounded-xl"
            >
              Ajouter
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
