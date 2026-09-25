import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null

let cachedLocalData = null

/**
 * Mengambil data kecamatan berdasarkan tahun (2020 - 2025) dari Supabase jika dikonfigurasi,
 * atau fallback ke data lokal GeoJSON jika offline / belum disetup.
 */
export async function getKecamatanData(year = 2024) {
  const targetYear = Number(year) || 2024

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('kecamatan')
        .select('*')
        .eq('tahun', targetYear)
        .order('id', { ascending: true })

      if (!error && data && data.length > 0) {
        const features = data.map((item) => {
          let geom = item.geometry
          if (typeof geom === 'string') {
            try {
              geom = JSON.parse(geom)
            } catch {
              geom = null
            }
          }
          return {
            type: 'Feature',
            id: item.id,
            properties: {
              id: item.id,
              nama: item.nama,
              tahun: item.tahun || targetYear,
              jumlah_penduduk: item.jumlah_penduduk,
              luas_km2: Number(item.luas_km2),
              jumlah_rumah: item.jumlah_rumah,
              kepadatan_penduduk: Number(item.kepadatan_penduduk),
              kepadatan_rumah: Number(item.kepadatan_rumah),
              rata_rata_penghuni: Number(item.rata_rata_penghuni),
              cluster_label: item.cluster_label,
            },
            geometry: geom,
          }
        })

        return {
          source: 'supabase',
          year: targetYear,
          featureCollection: {
            type: 'FeatureCollection',
            features,
          },
        }
      }
      console.warn('Supabase fetch failed or empty, fallback to local GeoJSON:', error)
    } catch (err) {
      console.warn('Supabase connection exception, fallback to local GeoJSON:', err)
    }
  }

  if (!cachedLocalData) {
    const res = await fetch('/data/samarinda_kecamatan.json')
    if (!res.ok) {
      throw new Error(`Gagal memuat data lokal: ${res.statusText}`)
    }
    cachedLocalData = await res.json()
  }

  const fc =
    cachedLocalData.by_year?.[String(targetYear)] ||
    cachedLocalData[String(targetYear)] ||
    cachedLocalData

  return {
    source: 'local',
    year: targetYear,
    featureCollection: fc,
    metrics: cachedLocalData.metrics?.[String(targetYear)],
    clusterStats: cachedLocalData.cluster_stats?.[String(targetYear)],
    transitions: cachedLocalData.transitions,
  }
}

