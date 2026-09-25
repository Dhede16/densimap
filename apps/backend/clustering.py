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

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# Paths - relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'apps', 'web', 'public', 'data')
DB_DIR = os.path.join(BASE_DIR, 'database')

PENDUDUK_FILE = os.path.join(DATA_DIR, 'jumlah-penduduk-berdasarakan-kecamatan.xlsx')
RUMAH_FILE = os.path.join(DATA_DIR, 'jumlah-rumah-berdasarkan-kecamatan.xlsx')
BOUNDARIES_CACHE_FILE = os.path.join(DATA_DIR, 'samarinda_boundaries.json')
OUTPUT_GEOJSON = os.path.join(OUTPUT_DIR, 'samarinda_kecamatan.json')
SCHEMA_SQL = os.path.join(DB_DIR, 'schema.sql')
SEED_SQL = os.path.join(DB_DIR, 'seed.sql')


def clean_kecamatan_name(val):
    s = str(val).upper()
    for name in LUAS_WILAYAH.keys():
        if name.upper() in s:
            return name
    return None


def fetch_boundary(name, cache_file=BOUNDARIES_CACHE_FILE):
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

    time.sleep(1.0)
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
        print('Supabase sync skipped: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY not configured.')
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
        print(f'Supabase updated: {len(rows)} rows upserted.')
        return True
    except Exception as error:
        raise RuntimeError(f'Failed to update Supabase: {error}') from error


def engineer_features(df):
    """Create derived features: density, house density, avg occupants per house."""
    df = df.copy()
    df['kepadatan_penduduk'] = df['jumlah_penduduk'] / df['luas_km2']
    df['kepadatan_rumah'] = df['jumlah_rumah'] / df['luas_km2']
    df['rata_rata_penghuni'] = df['jumlah_penduduk'] / df['jumlah_rumah']
    return df


def find_optimal_k_hierarchical(X_scaled, max_k=5):
    """Use hierarchical clustering to suggest optimal k via silhouette analysis."""
    best_k = 3
    best_score = -1
    scores = {}
    for k in range(2, max_k + 1):
        hierarchical = AgglomerativeClustering(n_clusters=k, metric='euclidean', linkage='ward')
        labels = hierarchical.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        scores[k] = score
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, scores


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
        geom = boundaries_cache.get(name) or fetch_boundary(name)
        records.append({
            'nama': name,
            'tahun': year,
            'jumlah_penduduk': penduduk,
            'luas_km2': luas,
            'jumlah_rumah': rumah,
            'geometry': geom
        })

    df = pd.DataFrame(records)
    df = engineer_features(df)

    features = ['kepadatan_penduduk', 'kepadatan_rumah', 'rata_rata_penghuni']
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Hierarchical: suggest optimal k (default to 3 if unclear)
    optimal_k, h_scores = find_optimal_k_hierarchical(X_scaled, max_k=5)
    n_clusters = 3  # Fixed per research design, but hierarchical validates

    hierarchical = AgglomerativeClustering(n_clusters=n_clusters, metric='euclidean', linkage='ward')
    h_labels = hierarchical.fit_predict(X_scaled)
    h_silhouette = silhouette_score(X_scaled, h_labels)
    h_db = davies_bouldin_score(X_scaled, h_labels)

    # K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    km_labels = kmeans.fit_predict(X_scaled)
    km_silhouette = silhouette_score(X_scaled, km_labels)
    km_db = davies_bouldin_score(X_scaled, km_labels)

    # Label clusters by mean population density order
    df['raw_cluster'] = km_labels
    cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
    cluster_order = list(cluster_densities.index)
    label_map = {
        cluster_order[0]: 'Rendah',
        cluster_order[1]: 'Sedang',
        cluster_order[2]: 'Tinggi'
    }
    df['cluster_label'] = df['raw_cluster'].map(label_map)

    # Per-cluster stats for interpretation
    cluster_stats = {}
    for label in ['Rendah', 'Sedang', 'Tinggi']:
        subset = df[df['cluster_label'] == label]
        cluster_stats[label] = {
            'count': int(len(subset)),
            'avg_kepadatan_penduduk': round(subset['kepadatan_penduduk'].mean(), 2),
            'avg_kepadatan_rumah': round(subset['kepadatan_rumah'].mean(), 2),
            'avg_rata_rata_penghuni': round(subset['rata_rata_penghuni'].mean(), 2),
            'kecamatan': subset['nama'].tolist()
        }

    metrics = {
        'hierarchical': {
            'silhouette': round(h_silhouette, 4),
            'davies_bouldin': round(h_db, 4),
            'optimal_k_suggestion': optimal_k,
            'silhouette_by_k': {str(k): round(v, 4) for k, v in h_scores.items()}
        },
        'kmeans': {
            'silhouette': round(km_silhouette, 4),
            'davies_bouldin': round(km_db, 4),
            'inertia': round(kmeans.inertia_, 4)
        },
        'features_used': features
    }

    print(f"Year {year}: H-Sil={h_silhouette:.4f} (k={optimal_k}), KM-Sil={km_silhouette:.4f}, DB={km_db:.4f}")
    return df, metrics, cluster_stats


def compute_cluster_transitions(all_dfs):
    """Track cluster changes across years for each kecamatan."""
    transitions = {}
    kecamatan_list = list(LUAS_WILAYAH.keys())
    for name in kecamatan_list:
        transitions[name] = {}
        for year in YEARS:
            row = all_dfs[year][all_dfs[year]['nama'] == name]
            if not row.empty:
                transitions[name][str(year)] = row.iloc[0]['cluster_label']
    return transitions


def run_pipeline():
    print("--- 1. Reading Input Data ---")
    df_penduduk = pd.read_excel(PENDUDUK_FILE)
    df_rumah = pd.read_excel(RUMAH_FILE)

    print("--- 2. Fetching/Caching Boundaries ---")
    boundaries_cache = {}
    for name in LUAS_WILAYAH.keys():
        boundaries_cache[name] = fetch_boundary(name)

    all_dfs = {}
    all_metrics = {}
    all_cluster_stats = {}
    by_year_geojson = {}

    for year in YEARS:
        df_year, metrics, cluster_stats = process_year_clustering(df_penduduk, df_rumah, year, boundaries_cache)
        all_dfs[year] = df_year
        all_metrics[str(year)] = metrics
        all_cluster_stats[str(year)] = cluster_stats

        features_geojson = []
        for idx, row in df_year.iterrows():
            feature = {
                "type": "Feature",
                "id": int(idx) + 1,
                "properties": {
                    "id": int(idx) + 1,
                    "nama": row['nama'],
                    "tahun": row['tahun'],
                    "jumlah_penduduk": row['jumlah_penduduk'],
                    "luas_km2": row['luas_km2'],
                    "jumlah_rumah": row['jumlah_rumah'],
                    "kepadatan_penduduk": round(row['kepadatan_penduduk'], 2),
                    "kepadatan_rumah": round(row['kepadatan_rumah'], 2),
                    "rata_rata_penghuni": round(row['rata_rata_penghuni'], 2),
                    "cluster_label": row['cluster_label']
                },
                "geometry": row['geometry']
            }
            features_geojson.append(feature)

        by_year_geojson[str(year)] = {
            "type": "FeatureCollection",
            "features": features_geojson
        }

    # Cross-year cluster transitions
    transitions = compute_cluster_transitions(all_dfs)

    print("\n--- 3. Saving Output Files ---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)

    # Multi-year GeoJSON with metrics
    output_geojson = {
        "years": YEARS,
        "default_year": 2025,
        "features": by_year_geojson["2025"]["features"],
        "type": "FeatureCollection",
        "by_year": by_year_geojson,
        "metrics": all_metrics,
        "cluster_stats": all_cluster_stats,
        "transitions": transitions
    }
    for y in YEARS:
        output_geojson[str(y)] = by_year_geojson[str(y)]

    with open(OUTPUT_GEOJSON, 'w', encoding='utf-8') as f:
        json.dump(output_geojson, f, indent=2, ensure_ascii=False)
    print(f"GeoJSON saved to {OUTPUT_GEOJSON}")

    # Schema SQL
    schema_sql = """-- DensiMap Schema for Supabase (PostgreSQL + PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.kecamatan (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    tahun INTEGER NOT NULL DEFAULT 2024,
    jumlah_penduduk INTEGER NOT NULL,
    luas_km2 NUMERIC(8, 2) NOT NULL,
    jumlah_rumah INTEGER NOT NULL,
    kepadatan_penduduk NUMERIC(10, 2) NOT NULL,
    kepadatan_rumah NUMERIC(10, 2) NOT NULL,
    rata_rata_penghuni NUMERIC(6, 2) NOT NULL,
    geometry JSONB NOT NULL,
    cluster_label VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(nama, tahun)
);

ALTER TABLE public.kecamatan ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read-only access" 
ON public.kecamatan 
FOR SELECT 
TO anon 
USING (true);
"""
    with open(SCHEMA_SQL, 'w', encoding='utf-8') as f:
        f.write(schema_sql)
    print(f"Schema SQL saved to {SCHEMA_SQL}")

    # Seed SQL
    seed_lines = ["-- Data Kecamatan Samarinda (2020-2025) dengan Hasil Klasterisasi\nTRUNCATE TABLE public.kecamatan;\n"]
    row_id = 1
    for year in YEARS:
        df_year = all_dfs[year]
        for _, row in df_year.iterrows():
            geom_json_str = json.dumps(row['geometry']).replace("'", "''")
            line = f"""INSERT INTO public.kecamatan (id, nama, tahun, jumlah_penduduk, luas_km2, jumlah_rumah, kepadatan_penduduk, kepadatan_rumah, rata_rata_penghuni, geometry, cluster_label)
VALUES ({row_id}, '{row['nama']}', {row['tahun']}, {row['jumlah_penduduk']}, {row['luas_km2']}, {row['jumlah_rumah']}, {row['kepadatan_penduduk']}, {row['kepadatan_rumah']}, {row['rata_rata_penghuni']}, '{geom_json_str}'::jsonb, '{row['cluster_label']}');"""
            seed_lines.append(line)
            row_id += 1

    with open(SEED_SQL, 'w', encoding='utf-8') as f:
        f.write('\n'.join(seed_lines))
    print(f"Seed SQL saved to {SEED_SQL}")

    sync_to_supabase(all_dfs)

    print("\n[OK] Multi-year clustering pipeline completed successfully!")
    return all_dfs[2025], all_metrics['2025'], all_dfs, all_metrics


if __name__ == '__main__':
    run_pipeline()