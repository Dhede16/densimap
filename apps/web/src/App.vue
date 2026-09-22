<template>
  <div class="densimap-wrapper">
    <!-- Top Header Bar -->
    <header class="top-header">
      <div class="brand-section">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
            <line x1="8" y1="2" x2="8" y2="18"></line>
            <line x1="16" y1="6" x2="16" y2="22"></line>
          </svg>
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

        <!-- Supabase Connection Indicator -->
        <div class="data-source-badge" :class="dataSource === 'supabase' ? 'badge-live' : 'badge-local'">
          <span class="status-dot"></span>
          <span>{{ dataSource === 'supabase' ? 'Supabase Live' : 'Data Lokal (Offline)' }}</span>
        </div>
      </div>
    </header>

    <!-- Interactive Map Container -->
    <div id="map-view" class="map-view"></div>

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

      <div class="legend-footer">
        <span>Basemap: {{ mapboxActive ? 'Mapbox Light 2D' : 'CartoDB Positron 2D' }}</span>
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
          <button class="close-modal-btn" @click="showTableModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Kecamatan</th>
                  <th>Klaster</th>
                  <th class="text-right">Penduduk (2024)</th>
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
const searchQuery = ref('')
const isSearchOpen = ref(false)
const searchContainerRef = ref(null)
const dataSource = ref('local')
const mapboxActive = ref(false)
const showTableModal = ref(false)
const selectedClusterFilter = ref(null)

const kecamatanList = ref([])
const clusterCounts = ref({ Rendah: 0, Sedang: 0, Tinggi: 0 })

let map = null
let geoJsonLayer = null
let defaultBounds = null
const layerMap = new Map()

// Format helpers
const formatNumber = (val) => new Intl.NumberFormat('id-ID').format(val)
const formatDecimal = (val) => new Intl.NumberFormat('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)

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
    attributionControl: true,
  })

  // Leaflet Zoom Control (+ / -) di kanan bawah
  L.control.zoom({ position: 'bottomright' }).addTo(map)

  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN
  if (mapboxToken) {
    mapboxActive.value = true
    L.tileLayer(`https://api.mapbox.com/styles/v1/mapbox/light-v11/tiles/{z}/{x}/{y}?access_token=${mapboxToken}`, {
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

// Load data and setup view
const loadData = async () => {
  try {
    const result = await getKecamatanData()
    dataSource.value = result.source
    const fc = result.featureCollection

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
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
}

.logo-icon svg {
  width: 20px;
  height: 20px;
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

.data-source-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
}

.data-source-badge.badge-live {
  background: #ECFDF5;
  color: #059669;
  border: 1px solid #A7F3D0;
}
.data-source-badge.badge-local {
  background: #F1F5F9;
  color: #475569;
  border: 1px solid #E2E8F0;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
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
  right: 20px;
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

.legend-footer {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #F1F5F9;
  font-size: 10px;
  color: #94A3B8;
  text-align: right;
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
  justify-content: space-between;
}

:deep(.popup-title) {
  font-size: 15px;
  font-weight: 800;
  color: #0F172A;
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
  align-items: flex-start;
  justify-content: space-between;
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
