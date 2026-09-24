import os
import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

# BPS Luas Wilayah Kota Samarinda (km2)
LUAS_WILAYAH = {
    'Palaran': 221.29,
    'Samarinda Seberang': 12.49,
    'Samarinda Ulu': 22.12,
    'Samarinda Ilir': 17.18,
    'Samarinda Utara': 229.52,
    'Sungai Kunjang': 43.04,
    'Sambutan': 100.95,
    'Sungai Pinang': 34.16,
    'Samarinda Kota': 11.12,
    'Loa Janan Ilir': 26.13
}

def clean_kecamatan_name(val):
    s = str(val).upper()
    for name in LUAS_WILAYAH.keys():
        if name.upper() in s:
            return name
    return None

def fetch_boundary(name, cache_file=r'C:\Users\NITRO\code\densimap\data\samarinda_boundaries.json'):
    # Check cache first
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            if name in cache:
                return cache[name]
    else:
        cache = {}

    print(f"Fetching geometry for {name} from Nominatim...")
    q = f"{name}, Samarinda"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        'q': q,
        'format': 'geojson',
        'polygon_geojson': 1
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'DensiMap-Clustering/1.0 (academic)'})
    
    time.sleep(1.0) # rate limit courtesy
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            for feat in data.get('features', []):
                if feat.get('geometry', {}).get('type') in ['Polygon', 'MultiPolygon']:
                    cache[name] = feat.get('geometry')
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, indent=2)
                    return feat.get('geometry')
    except Exception as e:
        print(f"Error fetching {name}: {e}")

    return None

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

def load_backend_env():
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
    ]
    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue
        with open(env_path, 'r', encoding='utf-8') as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"\''))

def sync_to_supabase(all_dfs):
    load_backend_env()
    supabase_url = os.environ.get('SUPABASE_URL')
    access_token = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_ACCESS_TOKEN')
    if not supabase_url or not access_token:
        print('Supabase sync dilewati: SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY belum dikonfigurasi.')
        return False

    rows = []
    updated_at = datetime.now(timezone.utc).isoformat()
    for year in YEARS:
        for _, row in all_dfs[year].iterrows():
            rows.append({
                'nama': str(row['nama']),
                'tahun': int(row['tahun']),
                'jumlah_penduduk': int(row['jumlah_penduduk']),
                'luas_km2': float(row['luas_km2']),
                'jumlah_rumah': int(row['jumlah_rumah']),
                'kepadatan_penduduk': float(row['kepadatan_penduduk']),
                'geometry': row['geometry'],
                'cluster_label': str(row['cluster_label']),
                'updated_at': updated_at,
            })

    url = supabase_url.rstrip('/') + '/rest/v1/kecamatan?on_conflict=nama,tahun'
    request = urllib.request.Request(
        url,
        data=json.dumps(rows, ensure_ascii=False).encode('utf-8'),
        method='POST',
        headers={
            'apikey': access_token,
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates,return=minimal',
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError(f'HTTP {response.status}')
        print(f'Supabase berhasil diperbarui: {len(rows)} baris di-upsert.')
        return True
    except Exception as error:
        raise RuntimeError(f'Gagal memperbarui Supabase: {error}') from error

def process_year_clustering(df_penduduk, df_rumah, year, boundaries_cache):
    records = []
    penduduk_map = {}
    for _, row in df_penduduk.iterrows():
        name = clean_kecamatan_name(row.iloc[1])
        if name and name in LUAS_WILAYAH:
            penduduk_map[name] = int(row[year])

    rumah_map = {}
    for _, row in df_rumah.iterrows():
        name = clean_kecamatan_name(row.iloc[1])
        if name and name in LUAS_WILAYAH:
            rumah_map[name] = int(row[year])

    for name in LUAS_WILAYAH.keys():
        luas = LUAS_WILAYAH[name]
        penduduk = penduduk_map[name]
        rumah = rumah_map[name]
        kepadatan = round(penduduk / luas, 2)
        geom = boundaries_cache.get(name) or fetch_boundary(name)
        records.append({
            'nama': name,
            'tahun': year,
            'jumlah_penduduk': penduduk,
            'luas_km2': luas,
            'jumlah_rumah': rumah,
            'kepadatan_penduduk': kepadatan,
            'geometry': geom
        })

    df = pd.DataFrame(records)

    features = ['kepadatan_penduduk', 'luas_km2']
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Hierarchical Clustering (Ward)
    hierarchical = AgglomerativeClustering(n_clusters=3, metric='euclidean', linkage='ward')
    h_labels = hierarchical.fit_predict(X_scaled)
    h_silhouette = silhouette_score(X_scaled, h_labels)

    # K-Means Clustering (k=3)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=20)
    km_labels = kmeans.fit_predict(X_scaled)
    km_silhouette = silhouette_score(X_scaled, km_labels)
    km_db = davies_bouldin_score(X_scaled, km_labels)

    # Labeling Cluster berdasarkan Urutan Rata-rata Kepadatan Penduduk
    df['raw_cluster'] = km_labels
    cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
    cluster_order = list(cluster_densities.index)
    label_map = {
        cluster_order[0]: 'Rendah',
        cluster_order[1]: 'Sedang',
        cluster_order[2]: 'Tinggi'
    }
    df['cluster_label'] = df['raw_cluster'].map(label_map)

    print(f"Tahun {year}: Hierarchical Silhouette = {h_silhouette:.4f}, K-Means Silhouette = {km_silhouette:.4f}, Delta = {abs(h_silhouette - km_silhouette):.4f}, DB Index = {km_db:.4f}")
    return df, km_silhouette, h_silhouette

def run_pipeline():
    print("--- 1. Membaca Data Input ---")
    df_penduduk = pd.read_excel(r'C:\Users\NITRO\code\densimap\data\jumlah-penduduk-berdasarakan-kecamatan.xlsx')
    df_rumah = pd.read_excel(r'C:\Users\NITRO\code\densimap\data\jumlah-rumah-berdasarkan-kecamatan.xlsx')

    # Pre-fetch / cache boundaries for all 10 kecamatan
    boundaries_cache = {}
    for name in LUAS_WILAYAH.keys():
        boundaries_cache[name] = fetch_boundary(name)

    all_dfs = {}
    all_silhouettes = {}
    by_year_geojson = {}

    for year in YEARS:
        df_year, sil, h_sil = process_year_clustering(df_penduduk, df_rumah, year, boundaries_cache)
        all_dfs[year] = df_year
        all_silhouettes[year] = sil

        features_geojson = []
        for idx, row in df_year.iterrows():
            feature = {
                "type": "Feature",
                "id": idx + 1, # type: ignore
                "properties": {
                    "id": idx + 1, # type: ignore
                    "nama": row['nama'],
                    "tahun": row['tahun'],
                    "jumlah_penduduk": row['jumlah_penduduk'],
                    "luas_km2": row['luas_km2'],
                    "jumlah_rumah": row['jumlah_rumah'],
                    "kepadatan_penduduk": row['kepadatan_penduduk'],
                    "cluster_label": row['cluster_label']
                },
                "geometry": row['geometry']
            }
            features_geojson.append(feature)

        by_year_geojson[str(year)] = {
            "type": "FeatureCollection",
            "features": features_geojson
        }

    # --- Menyimpan File Output ---
    print("\n--- 2. Menyimpan File Output ---")
    os.makedirs('database', exist_ok=True)
    os.makedirs('apps/web/public/data', exist_ok=True)

    # A. Multi-year GeoJSON map data
    output_geojson = {
        "years": YEARS,
        "default_year": 2025,
        "features": by_year_geojson["2025"]["features"],
        "type": "FeatureCollection",
        "by_year": by_year_geojson
    }
    # Also add direct string keys for easy access: geojson["2020"]
    for y in YEARS:
        output_geojson[str(y)] = by_year_geojson[str(y)]

    json_path = r'C:\Users\NITRO\code\densimap\data\samarinda_boundaries.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_geojson, f, indent=2, ensure_ascii=False)
    print(f"GeoJSON tersimpan di {json_path}")

    # B. Schema SQL Supabase
    schema_sql = """-- Skema Basis Data DensiMap untuk Supabase (PostgreSQL + PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.kecamatan (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    tahun INTEGER NOT NULL DEFAULT 2024,
    jumlah_penduduk INTEGER NOT NULL,
    luas_km2 NUMERIC(8, 2) NOT NULL,
    jumlah_rumah INTEGER NOT NULL,
    kepadatan_penduduk NUMERIC(10, 2) NOT NULL,
    geometry JSONB NOT NULL,
    cluster_label VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(nama, tahun)
);

-- Row Level Security (RLS)
ALTER TABLE public.kecamatan ENABLE ROW LEVEL SECURITY;

-- Allow anon read-only SELECT
CREATE POLICY "Allow public read-only access" 
ON public.kecamatan 
FOR SELECT 
TO anon 
USING (true);
"""
    with open('database/schema.sql', 'w', encoding='utf-8') as f:
        f.write(schema_sql)
    print("Skema SQL tersimpan di database/schema.sql")

    # C. Seed SQL Supabase
    seed_lines = ["-- Data Kecamatan Samarinda (2020-2025) dengan Hasil Klasterisasi\nTRUNCATE TABLE public.kecamatan;\n"]
    row_id = 1
    for year in YEARS:
        df_year = all_dfs[year]
        for _, row in df_year.iterrows():
            geom_json_str = json.dumps(row['geometry']).replace("'", "''")
            line = f"""INSERT INTO public.kecamatan (id, nama, tahun, jumlah_penduduk, luas_km2, jumlah_rumah, kepadatan_penduduk, geometry, cluster_label)
VALUES ({row_id}, '{row['nama']}', {row['tahun']}, {row['jumlah_penduduk']}, {row['luas_km2']}, {row['jumlah_rumah']}, {row['kepadatan_penduduk']}, '{geom_json_str}'::jsonb, '{row['cluster_label']}');"""
            seed_lines.append(line)
            row_id += 1

    with open('database/seed.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(seed_lines))
    print("Seed SQL tersimpan di database/seed.sql")

    sync_to_supabase(all_dfs)

    print("\nProses clustering multi-tahun selesai dengan sukses!")
    return all_dfs[2025], all_silhouettes[2025], all_dfs, all_silhouettes

if __name__ == '__main__':
    run_pipeline()
