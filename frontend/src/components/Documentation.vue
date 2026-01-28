<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const activeSection = ref('getting-started')
const showMobileMenu = ref(false)

const sections = [
  { id: 'getting-started', title: 'Démarrage', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { id: 'concepts', title: 'Concepts', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { id: 'ai-composer', title: 'Compositeur IA', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { id: 'code-editor', title: 'Éditeur de code', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
  { id: 'parameters', title: 'Paramètres', icon: 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4' },
  { id: 'assembly', title: 'Mode assemblage', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
  { id: 'export', title: 'Export & Impression', icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4' },
  { id: 'cadquery', title: 'Guide CadQuery', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
  { id: 'tips', title: 'Astuces', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
]

// Handle scroll spy
function handleScroll() {
  const scrollPosition = window.scrollY + 100
  
  for (const section of sections) {
    const element = document.getElementById(section.id)
    if (element) {
      const offsetTop = element.offsetTop
      const offsetHeight = element.offsetHeight
      
      if (scrollPosition >= offsetTop && scrollPosition < offsetTop + offsetHeight) {
        activeSection.value = section.id
        break
      }
    }
  }
}

function scrollToSection(sectionId: string) {
  activeSection.value = sectionId
  showMobileMenu.value = false
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div class="min-h-screen bg-dark-950">
    <div class="flex">
      <!-- Sidebar Navigation -->
      <aside class="hidden lg:block w-64 fixed left-0 top-[57px] h-[calc(100vh-57px)] glass border-r border-white/5 overflow-y-auto">
        <nav class="p-4 space-y-1">
          <button
            v-for="section in sections"
            :key="section.id"
            @click="scrollToSection(section.id)"
            :class="[
              'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all text-left',
              activeSection === section.id
                ? 'bg-cyber-500/10 text-cyber-400 border border-cyber-500/30'
                : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
            ]"
          >
            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="section.icon" />
            </svg>
            <span>{{ section.title }}</span>
          </button>
        </nav>
        
        <!-- External links -->
        <div class="p-4 border-t border-white/5">
          <a 
            href="https://cadquery.readthedocs.io" 
            target="_blank"
            class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-slate-400 hover:text-cyber-400 hover:bg-white/5 transition-all"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            <span>CadQuery Docs</span>
          </a>
        </div>
      </aside>

      <!-- Mobile menu button -->
      <button
        @click="showMobileMenu = !showMobileMenu"
        class="lg:hidden fixed bottom-4 right-4 z-50 w-14 h-14 bg-gradient-to-r from-cyber-600 to-accent-600 rounded-xl shadow-cyber flex items-center justify-center text-white"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
        </svg>
      </button>

      <!-- Mobile menu -->
      <Teleport to="body">
        <div
          v-if="showMobileMenu"
          class="lg:hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
          @click="showMobileMenu = false"
        >
          <div class="absolute right-4 bottom-20 w-64 glass rounded-2xl p-2 shadow-cyber-lg" @click.stop>
            <button
              v-for="section in sections"
              :key="section.id"
              @click="scrollToSection(section.id)"
              :class="[
                'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all text-left',
                activeSection === section.id
                  ? 'bg-cyber-500/10 text-cyber-400'
                  : 'text-slate-300 hover:bg-white/5'
              ]"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="section.icon" />
              </svg>
              {{ section.title }}
            </button>
          </div>
        </div>
      </Teleport>

      <!-- Main Content -->
      <main class="flex-1 lg:ml-64 px-6 py-8 max-w-4xl mx-auto">
        <!-- Hero -->
        <div class="mb-12 text-center">
          <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyber-500/10 border border-cyber-500/30 text-cyber-400 text-sm mb-6">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Documentation
          </div>
          <h1 class="text-4xl font-bold text-white mb-4">
            Bienvenue sur <span class="text-gradient">VoxelMind AI</span>
          </h1>
          <p class="text-xl text-slate-400 max-w-2xl mx-auto">
            Créez des modèles 3D imprimables en décrivant simplement ce que vous voulez, ou codez directement en CadQuery.
          </p>
        </div>

        <!-- Getting Started -->
        <section id="getting-started" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Démarrage rapide</h2>
          </div>
          
          <div class="space-y-6">
            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">1. Créer un projet</h3>
              <p class="text-slate-400 mb-4">
                Depuis la page d'accueil, cliquez sur <span class="text-cyber-400 font-mono">"Nouveau"</span> pour créer un projet vide, 
                ou utilisez <span class="text-accent-400 font-mono">"Composer IA"</span> pour générer automatiquement plusieurs pièces.
              </p>
              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <p class="text-sm text-slate-300">
                  <strong class="text-white">Exemple IA:</strong> "Un support de téléphone avec une base de 80x100mm, un dossier incliné à 70° et une rainure pour le câble"
                </p>
              </div>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">2. Ajouter des pièces</h3>
              <p class="text-slate-400 mb-4">
                Dans un projet, utilisez l'onglet <span class="text-accent-400 font-mono">"IA Composer"</span> pour décrire une pièce, 
                ou écrivez directement du code CadQuery dans l'onglet <span class="text-cyber-400 font-mono">"Code"</span>.
              </p>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">3. Visualiser et ajuster</h3>
              <p class="text-slate-400 mb-4">
                Le panneau 3D affiche votre modèle en temps réel. Utilisez le panneau <span class="text-white">Paramètres</span> 
                pour modifier les dimensions sans toucher au code.
              </p>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">4. Exporter</h3>
              <p class="text-slate-400">
                Téléchargez en <span class="font-mono text-slate-300">STL</span> pour n'importe quel slicer, 
                ou en <span class="font-mono text-slate-300">3MF</span> pour une compatibilité directe avec Bambu Studio.
              </p>
            </div>
          </div>
        </section>

        <!-- Concepts -->
        <section id="concepts" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Concepts clés</h2>
          </div>

          <div class="grid md:grid-cols-2 gap-4">
            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-8 h-8 rounded-lg bg-cyber-500/20 flex items-center justify-center">
                  <svg class="w-4 h-4 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                </div>
                <h4 class="font-semibold text-white">Projet</h4>
              </div>
              <p class="text-sm text-slate-400">
                Un projet contient plusieurs pièces qui forment un ensemble. Par exemple: un boîtier avec couvercle.
              </p>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-8 h-8 rounded-lg bg-accent-500/20 flex items-center justify-center">
                  <svg class="w-4 h-4 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
                <h4 class="font-semibold text-white">Pièce (Part)</h4>
              </div>
              <p class="text-sm text-slate-400">
                Une pièce est un modèle 3D unique défini par du code CadQuery. Chaque pièce génère un fichier STL.
              </p>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
                  <svg class="w-4 h-4 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                  </svg>
                </div>
                <h4 class="font-semibold text-white">Section</h4>
              </div>
              <p class="text-sm text-slate-400">
                Organisez vos projets en sections (dossiers) pour mieux les retrouver. Couleurs personnalisables.
              </p>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                  </svg>
                </div>
                <h4 class="font-semibold text-white">Paramètre</h4>
              </div>
              <p class="text-sm text-slate-400">
                Variables du code (ex: <code class="text-cyber-300">width = 50</code>) ajustables via l'interface sans modifier le code.
              </p>
            </div>
          </div>
        </section>

        <!-- AI Composer -->
        <section id="ai-composer" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Compositeur IA</h2>
          </div>

          <div class="glass rounded-2xl p-6 border border-white/5 mb-6">
            <h3 class="text-lg font-semibold text-white mb-4">Comment bien décrire votre modèle</h3>
            
            <div class="space-y-4">
              <div class="flex gap-3">
                <div class="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p class="text-slate-300 font-medium">Soyez précis sur les dimensions</p>
                  <p class="text-sm text-slate-500">"Une boîte de 100x60x40mm" plutôt que "une petite boîte"</p>
                </div>
              </div>

              <div class="flex gap-3">
                <div class="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p class="text-slate-300 font-medium">Décrivez la géométrie</p>
                  <p class="text-sm text-slate-500">"Coins arrondis avec un rayon de 5mm", "Trou central de 10mm de diamètre"</p>
                </div>
              </div>

              <div class="flex gap-3">
                <div class="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p class="text-slate-300 font-medium">Indiquez l'usage</p>
                  <p class="text-sm text-slate-500">"Pour un iPhone 15", "Pour vis M4", "Épaisseur de paroi 2mm pour solidité"</p>
                </div>
              </div>
            </div>
          </div>

          <div class="glass rounded-2xl p-6 border border-white/5">
            <h3 class="text-lg font-semibold text-white mb-4">Exemples de prompts</h3>
            
            <div class="space-y-3">
              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <p class="text-slate-300 text-sm font-mono">
                  "Un boîtier rectangulaire de 80x50x30mm avec des coins arrondis (rayon 3mm), une épaisseur de paroi de 2mm, et un couvercle clipsable"
                </p>
              </div>
              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <p class="text-slate-300 text-sm font-mono">
                  "Un support de téléphone avec une base de 100x80mm, un dossier incliné à 65°, et une rainure de 15mm pour le câble de charge"
                </p>
              </div>
              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <p class="text-slate-300 text-sm font-mono">
                  "Une équerre de 50x50x50mm avec des trous de fixation de 5mm dans chaque branche et des renforts triangulaires"
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- Code Editor -->
        <section id="code-editor" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Éditeur de code</h2>
          </div>

          <div class="glass rounded-2xl p-6 border border-white/5 mb-6">
            <h3 class="text-lg font-semibold text-white mb-4">Structure du code</h3>
            <p class="text-slate-400 mb-4">
              Chaque pièce utilise CadQuery, une bibliothèque Python pour la CAO paramétrique. 
              Le code doit définir une variable <code class="text-cyber-300 font-mono">result</code> contenant le solide final.
            </p>

            <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm overflow-x-auto">
              <pre class="text-slate-300"><span class="text-slate-500"># Paramètres modifiables</span>
<span class="text-cyan-400">width</span> = <span class="text-amber-400">50</span>
<span class="text-cyan-400">height</span> = <span class="text-amber-400">30</span>
<span class="text-cyan-400">depth</span> = <span class="text-amber-400">20</span>
<span class="text-cyan-400">fillet_radius</span> = <span class="text-amber-400">3</span>

<span class="text-slate-500"># Construction du modèle</span>
<span class="text-cyan-400">result</span> = (
    cq.Workplane(<span class="text-green-400">"XY"</span>)
    .box(width, depth, height)
    .edges(<span class="text-green-400">"|Z"</span>)
    .fillet(fillet_radius)
)</pre>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-4">
            <div class="glass rounded-xl p-5 border border-white/5">
              <h4 class="font-semibold text-white mb-2">Raccourcis clavier</h4>
              <ul class="space-y-2 text-sm text-slate-400">
                <li><kbd class="px-2 py-1 bg-dark-700 rounded text-xs text-slate-300">Cmd+S</kbd> Sauvegarder et exécuter</li>
                <li><kbd class="px-2 py-1 bg-dark-700 rounded text-xs text-slate-300">Cmd+Z</kbd> Annuler</li>
                <li><kbd class="px-2 py-1 bg-dark-700 rounded text-xs text-slate-300">Cmd+/</kbd> Commenter la ligne</li>
              </ul>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <h4 class="font-semibold text-white mb-2">Mode édition IA</h4>
              <p class="text-sm text-slate-400">
                Activez "Modifier le design" dans l'onglet IA pour que l'assistant modifie 
                votre code existant au lieu de tout réécrire.
              </p>
            </div>
          </div>
        </section>

        <!-- Parameters -->
        <section id="parameters" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Panneau Paramètres</h2>
          </div>

          <div class="glass rounded-2xl p-6 border border-white/5">
            <p class="text-slate-400 mb-4">
              Le panneau paramètres détecte automatiquement les variables numériques définies en début de code 
              (comme <code class="text-cyber-300">width = 50</code>) et vous permet de les modifier via des champs de saisie.
            </p>

            <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5 mb-4">
              <h4 class="text-white font-medium mb-2">Comment ça marche</h4>
              <ol class="list-decimal list-inside space-y-1 text-sm text-slate-400">
                <li>Les variables numériques simples sont détectées automatiquement</li>
                <li>Modifiez une valeur dans le panneau</li>
                <li>Cliquez sur "Appliquer" pour régénérer le modèle</li>
                <li>Le code source est automatiquement mis à jour</li>
              </ol>
            </div>

            <div class="flex items-center gap-2 text-sm text-amber-400">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Les valeurs doivent être &gt; 0 pour éviter les erreurs géométriques</span>
            </div>
          </div>
        </section>

        <!-- Assembly Mode -->
        <section id="assembly" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Mode Assemblage</h2>
          </div>

          <div class="glass rounded-2xl p-6 border border-white/5 mb-6">
            <p class="text-slate-400 mb-4">
              Le mode assemblage affiche toutes les pièces de votre projet simultanément. 
              Vous pouvez les positionner manuellement ou utiliser l'IA pour les assembler.
            </p>

            <div class="grid md:grid-cols-2 gap-4">
              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <h4 class="text-white font-medium mb-2 flex items-center gap-2">
                  <svg class="w-4 h-4 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                  Contrôles manuels
                </h4>
                <ul class="text-sm text-slate-400 space-y-1">
                  <li>• Cliquez sur une pièce pour la sélectionner</li>
                  <li>• Utilisez les flèches pour déplacer</li>
                  <li>• Changez le mode (Translation/Rotation)</li>
                  <li>• Entrez des valeurs précises</li>
                </ul>
              </div>

              <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                <h4 class="text-white font-medium mb-2 flex items-center gap-2">
                  <svg class="w-4 h-4 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Positionnement IA
                </h4>
                <p class="text-sm text-slate-400">
                  Décrivez comment assembler les pièces: "Place le couvercle sur la boîte" 
                  ou "Aligne la charnière avec le bord du panneau".
                </p>
              </div>
            </div>
          </div>

          <div class="glass rounded-xl p-4 border border-cyber-500/30 bg-cyber-500/5">
            <div class="flex items-start gap-3">
              <svg class="w-5 h-5 text-cyber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-sm text-slate-300">
                <strong class="text-white">Astuce:</strong> Les positions en mode assemblage sont pour la visualisation uniquement. 
                Lors de l'export 3MF, chaque pièce est exportée séparément à l'origine.
              </p>
            </div>
          </div>
        </section>

        <!-- Export -->
        <section id="export" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Export & Impression 3D</h2>
          </div>

          <div class="space-y-4">
            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">Formats disponibles</h3>
              
              <div class="grid md:grid-cols-2 gap-4">
                <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-1 bg-slate-700 rounded text-xs font-mono text-slate-300">STL</span>
                    <span class="text-white font-medium">Standard</span>
                  </div>
                  <p class="text-sm text-slate-400">
                    Format universel compatible avec tous les slicers (Cura, PrusaSlicer, etc.)
                  </p>
                </div>

                <div class="bg-dark-800/50 rounded-xl p-4 border border-white/5">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-1 bg-cyber-600 rounded text-xs font-mono text-white">3MF</span>
                    <span class="text-white font-medium">Recommandé</span>
                  </div>
                  <p class="text-sm text-slate-400">
                    Format moderne avec métadonnées. Idéal pour Bambu Studio et PrusaSlicer.
                  </p>
                </div>
              </div>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">Vérification du volume d'impression</h3>
              <p class="text-slate-400 mb-4">
                Configurez votre imprimante dans les paramètres pour vérifier si vos pièces tiennent dans le volume d'impression.
              </p>
              
              <div class="flex flex-wrap gap-2">
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Bambu Lab X1</span>
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Bambu Lab P1S</span>
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Bambu Lab P2S</span>
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Bambu Lab A1</span>
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Prusa MK4</span>
                <span class="px-3 py-1.5 bg-dark-700 rounded-lg text-sm text-slate-300">Custom...</span>
              </div>
            </div>
          </div>
        </section>

        <!-- CadQuery Guide -->
        <section id="cadquery" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Guide CadQuery rapide</h2>
          </div>

          <div class="space-y-4">
            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">Formes de base</h3>
              
              <div class="grid md:grid-cols-2 gap-4">
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Boîte</p>
                  <p class="text-slate-300">cq.Workplane("XY").box(10, 20, 30)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Cylindre</p>
                  <p class="text-slate-300">cq.Workplane("XY").cylinder(height=30, radius=10)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Sphère</p>
                  <p class="text-slate-300">cq.Workplane("XY").sphere(radius=15)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Extrusion 2D</p>
                  <p class="text-slate-300">cq.Workplane("XY").rect(20, 30).extrude(10)</p>
                </div>
              </div>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">Opérations courantes</h3>
              
              <div class="space-y-3">
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Arrondir les arêtes verticales</p>
                  <p class="text-slate-300">.edges("|Z").fillet(2)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Chanfrein sur le dessus</p>
                  <p class="text-slate-300">.edges(">Z").chamfer(1)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Percer un trou</p>
                  <p class="text-slate-300">.faces(">Z").workplane().hole(diameter=5, depth=10)</p>
                </div>
                <div class="bg-dark-900 rounded-xl p-4 font-mono text-sm">
                  <p class="text-slate-500 mb-2"># Évider (shell)</p>
                  <p class="text-slate-300">.faces(">Z").shell(-2)  <span class="text-slate-500"># -2mm d'épaisseur</span></p>
                </div>
              </div>
            </div>

            <div class="glass rounded-2xl p-6 border border-white/5">
              <h3 class="text-lg font-semibold text-white mb-4">Sélecteurs d'arêtes/faces</h3>
              
              <div class="grid md:grid-cols-3 gap-3 text-sm">
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">"|Z"</code>
                  <p class="text-slate-500 mt-1">Arêtes parallèles à Z</p>
                </div>
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">">Z"</code>
                  <p class="text-slate-500 mt-1">Faces/arêtes en haut</p>
                </div>
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">"&lt;Z"</code>
                  <p class="text-slate-500 mt-1">Faces/arêtes en bas</p>
                </div>
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">">X"</code>
                  <p class="text-slate-500 mt-1">Côté droit</p>
                </div>
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">"&lt;X"</code>
                  <p class="text-slate-500 mt-1">Côté gauche</p>
                </div>
                <div class="bg-dark-800/50 rounded-lg p-3">
                  <code class="text-cyber-300">"#Z"</code>
                  <p class="text-slate-500 mt-1">Perpendiculaire à Z</p>
                </div>
              </div>
            </div>

            <a 
              href="https://cadquery.readthedocs.io" 
              target="_blank"
              class="block glass rounded-xl p-4 border border-cyber-500/30 bg-cyber-500/5 hover:bg-cyber-500/10 transition-colors"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-cyber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  <span class="text-white font-medium">Documentation CadQuery complète</span>
                </div>
                <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </a>
          </div>
        </section>

        <!-- Tips -->
        <section id="tips" class="mb-16 scroll-mt-24">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-500/20 to-accent-500/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-white">Astuces & bonnes pratiques</h2>
          </div>

          <div class="space-y-4">
            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <span class="text-green-400 font-bold">1</span>
                </div>
                <div>
                  <h4 class="font-semibold text-white mb-1">Commencez par les paramètres</h4>
                  <p class="text-sm text-slate-400">
                    Définissez toutes les dimensions en variables au début du code. Cela facilite les ajustements ultérieurs.
                  </p>
                </div>
              </div>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <span class="text-green-400 font-bold">2</span>
                </div>
                <div>
                  <h4 class="font-semibold text-white mb-1">Fillets et chamfers en dernier</h4>
                  <p class="text-sm text-slate-400">
                    Appliquez les arrondis (fillet) et chanfreins après avoir créé la géométrie de base. 
                    Assurez-vous que le rayon est inférieur à la moitié de la plus petite arête.
                  </p>
                </div>
              </div>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <span class="text-green-400 font-bold">3</span>
                </div>
                <div>
                  <h4 class="font-semibold text-white mb-1">Utilisez le contexte IA</h4>
                  <p class="text-sm text-slate-400">
                    Activez "Utiliser le contexte" dans le compositeur IA pour que les nouvelles pièces 
                    soient dimensionnées en fonction des pièces existantes du projet.
                  </p>
                </div>
              </div>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <span class="text-green-400 font-bold">4</span>
                </div>
                <div>
                  <h4 class="font-semibold text-white mb-1">Dupliquez avant de modifier</h4>
                  <p class="text-sm text-slate-400">
                    Utilisez le clic droit pour dupliquer un projet ou une section avant d'expérimenter 
                    des modifications majeures.
                  </p>
                </div>
              </div>
            </div>

            <div class="glass rounded-xl p-5 border border-white/5">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                  <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <h4 class="font-semibold text-white mb-1">Erreurs courantes</h4>
                  <ul class="text-sm text-slate-400 space-y-1 mt-2">
                    <li>• <strong class="text-slate-300">Fillet trop grand:</strong> Le rayon dépasse la taille de l'arête</li>
                    <li>• <strong class="text-slate-300">Division par zéro:</strong> Un paramètre vaut 0</li>
                    <li>• <strong class="text-slate-300">Géométrie invalide:</strong> Formes qui s'auto-intersectent</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Footer -->
        <footer class="text-center py-8 border-t border-white/5">
          <p class="text-slate-500 text-sm">
            VoxelMind AI - Générateur de modèles 3D par IA
          </p>
          <p class="text-slate-600 text-xs mt-2">
            Propulsé par CadQuery et OpenCascade
          </p>
        </footer>
      </main>
    </div>
  </div>
</template>
