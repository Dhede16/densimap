let cachedData = null

/**
 * Mengambil data kecamatan berdasarkan tahun (2020 - 2025) dari GeoJSON lokal.
 * Data sudah termasuk metrics, cluster stats, dan transitions yang di-pre-compute oleh backend pipeline.
 */
export async function getKecamatanData(year = 2024) {
  const targetYear = Number(year) || 2024

  if (!cachedData) {
    const res = await fetch('/data/samarinda_kecamatan.json')
    if (!res.ok) {
      throw new Error(`Gagal memuat data lokal: ${res.statusText}`)
    }
    cachedData = await res.json()
  }

  const filteredFeatures = cachedData.features.filter(f => f.properties.tahun === targetYear)

  const fc = {
    type: 'FeatureCollection',
    features: filteredFeatures
  }

  return {
    source: 'local',
    year: targetYear,
    featureCollection: fc,
    metrics: cachedData.metrics?.[String(targetYear)],
    clusterStats: cachedData.cluster_stats?.[String(targetYear)],
    transitions: cachedData.transitions,
  }
}