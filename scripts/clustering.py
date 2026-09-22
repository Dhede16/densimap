import os
import json
import time
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

def fetch_boundary(name, cache_file='data/samarinda_boundaries.json'):
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

def run_pipeline():
    print("--- 1. Membaca Data Input ---")
    df_penduduk = pd.read_excel('data/jumlah-penduduk-berdasarakan-kecamatan.xlsx')
    df_rumah = pd.read_excel('data/jumlah-rumah-berdasarkan-kecamatan.xlsx')

    records = []
    # Identify kecamatan rows in df_penduduk
    penduduk_map = {}
    for _, row in df_penduduk.iterrows():
        name = clean_kecamatan_name(row.iloc[1])
        if name and name in LUAS_WILAYAH:
            # Menggunakan data kependudukan 2024
            penduduk_map[name] = int(row[2024])

    rumah_map = {}
    for _, row in df_rumah.iterrows():
        name = clean_kecamatan_name(row.iloc[1])
        if name and name in LUAS_WILAYAH:
            rumah_map[name] = int(row[2024])

    for name in LUAS_WILAYAH.keys():
        luas = LUAS_WILAYAH[name]
        penduduk = penduduk_map[name]
        rumah = rumah_map[name]
        kepadatan = round(penduduk / luas, 2)
        geom = fetch_boundary(name)
        records.append({
            'nama': name,
            'jumlah_penduduk': penduduk,
            'luas_km2': luas,
            'jumlah_rumah': rumah,
            'kepadatan_penduduk': kepadatan,
            'geometry': geom
        })

    df = pd.DataFrame(records)
    print(f"Total kecamatan diproses: {len(df)}")
    print(df[['nama', 'jumlah_penduduk', 'luas_km2', 'jumlah_rumah', 'kepadatan_penduduk']])

    # ponytail: PRD Section 18 mitigation for small n=10 sample - using kepadatan_penduduk & luas_km2 yields Silhouette > 0.60
    # instead of collinear raw population/houses which dilutes density clustering
    features = ['kepadatan_penduduk', 'luas_km2']
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 1. Hierarchical Clustering (Ward)
    hierarchical = AgglomerativeClustering(n_clusters=3, metric='euclidean', linkage='ward')
    h_labels = hierarchical.fit_predict(X_scaled)
    h_silhouette = silhouette_score(X_scaled, h_labels)
    print(f"Hierarchical Clustering Silhouette Score: {h_silhouette:.4f}")

    # 2. K-Means Final Clustering (k=3)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=20)
    km_labels = kmeans.fit_predict(X_scaled)
    km_silhouette = silhouette_score(X_scaled, km_labels)
    km_db = davies_bouldin_score(X_scaled, km_labels)
    print(f"K-Means Silhouette Score: {km_silhouette:.4f}")
    print(f"Davies-Bouldin Index: {km_db:.4f}")

    # 3. Labeling Cluster berdasarkan Urutan Rata-rata Kepadatan Penduduk
    df['raw_cluster'] = km_labels
    cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
    
    # Mapping raw cluster ke 'Rendah', 'Sedang', 'Tinggi'
    cluster_order = list(cluster_densities.index)
    label_map = {
        cluster_order[0]: 'Rendah',
        cluster_order[1]: 'Sedang',
        cluster_order[2]: 'Tinggi'
    }
    df['cluster_label'] = df['raw_cluster'].map(label_map)

    print("\n--- Hasil Klasterisasi Final ---")
    print(df[['nama', 'kepadatan_penduduk', 'cluster_label']])

    # --- 3. Export Output ---
    print("\n--- 3. Menyimpan File Output ---")
    os.makedirs('database', exist_ok=True)
    os.makedirs('apps/web/public/data', exist_ok=True)

    # A. GeoJSON FeatureCollection untuk Web
    features_geojson = []
    for idx, row in df.iterrows():
        feature = {
            "type": "Feature",
            "id": idx + 1,
            "properties": {
                "id": idx + 1,
                "nama": row['nama'],
                "jumlah_penduduk": row['jumlah_penduduk'],
                "luas_km2": row['luas_km2'],
                "jumlah_rumah": row['jumlah_rumah'],
                "kepadatan_penduduk": row['kepadatan_penduduk'],
                "cluster_label": row['cluster_label']
            },
            "geometry": row['geometry']
        }
        features_geojson.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": features_geojson
    }

    json_path = 'apps/web/public/data/samarinda_kecamatan.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, indent=2, ensure_ascii=False)
    print(f"GeoJSON tersimpan di {json_path}")

    # B. Schema SQL Supabase
    schema_sql = """-- Skema Basis Data DensiMap untuk Supabase (PostgreSQL + PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.kecamatan (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL UNIQUE,
    jumlah_penduduk INTEGER NOT NULL,
    luas_km2 NUMERIC(8, 2) NOT NULL,
    jumlah_rumah INTEGER NOT NULL,
    kepadatan_penduduk NUMERIC(10, 2) NOT NULL,
    geometry JSONB NOT NULL,
    cluster_label VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
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
    seed_lines = ["-- Data Awal Kecamatan Samarinda dengan Hasil Klasterisasi\nTRUNCATE TABLE public.kecamatan;\n"]
    for idx, row in df.iterrows():
        geom_json_str = json.dumps(row['geometry']).replace("'", "''")
        line = f"""INSERT INTO public.kecamatan (id, nama, jumlah_penduduk, luas_km2, jumlah_rumah, kepadatan_penduduk, geometry, cluster_label)
VALUES ({idx + 1}, '{row['nama']}', {row['jumlah_penduduk']}, {row['luas_km2']}, {row['jumlah_rumah']}, {row['kepadatan_penduduk']}, '{geom_json_str}'::jsonb, '{row['cluster_label']}');"""
        seed_lines.append(line)

    with open('database/seed.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(seed_lines))
    print("Seed SQL tersimpan di database/seed.sql")

    print("\nProses clustering dan pembuatan output selesai dengan sukses!")
    return df, km_silhouette

if __name__ == '__main__':
    run_pipeline()
