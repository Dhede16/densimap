import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null

/**
 * Mengambil data kecamatan dari Supabase jika dikonfigurasi,
 * atau fallback ke data lokal GeoJSON jika offline / belum disetup.
 */
export async function getKecamatanData() {
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('kecamatan')
        .select('*')
        .order('id', { ascending: true })

      if (!error && data && data.length > 0) {
        // Format PostGIS geometry / jsonb ke standard GeoJSON FeatureCollection
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
              jumlah_penduduk: item.jumlah_penduduk,
              luas_km2: Number(item.luas_km2),
              jumlah_rumah: item.jumlah_rumah,
              kepadatan_penduduk: Number(item.kepadatan_penduduk),
              cluster_label: item.cluster_label,
            },
            geometry: geom,
          }
        })

        return {
          source: 'supabase',
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

  // Fallback ke file lokal public/data/samarinda_kecamatan.json
  const res = await fetch('/data/samarinda_kecamatan.json')
  if (!res.ok) {
    throw new Error(`Gagal memuat data lokal: ${res.statusText}`)
  }
  const localData = await res.json()
  return {
    source: 'local',
    featureCollection: localData,
  }
}
