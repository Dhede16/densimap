<template>
  <div class="densimap-wrapper" :class="{ 'panel-open': isLeftPanelOpen }">
    <!-- Left Panel Toggle Button (fixed on left edge) -->
    <button
      class="panel-toggle-btn"
      @click="isLeftPanelOpen = !isLeftPanelOpen"
      :title="isLeftPanelOpen ? 'Tutup Panel' : 'Buka Panel'"
      :aria-label="isLeftPanelOpen ? 'Close panel' : 'Open panel'"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="20" height="20">
        <path v-if="isLeftPanelOpen" d="M15 18l-6-6 6-6" />
        <path v-else d="M9 18l6-6-6-6" />
      </svg>
    </button>

    <!-- Top Header Bar -->
    <header class="top-header">
      <div class="brand-section">
        <div class="logo-icon">
          <img src="/assets/logo.jpg" alt="DensiMap Logo" class="logo-img" />
        </div>
        <div class="brand-text">
          <h1>DensiMap Samarinda</h1>
          <span class="subtitle">Pemetaan Kepadatan Penduduk Hybrid K-Means & Hierarchical</span>
        </div>
      </div>

      <div class="header-actions">
        <!-- Search Kecamatan Input -->
        <div class="search-container" ref="searchContainerRef">
          <div class="search-input-wrapper">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              v-model="searchQuery"
              @focus="isSearchOpen = true"
              type="text"
              placeholder="Cari kecamatan..."
              class="search-input"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''; isSearchOpen = false"
              class="clear-search-btn"
              title="Bersihkan"
            >
              ✕
            </button>
          </div>

          <!-- Search Dropdown Results -->
          <div v-if="isSearchOpen && filteredKecamatan.length > 0" class="search-dropdown">
            <div
              v-for="item in filteredKecamatan"
              :key="item.id"
              @click="selectKecamatan(item)"
              class="search-item"
            >
              <div class="item-info">
                <span class="item-name">{{ item.nama }}</span>
                <span class="item-density">{{ formatNumber(item.kepadatan_penduduk) }} jiwa/km²</span>
              </div>
              <span class="cluster-pill" :class="'pill-' + item.cluster_label.toLowerCase()">
                {{ item.cluster_label }}
              </span>
            </div>
          </div>
        </div>

        <!-- Table Summary Button -->
        <button class="action-btn" @click="showTableModal = true" title="Lihat Data Seluruh Kecamatan">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
          <span>Data Tabel</span>
        </button>

        <!-- Start Button - Opens Left Panel -->
        <button
          class="start-btn"
          @click="isLeftPanelOpen = true"
          :disabled="isLeftPanelOpen"
          :title="isLeftPanelOpen ? 'Panel sudah terbuka' : 'Mulai / Buka Panel'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          <span>Mulai</span>
        </button>
      </div>
    </header>

    <!-- Interactive Map Container -->
    <div id="map-view" class="map-view"></div>

    <!-- Left Sliding Panel -->
    <aside
      class="left-panel"
      :class="{ open: isLeftPanelOpen }"
    >
      <div class="left-panel-content">
        <div class="left-panel-header">
          <h3>Alur Penerapan Model (Step-by-Step)</h3>
          <p class="panel-subtitle">Tahun: <strong>{{ panelYear }}</strong> · Klik "Jalankan" pada setiap tahap</p>
        </div>
        <div class="left-panel-body">
          <!-- Year Selector in Panel -->
          <div class="panel-year-selector">
            <label>Pilih Tahun Data:</label>
            <select v-model="panelYear" @change="onPanelYearChange" class="panel-year-select">
              <option v-for="year in availableYears" :key="year" :value="year">
                {{ year }}
              </option>
            </select>
          </div>

          <!-- Model Pipeline Flow - Interactive Steps -->
          <div class="pipeline-flow">
            <div class="pipeline-step" v-for="(step, idx) in pipelineSteps" :key="step.id">
              <div class="step-number">{{ idx + 1 }}</div>
              <div class="step-content">
                <div class="step-header">
                  <h5>{{ step.title }}</h5>
                  <span class="step-status" :class="{ completed: isStepCompleted(step.id), active: activeStepId === step.id }">
                    {{ isStepCompleted(step.id) ? '✓ Selesai' : (activeStepId === step.id ? '▶ Sedang' : '⏳ Belum') }}
                  </span>
                </div>
                <p class="step-desc">{{ step.desc }}</p>
                <p class="step-short">{{ step.shortDesc }}</p>

                <!-- Run Button -->
                <button
                  class="step-run-btn"
                  @click="runStep(step.id)"
                  :disabled="activeStepId === step.id || isStepCompleted(step.id) || !canRunStep(step.id)"
                >
                  {{ activeStepId === step.id ? 'Menjalankan...' : (isStepCompleted(step.id) ? 'Selesai' : 'Jalankan Tahap Ini') }}
                </button>

                <!-- Step Result Display -->
                <div v-if="stepResults[step.id]" class="step-result" :key="step.id">
                  <div class="result-header">
                    <h6>{{ stepResults[step.id].title }}</h6>
                    <span class="result-summary">{{ stepResults[step.id].summary }}</span>
                  </div>

                  <!-- Data Table for steps with rows -->
                  <div v-if="stepResults[step.id].columns && stepResults[step.id].rows" class="result-table-container">
                    <table class="result-table">
                      <thead>
                        <tr>
                          <th v-for="(col, ci) in stepResults[step.id].columns" :key="ci">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, ri) in stepResults[step.id].rows" :key="ri">
                          <td v-for="(cell, cj) in row" :key="cj">{{ cell }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Formulas for feature engineering -->
                  <div v-if="stepResults[step.id].formulas" class="result-formulas">
                    <h6>Rumus yang Digunakan:</h6>
                    <ul>
                      <li v-for="(f, fi) in stepResults[step.id].formulas" :key="fi">{{ f }}</li>
                    </ul>
                  </div>

                  <!-- Stats for preprocessing -->
                  <div v-if="stepResults[step.id].stats" class="result-stats">
                    <h6>Statistik Standardisasi:</h6>
                    <div class="stats-grid">
                      <div class="stat-item">
                        <span class="stat-label">Mean</span>
                        <span class="stat-value">[{{ stepResults[step.id].stats.mean.join(', ') }}]</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">Std Dev</span>
                        <span class="stat-value">[{{ stepResults[step.id].stats.std.join(', ') }}]</span>
                      </div>
                    </div>
                  </div>

                  <!-- Silhouette by K for hierarchical -->
                  <div v-if="stepResults[step.id].silhouetteByK" class="result-silhouette">
                    <h6>Silhouette Score per k:</h6>
                    <div class="silhouette-bars">
                      <div v-for="s in stepResults[step.id].silhouetteByK" :key="s.k" class="silhouette-bar">
                        <span class="k-label">k={{ s.k }}</span>
                        <div class="bar-container">
                          <div class="bar-fill" :style="{ width: (s.score * 100) + '%' }"></div>
                        </div>
                        <span class="score-value">{{ s.score.toFixed(3) }}</span>
                      </div>
                    </div>
                    <p class="silhouette-note">Linkage: {{ stepResults[step.id].linkage }} · Metric: {{ stepResults[step.id].metric }}</p>
                  </div>

                  <!-- Clusters for kmeans/evaluation -->
                  <div v-if="stepResults[step.id].clusters" class="result-clusters">
                    <h6>Hasil Cluster:</h6>
                    <div class="clusters-grid">
                      <div
                        v-for="c in stepResults[step.id].clusters"
                        :key="c.label"
                        class="cluster-detail-card"
                        :class="'cluster-' + c.label.toLowerCase()"
                      >
                        <div class="cluster-detail-header">
                          <span class="cluster-detail-label">{{ c.label }}</span>
                          <span class="cluster-detail-count">{{ c.count }} kecamatan</span>
                        </div>
                        <div v-if="c.avg_density !== undefined" class="cluster-metrics">
                          <div class="metric-row">
                            <span>Rata² Kepadatan Penduduk:</span>
                            <span>{{ formatDecimal(c.avg_density) }} jiwa/km²</span>
                          </div>
                          <div v-if="c.avg_house_density !== undefined" class="metric-row">
                            <span>Rata² Kepadatan Rumah:</span>
                            <span>{{ formatDecimal(c.avg_house_density) }} rumah/km²</span>
                          </div>
                          <div v-if="c.avg_occupants !== undefined" class="metric-row">
                            <span>Rata² Penghuni/Rumah:</span>
                            <span>{{ formatDecimal(c.avg_occupants) }} orang</span>
                          </div>
                        </div>
                        <div class="cluster-kecamatan">
                          <strong>Kecamatan:</strong> {{ c.kecamatan.join(', ') }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Metrics for kmeans -->
                  <div v-if="stepResults[step.id].metrics && !stepResults[step.id].clusters" class="result-metrics">
                    <h6>Metrik Evaluasi:</h6>
                    <div class="metrics-grid-small">
                      <div v-for="(val, key) in stepResults[step.id].metrics" :key="key" class="metric-small">
                        <span class="metric-key">{{ key.replace(/_/g, ' ').toUpperCase() }}</span>
                        <span class="metric-val">{{ typeof val === 'number' ? val.toFixed(3) : val }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Visualization info -->
                  <div v-if="stepResults[step.id].color_scheme" class="result-visualization">
                    <h6>Skema Warna Cluster:</h6>
                    <div class="color-legend">
                      <div v-for="(color, label) in stepResults[step.id].color_scheme" :key="label" class="color-item">
                        <span class="color-swatch" :style="{ background: color.split(' ')[0] }"></span>
                        <span>{{ label }}: {{ color }}</span>
                      </div>
                    </div>
                    <h6>Interaktivitas:</h6>
                    <ul>
                      <li v-for="(item, i) in stepResults[step.id].interactivity" :key="i">{{ item }}</li>
                    </ul>
                  </div>

                  <!-- Interpretation for evaluation -->
                  <div v-if="stepResults[step.id].interpretation" class="result-interpretation">
                    <h6>Interpretasi Cluster:</h6>
                    <div class="interpretation-list">
                      <div v-for="(desc, label) in stepResults[step.id].interpretation" :key="label" class="interpretation-item" :class="'interp-' + label.toLowerCase()">
                        <strong>{{ label }}:</strong> {{ desc }}
                      </div>
                    </div>
                  </div>

                  <!-- Params for kmeans -->
                  <div v-if="stepResults[step.id].params" class="result-params">
                    <h6>Parameter K-Means:</h6>
                    <div class="params-grid">
                      <div v-for="(val, key) in stepResults[step.id].params" :key="key" class="param-item">
                        <span class="param-key">{{ key.replace(/_/g, ' ') }}</span>
                        <span class="param-val">{{ val }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="step-arrow" v-if="idx < pipelineSteps.length - 1">→</div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Floating Reset View Button -->
    <button class="reset-view-btn" @click="resetMapBounds" title="Kembalikan Tampilan Peta Samarinda">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
        <path d="M3 3v5h5"></path>
      </svg>
      <span>Reset Fokus</span>
    </button>

    <!-- Legend Panel (W-06) -->
    <aside class="legend-panel">
      <div class="legend-header">
        <h3>Tingkat Kepadatan</h3>
        <span class="legend-badge">Klaster</span>
      </div>

      <div class="legend-items">
        <div
          class="legend-row"
          :class="{ active: selectedClusterFilter === 'Tinggi' }"
          @click="toggleClusterFilter('Tinggi')"
        >
          <span class="legend-color-box high"></span>
          <div class="legend-desc">
            <span class="label">Tinggi</span>
            <span class="sublabel">&gt; 5.000 jiwa/km² ({{ clusterCounts['Tinggi'] || 0 }})</span>
          </div>
        </div>

        <div
          class="legend-row"
          :class="{ active: selectedClusterFilter === 'Sedang' }"
          @click="toggleClusterFilter('Sedang')"
        >
          <span class="legend-color-box mid"></span>
          <div class="legend-desc">
            <span class="label">Sedang</span>
            <span class="sublabel">1.000 - 5.000 jiwa/km² ({{ clusterCounts['Sedang'] || 0 }})</span>
          </div>
        </div>

        <div
          class="legend-row"
          :class="{ active: selectedClusterFilter === 'Rendah' }"
          @click="toggleClusterFilter('Rendah')"
        >
          <span class="legend-color-box low"></span>
          <div class="legend-desc">
            <span class="label">Rendah</span>
            <span class="sublabel">&lt; 1.000 jiwa/km² ({{ clusterCounts['Rendah'] || 0 }})</span>
          </div>
        </div>
      </div>

      <div v-if="selectedClusterFilter" class="filter-reset-hint" @click="toggleClusterFilter(null)">
        <span>Tampilkan Semua Klaster ✕</span>
      </div>

      <!-- Clustering Evaluation Metrics -->
      <div v-if="clusteringMetrics" class="metrics-section">
        <div class="metrics-header">
          <h4>Evaluasi Klasterisasi</h4>
          <span class="metrics-badge">K-Means</span>
        </div>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="metric-label">Silhouette Score</span>
            <span class="metric-value">{{ clusteringMetrics.kmeans.silhouette.toFixed(3) }}</span>
            <span class="metric-desc" v-if="clusteringMetrics.kmeans.silhouette >= 0.5">Baik</span>
            <span class="metric-desc" v-else-if="clusteringMetrics.kmeans.silhouette >= 0.25">Sedang</span>
            <span class="metric-desc" v-else>Rendah</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Davies-Bouldin</span>
            <span class="metric-value">{{ clusteringMetrics.kmeans.davies_bouldin.toFixed(3) }}</span>
            <span class="metric-desc">Lebih rendah = lebih baik</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Inertia</span>
            <span class="metric-value">{{ clusteringMetrics.kmeans.inertia.toFixed(1) }}</span>
            <span class="metric-desc">Within-cluster variance</span>
          </div>
        </div>

        <div v-if="clusterStats" class="cluster-stats">
          <h5>Karakteristik Cluster</h5>
          <div class="cluster-stats-grid">
            <div
              v-for="label in ['Rendah', 'Sedang', 'Tinggi']"
              :key="label"
              class="cluster-stat-card"
              :class="'stat-' + label.toLowerCase()"
            >
              <div class="stat-header">
                <span class="stat-label">{{ label }}</span>
                <span class="stat-count">{{ clusterStats[label]?.count || 0 }} kec</span>
              </div>
              <div class="stat-metrics">
                <div class="stat-row">
                  <span class="stat-name">Kep. Penduduk</span>
                  <span class="stat-val">{{ formatDecimal(clusterStats[label]?.avg_kepadatan_penduduk || 0) }} jiwa/km²</span>
                </div>
                <div class="stat-row">
                  <span class="stat-name">Kep. Rumah</span>
                  <span class="stat-val">{{ formatDecimal(clusterStats[label]?.avg_kepadatan_rumah || 0) }} rumah/km²</span>
                </div>
                <div class="stat-row">
                  <span class="stat-name">Rata² Penghuni</span>
                  <span class="stat-val">{{ formatDecimal(clusterStats[label]?.avg_rata_rata_penghuni || 0) }} orang/rumah</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Table Modal View -->
    <div v-if="showTableModal" class="modal-backdrop" @click.self="showTableModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h2>Data Kepadatan 10 Kecamatan Kota Samarinda</h2>
            <p>Hasil pengelompokan menggunakan metode Hybrid Hierarchical Clustering & K-Means</p>
          </div>
          <div class="modal-header-actions">
            <!-- Year Selector inside Modal -->
            <div class="year-select-container modal-year-select" title="Pilih Tahun Data">
              <svg class="year-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
              <select v-model="selectedYear" @change="onYearChange" class="year-select">
                <option v-for="year in availableYears" :key="year" :value="year">
                  Tahun {{ year }}
                </option>
              </select>
              <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <button class="close-modal-btn" @click="showTableModal = false" title="Tutup">✕</button>
          </div>
        </div>

        <div class="modal-body">
          <!-- Mini summary stats for active year -->
          <div class="modal-summary-bar">
            <div class="summary-pill">
              <span class="summary-label">Tahun</span>
              <span class="summary-value highlight">{{ selectedYear }}</span>
            </div>
            <div class="summary-pill">
              <span class="summary-label">Total Penduduk</span>
              <span class="summary-value">{{ formatNumber(totalPenduduk) }} jiwa</span>
            </div>
            <div class="summary-pill">
              <span class="summary-label">Total Rumah</span>
              <span class="summary-value">{{ formatNumber(totalRumah) }} unit</span>
            </div>
            <div class="summary-pill">
              <span class="summary-label">Rata-rata Kepadatan</span>
              <span class="summary-value">{{ formatDecimal(avgKepadatan) }} jiwa/km²</span>
            </div>
          </div>

          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Kecamatan</th>
                  <th>Tahun</th>
                  <th>Klaster</th>
                  <th class="text-right">Penduduk (jiwa)</th>
                  <th class="text-right">Luas (km²)</th>
                  <th class="text-right">Rumah (unit)</th>
                  <th class="text-right">Kepadatan (jiwa/km²)</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in kecamatanList" :key="item.id">
                  <td>{{ idx + 1 }}</td>
                  <td class="font-bold">{{ item.nama }}</td>
                  <td><span class="year-badge">{{ item.tahun || selectedYear }}</span></td>
                  <td>
                    <span class="cluster-pill" :class="'pill-' + item.cluster_label.toLowerCase()">
                      {{ item.cluster_label }}
                    </span>
                  </td>
                  <td class="text-right">{{ formatNumber(item.jumlah_penduduk) }}</td>
                  <td class="text-right">{{ formatDecimal(item.luas_km2) }}</td>
                  <td class="text-right">{{ formatNumber(item.jumlah_rumah) }}</td>
                  <td class="text-right font-bold">{{ formatDecimal(item.kepadatan_penduduk) }}</td>
                  <td>
                    <button class="row-focus-btn" @click="selectKecamatanFromModal(item)">
                      Lihat di Peta
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import { getKecamatanData } from './services/supabase'

// Reactive state
const availableYears = [2020, 2021, 2022, 2023, 2024, 2025]
const selectedYear = ref(2025)
const searchQuery = ref('')
const isSearchOpen = ref(false)
const searchContainerRef = ref(null)
const dataSource = ref('local')
const mapboxActive = ref(false)
const showTableModal = ref(false)
const selectedClusterFilter = ref(null)
const isLeftPanelOpen = ref(false)
const clusteringMetrics = ref(null)
const clusterStats = ref(null)
const clusterTransitions = ref({})
const panelYear = ref(2025)

const kecamatanList = ref([])
const clusterCounts = ref({ Rendah: 0, Sedang: 0, Tinggi: 0 })

let map = null
let geoJsonLayer = null
let defaultBounds = null
const layerMap = new Map()

// Format helpers
const formatNumber = (val) => new Intl.NumberFormat('id-ID').format(val)
const formatDecimal = (val) => new Intl.NumberFormat('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)

// Pipeline steps definition
const pipelineSteps = [
  {
    id: 'raw-data',
    title: '1. Data Mentah (BPS)',
    desc: 'Jumlah Penduduk, Luas Wilayah (km²), Jumlah Rumah per Kecamatan',
    shortDesc: 'Data asli dari BPS Kota Samarinda'
  },
  {
    id: 'feature-engineering',
    title: '2. Feature Engineering',
    desc: 'Menghitung fitur turunan: Kepadatan Penduduk, Kepadatan Rumah, Rata² Penghuni',
    shortDesc: 'Rumus: Penduduk/Luas, Rumah/Luas, Penduduk/Rumah'
  },
  {
    id: 'preprocessing',
    title: '3. Preprocessing & Standardisasi',
    desc: 'Validasi data, cek missing value, standarisasi Z-score (mean=0, std=1)',
    shortDesc: 'StandardScaler pada 3 fitur numerik'
  },
  {
    id: 'hierarchical',
    title: '4. Hierarchical Clustering (Ward)',
    desc: 'Agglomerative clustering dengan linkage Ward, validasi k optimal via silhouette',
    shortDesc: 'Dendrogram & silhouette per k=2..5'
  },
  {
    id: 'kmeans',
    title: '5. K-Means Clustering',
    desc: 'Pengelompokan final ke 3 cluster, inisialisasi k-means++',
    shortDesc: 'n_clusters=3, random_state=42, n_init=20'
  },
  {
    id: 'evaluation',
    title: '6. Evaluasi & Interpretasi',
    desc: 'Silhouette Score, Davies-Bouldin, labeling cluster by density mean',
    shortDesc: 'Kualitas cluster & penamaan Rendah/Sedang/Tinggi'
  },
  {
    id: 'visualization',
    title: '7. Visualisasi Peta (GIS)',
    desc: 'Render GeoJSON ke Leaflet, warna per cluster, tooltip & popup',
    shortDesc: 'Basemap Mapbox/CartoDB + 10 polygons'
  }
]
 
// Active step state
const activeStepId = ref(null)
const stepResults = ref({})
const completedSteps = ref([])
const visualizationDone = ref(false)

const stepOrder = ['raw-data', 'feature-engineering', 'preprocessing', 'hierarchical', 'kmeans', 'evaluation', 'visualization']

const canRunStep = (stepId) => {
  const stepIndex = stepOrder.indexOf(stepId)
  if (stepIndex === 0) return true
  return stepOrder.slice(0, stepIndex).every(s => completedSteps.value.includes(s))
}

const isStepCompleted = (stepId) => completedSteps.value.includes(stepId)

// Panel year change handler
const onPanelYearChange = async () => {
  await loadData(panelYear.value)
  activeStepId.value = null
  stepResults.value = {}
  completedSteps.value = []
  visualizationDone.value = false
}

// Run a specific pipeline step with real data
const runStep = async (stepId) => {
  if (!canRunStep(stepId)) return

  activeStepId.value = stepId
  const list = kecamatanList.value
  if (!list.length) return

  let result = null

  switch (stepId) {
    case 'raw-data':
      result = computeRawData(list)
      break
    case 'feature-engineering':
      result = computeFeatureEngineering(list)
      break
    case 'preprocessing':
      result = computePreprocessing(list)
      break
    case 'hierarchical':
      result = computeHierarchical()
      break
    case 'kmeans':
      result = computeKMeans()
      break
    case 'evaluation':
      result = computeEvaluation()
      break
    case 'visualization':
      result = computeVisualization(list)
      visualizationDone.value = true
      if (geoJsonLayer) {
        geoJsonLayer.setStyle(polygonStyle)
      }
      break
  }

  stepResults.value[stepId] = result
  if (!completedSteps.value.includes(stepId)) {
    completedSteps.value.push(stepId)
  }
  activeStepId.value = null
}

// Step computation functions using real data
const computeRawData = (list) => {
  return {
    title: 'Data Mentah (BPS) - Tahun ' + panelYear.value,
    columns: ['Kecamatan', 'Penduduk (jiwa)', 'Luas (km²)', 'Rumah (unit)'],
    rows: list.map(item => [
      item.nama,
      formatNumber(item.jumlah_penduduk),
      formatDecimal(item.luas_km2),
      formatNumber(item.jumlah_rumah)
    ]),
    summary: `Total: ${list.length} kecamatan · ${formatNumber(list.reduce((a,b)=>a+Number(b.jumlah_penduduk),0))} jiwa · ${formatDecimal(list.reduce((a,b)=>a+Number(b.luas_km2),0))} km²`
  }
}

const computeFeatureEngineering = (list) => {
  return {
    title: 'Feature Engineering - Tahun ' + panelYear.value,
    columns: ['Kecamatan', 'Kepadatan Penduduk (jiwa/km²)', 'Kepadatan Rumah (rumah/km²)', 'Rata² Penghuni (org/rumah)'],
    rows: list.map(item => [
      item.nama,
      formatDecimal(item.kepadatan_penduduk),
      formatDecimal(item.kepadatan_rumah || (item.jumlah_rumah / item.luas_km2)),
      formatDecimal(item.rata_rata_penghuni || (item.jumlah_penduduk / item.jumlah_rumah))
    ]),
    formulas: [
      'Kepadatan Penduduk = Jumlah Penduduk / Luas Wilayah',
      'Kepadatan Rumah = Jumlah Rumah / Luas Wilayah',
      'Rata-rata Penghuni = Jumlah Penduduk / Jumlah Rumah'
    ],
    summary: `Rata² kepadatan: ${formatDecimal(list.reduce((a,b)=>a+Number(b.kepadatan_penduduk),0)/list.length)} jiwa/km²`
  }
}

const computePreprocessing = (list) => {
  // Compute z-scores manually for display
  const features = list.map(item => [
    Number(item.kepadatan_penduduk),
    Number(item.kepadatan_rumah || (item.jumlah_rumah / item.luas_km2)),
    Number(item.rata_rata_penghuni || (item.jumlah_penduduk / item.jumlah_rumah))
  ])

  const means = [0, 1, 2].map(i => features.reduce((a, b) => a + b[i], 0) / features.length)
  const stds = [0, 1, 2].map(i => Math.sqrt(features.reduce((a, b) => a + Math.pow(b[i] - means[i], 2), 0) / features.length))

  const scaled = features.map(row => row.map((val, i) => (val - means[i]) / (stds[i] || 1)))

  return {
    title: 'Preprocessing & Standardisasi (Z-Score) - Tahun ' + panelYear.value,
    columns: ['Kecamatan', 'Kep. Penduduk (asli)', 'Kep. Penduduk (z-score)', 'Kep. Rumah (asli)', 'Kep. Rumah (z-score)', 'Rata² Penghuni (asli)', 'Rata² Penghuni (z-score)'],
    rows: list.map((item, idx) => [
      item.nama,
      formatDecimal(features[idx][0]),
      formatDecimal(scaled[idx][0]),
      formatDecimal(features[idx][1]),
      formatDecimal(scaled[idx][1]),
      formatDecimal(features[idx][2]),
      formatDecimal(scaled[idx][2])
    ]),
    stats: {
      mean: means.map(m => formatDecimal(m)),
      std: stds.map(s => formatDecimal(s))
    },
    summary: `Mean: [${means.map(m=>formatDecimal(m)).join(', ')}] · Std: [${stds.map(s=>formatDecimal(s)).join(', ')}]`
  }
}

const computeHierarchical = () => {
  const metrics = clusteringMetrics.value?.hierarchical || {}
  const byK = metrics.silhouette_by_k || {}
  return {
    title: 'Hierarchical Clustering (Ward) - Tahun ' + panelYear.value,
    metrics: {
      optimal_k: metrics.optimal_k_suggestion || 3,
      silhouette: metrics.silhouette || 0,
      davies_bouldin: metrics.davies_bouldin || 0
    },
    silhouetteByK: Object.entries(byK).map(([k, v]) => ({ k: Number(k), score: v })),
    linkage: 'Ward',
    metric: 'Euclidean',
    summary: `Optimal k: ${metrics.optimal_k_suggestion || 3} (Silhouette: ${(metrics.silhouette || 0).toFixed(3)})`
  }
}

const computeKMeans = () => {
  const metrics = clusteringMetrics.value?.kmeans || {}
  const clusterStatsLocal = clusterStats.value || {}
  const list = kecamatanList.value

  // Fallback: compute cluster stats from raw data if backend stats not available
  const computedStats = {}
  if (list.length && Object.keys(clusterStatsLocal).length === 0) {
    const clusters = ['Rendah', 'Sedang', 'Tinggi']
    clusters.forEach(label => {
      const items = list.filter(item => item.cluster_label === label)
      if (items.length > 0) {
        computedStats[label] = {
          count: items.length,
          avg_kepadatan_penduduk: items.reduce((a, b) => a + Number(b.kepadatan_penduduk), 0) / items.length,
          avg_kepadatan_rumah: items.reduce((a, b) => a + Number(b.kepadatan_rumah || (b.jumlah_rumah / b.luas_km2)), 0) / items.length,
          avg_rata_rata_penghuni: items.reduce((a, b) => a + Number(b.rata_rata_penghuni || (b.jumlah_penduduk / b.jumlah_rumah)), 0) / items.length,
          kecamatan: items.map(i => i.nama)
        }
      }
    })
  }
  const statsSource = Object.keys(computedStats).length > 0 ? computedStats : clusterStatsLocal

  return {
    title: 'K-Means Clustering - Tahun ' + panelYear.value,
    params: { n_clusters: 3, random_state: 42, n_init: 20 },
    metrics: {
      silhouette: metrics.silhouette || 0,
      davies_bouldin: metrics.davies_bouldin || 0,
      inertia: metrics.inertia || 0
    },
    clusters: ['Rendah', 'Sedang', 'Tinggi'].map(label => ({
      label,
      count: statsSource[label]?.count || 0,
      avg_density: statsSource[label]?.avg_kepadatan_penduduk || 0,
      kecamatan: statsSource[label]?.kecamatan || []
    })),
    summary: `Silhouette: ${(metrics.silhouette || 0).toFixed(3)} · DB Index: ${(metrics.davies_bouldin || 0).toFixed(3)}`
  }
}

const computeEvaluation = () => {
  const clusterStatsLocal = clusterStats.value || {}
  const list = kecamatanList.value
  const order = ['Rendah', 'Sedang', 'Tinggi']

  // Fallback: compute from raw data
  const computedStats = {}
  if (list.length && Object.keys(clusterStatsLocal).length === 0) {
    order.forEach(label => {
      const items = list.filter(item => item.cluster_label === label)
      if (items.length > 0) {
        computedStats[label] = {
          count: items.length,
          avg_kepadatan_penduduk: items.reduce((a, b) => a + Number(b.kepadatan_penduduk), 0) / items.length,
          avg_kepadatan_rumah: items.reduce((a, b) => a + Number(b.kepadatan_rumah || (b.jumlah_rumah / b.luas_km2)), 0) / items.length,
          avg_rata_rata_penghuni: items.reduce((a, b) => a + Number(b.rata_rata_penghuni || (b.jumlah_penduduk / b.jumlah_rumah)), 0) / items.length,
          kecamatan: items.map(i => i.nama)
        }
      }
    })
  }
  const statsSource = Object.keys(computedStats).length > 0 ? computedStats : clusterStatsLocal

  return {
    title: 'Evaluasi & Interpretasi - Tahun ' + panelYear.value,
    clusters: order.map(label => ({
      label,
      count: statsSource[label]?.count || 0,
      avg_density: statsSource[label]?.avg_kepadatan_penduduk || 0,
      avg_house_density: statsSource[label]?.avg_kepadatan_rumah || 0,
      avg_occupants: statsSource[label]?.avg_rata_rata_penghuni || 0,
      kecamatan: statsSource[label]?.kecamatan || []
    })),
    interpretation: {
      Rendah: 'Kepadatan < 1.000 jiwa/km² — Wilayah perbukitan/perkebunan',
      Sedang: 'Kepadatan 1.000–5.000 jiwa/km² — Wilayah transisi/perkotaan',
      Tinggi: 'Kepadatan > 5.000 jiwa/km² — Pusat kota/permukiman padat'
    },
    summary: `${order.map(l => `${l}: ${statsSource[l]?.count || 0} kec`).join(' · ')}`
  }
}

const computeVisualization = (list) => {
  return {
    title: 'Visualisasi Peta (GIS) - Tahun ' + panelYear.value,
    basemap: 'Mapbox Outdoors-v12 / CartoDB Positron',
    features: list.length,
    geometry_type: 'Polygon / MultiPolygon',
    color_scheme: {
      Rendah: '#10B981 (Hijau)',
      Sedang: '#F59E0B (Amber)',
      Tinggi: '#EF4444 (Merah)'
    },
    interactivity: ['Tooltip on hover', 'Popup on click', 'Cluster filter', 'Reset view'],
    summary: `${list.length} polygon kecamatan siap dirender`
  }
}

// Computed stats for selected year table view
const totalPenduduk = computed(() => {
  return kecamatanList.value.reduce((acc, item) => acc + (Number(item.jumlah_penduduk) || 0), 0)
})

const totalRumah = computed(() => {
  return kecamatanList.value.reduce((acc, item) => acc + (Number(item.jumlah_rumah) || 0), 0)
})

const avgKepadatan = computed(() => {
  if (!kecamatanList.value.length) return 0
  const total = kecamatanList.value.reduce((acc, item) => acc + (Number(item.kepadatan_penduduk) || 0), 0)
  return total / kecamatanList.value.length
})

// Color scheme based on cluster label
const getClusterColor = (label) => {
  switch (label) {
    case 'Tinggi':
      return '#EF4444' // Red
    case 'Sedang':
      return '#F59E0B' // Amber
    case 'Rendah':
      return '#10B981' // Green
    default:
      return '#6B7280'
  }
}

// Filtered search results
const filteredKecamatan = computed(() => {
  if (!searchQuery.value.trim()) return kecamatanList.value
  const q = searchQuery.value.toLowerCase().trim()
  return kecamatanList.value.filter((item) => item.nama.toLowerCase().includes(q))
})

// Initialize Leaflet Map with Mapbox Light 2D or CartoDB Positron
const initMap = () => {
  // Koordinat pusat Samarinda (-0.502, 117.153)
  map = L.map('map-view', {
    center: [-0.502, 117.153],
    zoom: 11,
    zoomControl: false,
    attributionControl: false,
  })

  // Leaflet Zoom Control (+ / -) di kanan bawah
  L.control.zoom({ position: 'bottomright' }).addTo(map)

  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN
  if (mapboxToken) {
    mapboxActive.value = true
    L.tileLayer(`https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/{z}/{x}/{y}?access_token=${mapboxToken}`, {
      tileSize: 512,
      zoomOffset: -1,
      maxZoom: 18,
      attribution: '© <a href="https://www.mapbox.com/">Mapbox</a> © <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
    }).addTo(map)
  } else {
    mapboxActive.value = false
    // Elegant CartoDB Positron 2D Light basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    }).addTo(map)
  }
}

// Style function for polygon
const polygonStyle = (feature) => {
  const cluster = feature.properties.cluster_label
  const isMatchFilter = !selectedClusterFilter.value || selectedClusterFilter.value === cluster

  if (!visualizationDone.value) {
    // Show only boundaries before visualization step
    return {
      fillColor: '#E2E8F0',
      fillOpacity: 0.1,
      weight: 1.5,
      opacity: 0.6,
      color: '#94A3B8',
      dashArray: '5, 5',
    }
  }

  return {
    fillColor: getClusterColor(cluster),
    weight: 1.8,
    opacity: 1,
    color: '#334155',
    dashArray: '',
    fillOpacity: isMatchFilter ? 0.65 : 0.15,
  }
}

// Build interactive GeoJSON layer
const renderGeoJson = (geojson) => {
  if (geoJsonLayer) {
    map.removeLayer(geoJsonLayer)
  }
  layerMap.clear()

  geoJsonLayer = L.geoJSON(geojson, {
    style: polygonStyle,
    onEachFeature: (feature, layer) => {
      const props = feature.properties
      layerMap.set(props.id, layer)

      // Hover Tooltip
      layer.bindTooltip(
        `<strong>${props.nama}</strong><br><span style="font-size:11px; opacity:0.9;">${formatDecimal(props.kepadatan_penduduk)} jiwa/km²</span>`,
        { className: 'densimap-tooltip', sticky: true, direction: 'top' }
      )

      // Hover dynamic highlight
      layer.on({
        mouseover: (e) => {
          const l = e.target
          l.setStyle({
            weight: 3.5,
            color: '#0F172A',
            fillOpacity: 0.85,
          })
          if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
            l.bringToFront()
          }
        },
        mouseout: (e) => {
          geoJsonLayer.resetStyle(e.target)
        },
        click: (e) => {
          e.target.closeTooltip()
          //geoJsonLayer.resetStyle(e.target) //layer hitam
          map.fitBounds(e.target.getBounds(), { maxZoom: 13, padding: [60, 60] })
        },
      })

      // Popup Content (W-04)
      const popupHtml = `
        <div class="custom-popup-card">
          <div class="popup-card-header ${props.cluster_label.toLowerCase()}">
            <span class="popup-title">${props.nama}</span>
            <span class="popup-badge ${props.cluster_label.toLowerCase()}">
              Klaster ${props.cluster_label}
            </span>
          </div>
          <div class="popup-card-body">
            <div class="metric-highlight">
              <span class="metric-label">Kepadatan Penduduk</span>
              <span class="metric-number">${formatDecimal(props.kepadatan_penduduk)} <small>jiwa/km²</small></span>
            </div>
            <div class="popup-grid">
              <div class="grid-item">
                <span class="grid-label">👥 Jumlah Penduduk</span>
                <span class="grid-val">${formatNumber(props.jumlah_penduduk)} jiwa</span>
              </div>
              <div class="grid-item">
                <span class="grid-label">📐 Luas Wilayah</span>
                <span class="grid-val">${formatDecimal(props.luas_km2)} km²</span>
              </div>
              <div class="grid-item">
                <span class="grid-label">🏠 Jumlah Rumah</span>
                <span class="grid-val">${formatNumber(props.jumlah_rumah)} unit</span>
              </div>
              <div class="grid-item">
                <span class="grid-label">📊 Kategori</span>
                <span class="grid-val font-semibold">${props.cluster_label}</span>
              </div>
            </div>
          </div>
        </div>
      `
      layer.bindPopup(popupHtml, { maxWidth: 320, minWidth: 280, className: 'densimap-popup' })
    },
  }).addTo(map)

  defaultBounds = geoJsonLayer.getBounds()
  map.fitBounds(defaultBounds, { padding: [30, 30] })
}

// Handle Year selection change
const onYearChange = () => {
  panelYear.value = selectedYear.value
  loadData(selectedYear.value)
}

// Load data and setup view
const loadData = async (year = selectedYear.value) => {
  try {
    const result = await getKecamatanData(year)
    dataSource.value = result.source
    const fc = result.featureCollection

    // Reset visualization state when year changes
    visualizationDone.value = false

    // Extract list
    kecamatanList.value = fc.features.map((f) => f.properties)

    // Calculate cluster counts
    const counts = { Rendah: 0, Sedang: 0, Tinggi: 0 }
    kecamatanList.value.forEach((item) => {
      if (counts[item.cluster_label] !== undefined) {
        counts[item.cluster_label]++
      }
    })
    clusterCounts.value = counts

    // Capture metrics and stats
    clusteringMetrics.value = result.metrics || null
    clusterStats.value = result.clusterStats || null
    clusterTransitions.value = result.transitions || {}

    renderGeoJson(fc)
  } catch (err) {
    console.error('Failed to load kecamatan data:', err)
  }
}

// Select kecamatan from Search
const selectKecamatan = (item) => {
  searchQuery.value = item.nama
  isSearchOpen.value = false
  const layer = layerMap.get(item.id)
  if (layer) {
    map.fitBounds(layer.getBounds(), { maxZoom: 13, padding: [60, 60] })
    layer.openPopup()
  }
}

// Select from table modal
const selectKecamatanFromModal = (item) => {
  showTableModal.value = false
  selectKecamatan(item)
}

// Reset map bounds to entire Samarinda
const resetMapBounds = () => {
  if (map && defaultBounds) {
    map.closePopup()
    map.fitBounds(defaultBounds, { padding: [30, 30] })
  }
}

// Filter cluster highlighting
const toggleClusterFilter = (cluster) => {
  if (selectedClusterFilter.value === cluster) {
    selectedClusterFilter.value = null
  } else {
    selectedClusterFilter.value = cluster
  }

  if (geoJsonLayer) {
    geoJsonLayer.setStyle(polygonStyle)
  }
}

// Close search dropdown on outside click
const handleClickOutside = (e) => {
  if (searchContainerRef.value && !searchContainerRef.value.contains(e.target)) {
    isSearchOpen.value = false
  }
}

onMounted(() => {
  initMap()
  loadData()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (map) {
    map.remove()
  }
})
</script>

<style scoped>
.densimap-wrapper {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header Bar */
.top-header {
  position: absolute;
  top: 16px;
  left: 20px;
  right: 20px;
  height: 64px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(226, 232, 240, 0.85);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 1000;
  transition: all 0.2s ease;
}

.brand-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-text h1 {
  font-size: 16px;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.2;
}

.subtitle {
  font-size: 11px;
  color: #64748B;
  font-weight: 500;
  display: block;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* Search Box */
.search-container {
  position: relative;
  width: 260px;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  padding: 0 12px;
  height: 38px;
  transition: all 0.2s ease;
}

.search-input-wrapper:focus-within {
  background: #FFFFFF;
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.search-icon {
  width: 16px;
  height: 16px;
  color: #94A3B8;
  margin-right: 8px;
  flex-shrink: 0;
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  width: 100%;
  color: #0F172A;
  font-family: inherit;
}

.clear-search-btn {
  background: none;
  border: none;
  color: #94A3B8;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
}
.clear-search-btn:hover {
  color: #0F172A;
}

.search-dropdown {
  position: absolute;
  top: 44px;
  left: 0;
  right: 0;
  background: #FFFFFF;
  border-radius: var(--radius-md);
  border: 1px solid #E2E8F0;
  box-shadow: var(--shadow-float);
  max-height: 280px;
  overflow-y: auto;
  z-index: 1050;
  padding: 4px;
}

.search-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}

.search-item:hover {
  background: #F8FAFC;
}

.item-info {
  display: flex;
  flex-direction: column;
}

.item-name {
  font-size: 13px;
  font-weight: 600;
  color: #0F172A;
}

.item-density {
  font-size: 11px;
  color: #64748B;
}

/* Panel Toggle Button - Vertical rectangle on left edge */
.panel-toggle-btn {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1100;
  width: 44px;
  height: 140px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid #E2E8F0;
  border-left: none;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #334155;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-float);
}
.panel-toggle-btn:hover {
  background: #FFFFFF;
  box-shadow: 0 16px 40px -8px rgba(15, 23, 42, 0.18), 0 6px 16px -4px rgba(15, 23, 42, 0.1);
  width: 48px;
}
.panel-toggle-btn svg {
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* When panel is open, button moves to panel's right edge */
.left-panel.open ~ .panel-toggle-btn,
.panel-toggle-btn:has(+ .left-panel.open) {
  left: 50vw;
  max-width: 480px;
  left: calc(min(50vw, 480px));
}

/* Since we can't use :has() reliably, use a class on body or wrapper */
.densimap-wrapper.panel-open .panel-toggle-btn {
  left: calc(min(50vw, 480px));
}

/* Buttons and Badges */
.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  padding: 0 14px;
  height: 38px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.action-btn:hover {
  background: #F8FAFC;
  border-color: #CBD5E1;
  color: #0F172A;
}

/* Start Button - Opens Left Panel */
.start-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
  border: none;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  padding: 0 16px;
  height: 38px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
}

.start-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
  transform: translateY(-1px);
}

.start-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
}

.start-btn:disabled {
  background: #94A3B8;
  cursor: not-allowed;
  box-shadow: none;
  opacity: 0.7;
}

.start-btn svg {
  flex-shrink: 0;
}

/* Fullscreen Map */
.map-view {
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* Reset View Button */
.reset-view-btn {
  position: absolute;
  top: 96px;
  left: 20px;
  z-index: 990;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #1E293B;
  box-shadow: var(--shadow-subtle);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.reset-view-btn:hover {
  background: #FFFFFF;
  box-shadow: var(--shadow-float);
  transform: translateY(-1px);
}

/* Legend Panel (W-06) */
.legend-panel {
  position: absolute;
  bottom: 24px;
  left: 20px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(226, 232, 240, 0.85);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  padding: 16px;
  width: 260px;
  z-index: 990;
}

.legend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.legend-header h3 {
  font-size: 13px;
  font-weight: 700;
  color: #0F172A;
  margin: 0;
}

.legend-badge {
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 700;
  background: #F1F5F9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}

.legend-row:hover {
  background: #F1F5F9;
}

.legend-row.active {
  background: #E2E8F0;
  box-shadow: inset 0 0 0 1px #CBD5E1;
}

.legend-color-box {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.legend-color-box.high { background: #EF4444; }
.legend-color-box.mid { background: #F59E0B; }
.legend-color-box.low { background: #10B981; }

.legend-desc {
  display: flex;
  flex-direction: column;
}

.legend-desc .label {
  font-size: 12px;
  font-weight: 700;
  color: #0F172A;
}

.legend-desc .sublabel {
  font-size: 10px;
  color: #64748B;
}

.filter-reset-hint {
  margin-top: 8px;
  padding: 4px 6px;
  font-size: 11px;
  color: #2563EB;
  text-align: center;
  font-weight: 600;
  cursor: pointer;
  border-radius: 4px;
}
.filter-reset-hint:hover {
  background: #EFF6FF;
}

/* Metrics Section in Legend Panel */
.metrics-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #F1F5F9;
}

.metrics-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.metrics-header h4 {
  font-size: 12px;
  font-weight: 700;
  color: #0F172A;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metrics-badge {
  font-size: 9px;
  font-weight: 700;
  background: #EFF6FF;
  color: #2563EB;
  padding: 2px 6px;
  border-radius: 4px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.metric-card {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 10px 8px;
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 10px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 4px;
}

.metric-value {
  display: block;
  font-size: 16px;
  font-weight: 800;
  color: #0F172A;
  margin-bottom: 2px;
}

.metric-desc {
  display: block;
  font-size: 9px;
  color: #64748B;
}

.cluster-stats h5 {
  font-size: 11px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 10px 0;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cluster-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.cluster-stat-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 10px 8px;
}

.cluster-stat-card.stat-rendah { border-left: 3px solid #10B981; }
.cluster-stat-card.stat-sedang { border-left: 3px solid #F59E0B; }
.cluster-stat-card.stat-tinggi { border-left: 3px solid #EF4444; }

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #F1F5F9;
}

.stat-label {
  font-size: 11px;
  font-weight: 700;
  color: #0F172A;
}

.stat-count {
  font-size: 10px;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 6px;
  border-radius: 4px;
}

.stat-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 9px;
}

.stat-name {
  color: #64748B;
}

.stat-val {
  font-weight: 700;
  color: #0F172A;
}

.map-attribution {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #F1F5F9;
  font-size: 9px;
  color: #94A3B8;
  text-align: center;
  line-height: 1.4;
}
.map-attribution a {
  color: #64748B;
  text-decoration: none;
  transition: color 0.15s;
}
.map-attribution a:hover {
  color: #2563EB;
  text-decoration: underline;
}
.map-attribution span {
  margin: 0 4px;
}

.legend-footer {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #F1F5F9;
  font-size: 10px;
  color: #94A3B8;
  text-align: right;
}

/* Left Sliding Panel */
.left-panel {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  width: 50vw;
  max-width: 480px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(226, 232, 240, 0.85);
  box-shadow: var(--shadow-float);
  z-index: 1000;
  transform: translateX(-100%);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel.open {
  transform: translateX(0);
}

.left-panel-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  overflow-y: auto;
}

.left-panel-header {
  padding-bottom: 16px;
  border-bottom: 1px solid #F1F5F9;
  margin-bottom: 20px;
}

.left-panel-header h3 {
  font-size: 18px;
  font-weight: 800;
  color: #0F172A;
  margin: 0 0 4px 0;
}

.panel-subtitle {
  font-size: 13px;
  color: #64748B;
  font-weight: 500;
  margin: 0;
}

.left-panel-body {
  flex: 1;
  color: #334155;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.left-panel-body p {
  margin: 0 0 12px 0;
  font-size: 14px;
}

/* Panel Year Selector */
.panel-year-selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
}

.panel-year-selector label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.panel-year-select {
  padding: 8px 12px;
  border: 1px solid #CBD5E1;
  border-radius: var(--radius-sm);
  background: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  color: #0F172A;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
}
.panel-year-select:focus {
  outline: none;
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

/* Pipeline Flow */
.pipeline-flow {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipeline-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  position: relative;
  transition: all 0.2s ease;
}
.pipeline-step:hover {
  border-color: #CBD5E1;
  box-shadow: var(--shadow-subtle);
}

.step-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #2563EB, #3B82F6);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  margin-top: 2px;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-content h5 {
  font-size: 13px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 4px 0;
  line-height: 1.3;
}

.step-content p {
  font-size: 11px;
  color: #64748B;
  margin: 0;
  line-height: 1.4;
}

.step-detail {
  margin-top: 8px;
  padding: 8px 10px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  font-size: 10px;
  color: #475569;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  line-height: 1.5;
  white-space: pre-wrap;
}

.step-arrow {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  color: #94A3B8;
  font-size: 16px;
  font-weight: 700;
  margin-top: 4px;
}

/* Year Data Summary */
.year-data-summary {
  padding-top: 12px;
  border-top: 1px solid #F1F5F9;
}

.year-data-summary h4 {
  font-size: 13px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 12px 0;
}

.data-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.data-stat-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 10px 8px;
  text-align: center;
  transition: all 0.2s ease;
}
.data-stat-card:hover {
  border-color: #CBD5E1;
  box-shadow: var(--shadow-subtle);
}

.data-stat-label {
  display: block;
  font-size: 10px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 4px;
}

.data-stat-value {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #0F172A;
}

.cluster-breakdown h5 {
  font-size: 11px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cluster-breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cluster-breakdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}
.cluster-breakdown-item:hover {
  border-color: #CBD5E1;
}

.cluster-breakdown-item.breakdown-rendah { border-left: 3px solid #10B981; }
.cluster-breakdown-item.breakdown-sedang { border-left: 3px solid #F59E0B; }
.cluster-breakdown-item.breakdown-tinggi { border-left: 3px solid #EF4444; }

.breakdown-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}
.breakdown-color.rendah { background: #10B981; }
.breakdown-color.sedang { background: #F59E0B; }
.breakdown-color.tinggi { background: #EF4444; }

.breakdown-label {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  color: #0F172A;
}

.breakdown-count {
  font-size: 11px;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

/* Cluster Pills */
.cluster-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  text-transform: capitalize;
}

.pill-tinggi {
  background: #FEE2E2;
  color: #DC2626;
  border: 1px solid #FECACA;
}

.pill-sedang {
  background: #FEF3C7;
  color: #D97706;
  border: 1px solid #FDE68A;
}

.pill-rendah {
  background: #D1FAE5;
  color: #059669;
  border: 1px solid #A7F3D0;
}

/* Custom Popup Card (Leaflet) */
:deep(.custom-popup-card) {
  font-family: var(--font-main);
  background: #FFFFFF;
}

:deep(.popup-card-header) {
  padding: 14px 16px 10px 16px;
  border-bottom: 1px solid #F1F5F9;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

:deep(.popup-title) {
  font-size: 15px;
  font-weight: 800;
  color: #0F172A;
  min-width: 0;
}

:deep(.popup-badge) {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 10px;
}

:deep(.popup-badge.tinggi) { background: #FEE2E2; color: #DC2626; }
:deep(.popup-badge.sedang) { background: #FEF3C7; color: #D97706; }
:deep(.popup-badge.rendah) { background: #D1FAE5; color: #059669; }

:deep(.popup-card-body) {
  padding: 12px 16px 16px 16px;
}

:deep(.metric-highlight) {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
}

:deep(.metric-label) {
  font-size: 10px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
}

:deep(.metric-number) {
  font-size: 18px;
  font-weight: 800;
  color: #0F172A;
}

:deep(.metric-number small) {
  font-size: 12px;
  color: #64748B;
  font-weight: 500;
}

:deep(.popup-grid) {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

:deep(.grid-item) {
  display: flex;
  flex-direction: column;
}

:deep(.grid-label) {
  font-size: 10px;
  color: #64748B;
  font-weight: 500;
}

:deep(.grid-val) {
  font-size: 12px;
  color: #0F172A;
  font-weight: 700;
}

/* Modal Table View */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: #FFFFFF;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  width: 100%;
  max-width: 900px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

.modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-year-select {
  height: 36px;
  background: #FFFFFF;
}

.modal-summary-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-pill {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: 11px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.summary-value {
  font-size: 14px;
  font-weight: 700;
  color: #0F172A;
}

.summary-value.highlight {
  color: #2563EB;
}

.year-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #EFF6FF;
  color: #2563EB;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid #DBEAFE;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 800;
  color: #0F172A;
  margin: 0 0 4px 0;
}

.modal-header p {
  font-size: 12px;
  color: #64748B;
  margin: 0;
}

.close-modal-btn {
  background: #F1F5F9;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #64748B;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-modal-btn:hover {
  background: #E2E8F0;
  color: #0F172A;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  background: #F8FAFC;
  padding: 10px 14px;
  font-weight: 700;
  color: #475569;
  border-bottom: 2px solid #E2E8F0;
}

.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid #F1F5F9;
  color: #1E293B;
}

.data-table tr:hover td {
  background: #F8FAFC;
}

.text-right {
  text-align: right;
}

.font-bold {
  font-weight: 700;
}

.row-focus-btn {
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  color: #2563EB;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.row-focus-btn:hover {
  background: #2563EB;
  color: #FFFFFF;
}

/* Pipeline Step Interactive Styles */
.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  flex-wrap: wrap;
  gap: 8px;
}

.step-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  background: #F1F5F9;
  color: #64748B;
}
.step-status.completed {
  background: #D1FAE5;
  color: #059669;
}
.step-status.active {
  background: #EFF6FF;
  color: #2563EB;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.step-desc {
  font-size: 11px;
  color: #475569;
  margin: 0 0 4px 0;
}

.step-short {
  font-size: 10px;
  color: #94A3B8;
  margin: 0 0 10px 0;
  font-style: italic;
}

.step-run-btn {
  padding: 8px 14px;
  background: linear-gradient(135deg, #2563EB, #3B82F6);
  color: #FFFFFF;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
}
.step-run-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1D4ED8, #2563EB);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.4);
}
.step-run-btn:disabled {
  background: #94A3B8;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Step Result Styles */
.step-result {
  margin-top: 12px;
  padding: 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-md);
  animation: slideIn 0.3s ease;
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 8px;
}

.result-header h6 {
  font-size: 12px;
  font-weight: 700;
  color: #0F172A;
  margin: 0;
}

.result-summary {
  font-size: 10px;
  color: #64748B;
  background: #FFFFFF;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #E2E8F0;
}

/* Result Table */
.result-table-container {
  overflow-x: auto;
  margin-bottom: 10px;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}

.result-table th {
  background: #F1F5F9;
  padding: 6px 8px;
  font-weight: 700;
  color: #334155;
  border-bottom: 1px solid #E2E8F0;
  text-align: left;
  white-space: nowrap;
}

.result-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #F1F5F9;
  color: #1E293B;
}

.result-table tr:last-child td {
  border-bottom: none;
}

.result-table tr:hover td {
  background: #F1F5F9;
}

/* Formulas */
.result-formulas h6,
.result-stats h6,
.result-silhouette h6,
.result-clusters h6,
.result-metrics h6,
.result-visualization h6,
.result-interpretation h6,
.result-params h6 {
  font-size: 11px;
  font-weight: 700;
  color: #0F172A;
  margin: 10px 0 6px 0;
}

.result-formulas ul {
  margin: 0;
  padding-left: 16px;
  font-size: 10px;
  color: #475569;
  line-height: 1.6;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat-item {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 8px;
}

.stat-item .stat-label {
  display: block;
  font-size: 9px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.stat-item .stat-value {
  display: block;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  color: #0F172A;
  font-weight: 600;
}

/* Silhouette Bars */
.silhouette-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.silhouette-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.silhouette-bar .k-label {
  font-size: 10px;
  font-weight: 600;
  color: #334155;
  min-width: 36px;
}

.bar-container {
  flex: 1;
  height: 8px;
  background: #E2E8F0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #10B981, #34D399);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.score-value {
  font-size: 10px;
  font-weight: 700;
  color: #0F172A;
  min-width: 40px;
  text-align: right;
}

.silhouette-note {
  font-size: 9px;
  color: #94A3B8;
  margin: 6px 0 0 0 !important;
}

/* Cluster Detail Cards */
.clusters-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cluster-detail-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 10px;
  transition: all 0.2s ease;
}
.cluster-detail-card:hover {
  border-color: #CBD5E1;
  box-shadow: var(--shadow-subtle);
}

.cluster-detail-card.cluster-rendah { border-left: 3px solid #10B981; }
.cluster-detail-card.cluster-sedang { border-left: 3px solid #F59E0B; }
.cluster-detail-card.cluster-tinggi { border-left: 3px solid #EF4444; }

.cluster-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #F1F5F9;
}

.cluster-detail-label {
  font-size: 12px;
  font-weight: 700;
  color: #0F172A;
}

.cluster-detail-count {
  font-size: 10px;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.cluster-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
}
.metric-row span:first-child { color: #64748B; }
.metric-row span:last-child { color: #0F172A; font-weight: 600; }

.cluster-kecamatan {
  font-size: 10px;
  color: #475569;
}
.cluster-kecamatan strong { color: #334155; }

/* Metrics Grid Small */
.metrics-grid-small,
.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.metric-small,
.param-item {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  padding: 8px;
  text-align: center;
}

.metric-key,
.param-key {
  display: block;
  font-size: 9px;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.metric-val,
.param-val {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #0F172A;
}

/* Visualization */
.color-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.color-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: #334155;
}

.color-swatch {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(0,0,0,0.1);
  flex-shrink: 0;
}

.result-visualization ul {
  margin: 0;
  padding-left: 16px;
  font-size: 10px;
  color: #475569;
  line-height: 1.6;
}

/* Interpretation */
.interpretation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.interpretation-item {
  padding: 8px 10px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: var(--radius-sm);
  font-size: 10px;
  color: #334155;
  line-height: 1.5;
}

.interpretation-item.interp-rendah { border-left: 3px solid #10B981; }
.interpretation-item.interp-sedang { border-left: 3px solid #F59E0B; }
.interpretation-item.interp-tinggi { border-left: 3px solid #EF4444; }

/* Responsive adjustments */
@media (max-width: 768px) {
  .top-header {
    height: auto;
    flex-direction: column;
    padding: 12px;
    gap: 10px;
  }
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  .search-container {
    width: 100%;
  }
  .legend-panel {
    bottom: 12px;
    right: 12px;
    left: 12px;
    width: auto;
  }
}
</style>
