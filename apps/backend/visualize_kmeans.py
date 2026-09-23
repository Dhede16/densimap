import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Styling
sns.set_style("whitegrid")
sns.set_context("talk", font_scale=1.1)
plt.rcParams['font.family'] = 'DejaVu Sans'

# Paths
OUTPUT_DIR = r'C:\Users\NITRO\code\densimap\output'
DATA_DIR = r'C:\Users\NITRO\code\densimap\data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BPS Luas Wilayah
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

CLUSTER_COLORS = {'Rendah': '#10B981', 'Sedang': '#F59E0B', 'Tinggi': '#EF4444'}
CLUSTER_ORDER = ['Rendah', 'Sedang', 'Tinggi']

def clean_kecamatan_name(val):
    s = str(val).upper()
    for name in LUAS_WILAYAH.keys():
        if name.upper() in s:
            return name
    return None

def load_and_prepare(year):
    df_penduduk = pd.read_excel(os.path.join(DATA_DIR, 'jumlah-penduduk-berdasarakan-kecamatan.xlsx'))
    df_rumah = pd.read_excel(os.path.join(DATA_DIR, 'jumlah-rumah-berdasarkan-kecamatan.xlsx'))

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

    records = []
    for name in LUAS_WILAYAH.keys():
        luas = LUAS_WILAYAH[name]
        penduduk = penduduk_map[name]
        rumah = rumah_map[name]
        kepadatan = round(penduduk / luas, 2)
        records.append({
            'nama': name,
            'tahun': year,
            'jumlah_penduduk': penduduk,
            'luas_km2': luas,
            'jumlah_rumah': rumah,
            'kepadatan_penduduk': kepadatan,
        })

    return pd.DataFrame(records)

def run_kmeans_and_plot(df, year):
    features = ['kepadatan_penduduk', 'luas_km2']
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=20)
    labels = kmeans.fit_predict(X_scaled)

    # Map labels by mean density
    df['raw_cluster'] = labels
    cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
    cluster_order = list(cluster_densities.index)
    label_map = {
        cluster_order[0]: 'Rendah',
        cluster_order[1]: 'Sedang',
        cluster_order[2]: 'Tinggi'
    }
    df['cluster_label'] = df['raw_cluster'].map(label_map)

    # --- Plot 1: Scatter in original feature space ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Left: Original space
    ax = axes[0]
    for label in CLUSTER_ORDER:
        subset = df[df['cluster_label'] == label]
        ax.scatter(
            subset['luas_km2'], subset['kepadatan_penduduk'],
            c=CLUSTER_COLORS[label], label=label,
            s=180, edgecolor='white', linewidth=1.5, alpha=0.9, zorder=3
        )
        # Annotate kecamatan names
        for _, row in subset.iterrows():
            ax.annotate(row['nama'], (row['luas_km2'], row['kepadatan_penduduk']),
                        fontsize=9, ha='center', va='bottom', fontweight='medium',
                        xytext=(0, 5), textcoords='offset points')

    ax.set_xlabel('Luas Wilayah (km²)', fontweight='bold')
    ax.set_ylabel('Kepadatan Penduduk (jiwa/km²)', fontweight='bold')
    ax.set_title(f'K-Means Clusters — Original Space ({year})', fontweight='bold', pad=15)
    ax.legend(title='Klaster', frameon=True, fancybox=True, shadow=True)
    ax.grid(True, alpha=0.3)

    # Right: Scaled space (what K-Means actually sees)
    ax = axes[1]
    scaled_df = pd.DataFrame(X_scaled, columns=['kepadatan_scaled', 'luas_scaled'])
    scaled_df['cluster_label'] = df['cluster_label'].values
    scaled_df['nama'] = df['nama'].values

    for label in CLUSTER_ORDER:
        subset = scaled_df[scaled_df['cluster_label'] == label]
        ax.scatter(
            subset['luas_scaled'], subset['kepadatan_scaled'],
            c=CLUSTER_COLORS[label], label=label,
            s=180, edgecolor='white', linewidth=1.5, alpha=0.9, zorder=3
        )
        for _, row in subset.iterrows():
            ax.annotate(row['nama'], (row['luas_scaled'], row['kepadatan_scaled']),
                        fontsize=9, ha='center', va='bottom', fontweight='medium',
                        xytext=(0, 5), textcoords='offset points')

    # Plot centroids
    centroids = kmeans.cluster_centers_
    centroid_order = [cluster_order.index(i) for i in range(3)]  # map to sorted order
    for idx, label in enumerate(CLUSTER_ORDER):
        centroid_idx = centroid_order[idx]
        ax.scatter(
            centroids[centroid_idx, 1], centroids[centroid_idx, 0],
            c=CLUSTER_COLORS[label], marker='X', s=350,
            edgecolor='black', linewidth=2, zorder=5,
            label=f'Centroid {label}'
        )

    ax.set_xlabel('Luas (Standardized)', fontweight='bold')
    ax.set_ylabel('Kepadatan (Standardized)', fontweight='bold')
    ax.set_title(f'K-Means Clusters — Standardized Space ({year})', fontweight='bold', pad=15)
    ax.legend(title='Klaster', frameon=True, fancybox=True, shadow=True)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, f'kmeans_scatter_{year}.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {out_path}')

    # --- Plot 2: Pairplot-style with density contours ---
    fig, ax = plt.subplots(figsize=(10, 8))
    
    for label in CLUSTER_ORDER:
        subset = df[df['cluster_label'] == label]
        sns.kdeplot(
            x=subset['luas_km2'], y=subset['kepadatan_penduduk'],
            ax=ax, fill=True, alpha=0.2, color=CLUSTER_COLORS[label],
            levels=4, thresh=0.05, linewidth=0
        )
        ax.scatter(
            subset['luas_km2'], subset['kepadatan_penduduk'],
            c=CLUSTER_COLORS[label], label=label,
            s=200, edgecolor='white', linewidth=1.5, alpha=1.0, zorder=3
        )
        for _, row in subset.iterrows():
            ax.annotate(row['nama'], (row['luas_km2'], row['kepadatan_penduduk']),
                        fontsize=10, ha='center', va='bottom', fontweight='bold',
                        xytext=(0, 6), textcoords='offset points')

    ax.set_xlabel('Luas Wilayah (km²)', fontweight='bold', fontsize=13)
    ax.set_ylabel('Kepadatan Penduduk (jiwa/km²)', fontweight='bold', fontsize=13)
    ax.set_title(f'K-Means Clustering with Density Contours — {year}', fontweight='bold', fontsize=15, pad=20)
    ax.legend(title='Klaster', fontsize=11, title_fontsize=12, frameon=True, fancybox=True, shadow=True)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path2 = os.path.join(OUTPUT_DIR, f'kmeans_density_{year}.png')
    plt.savefig(out_path2, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {out_path2}')

    return df

def main():
    print('Generating K-Means scatter plots for all years...')
    print(f'Output directory: {OUTPUT_DIR}\n')

    for year in YEARS:
        print(f'--- Processing {year} ---')
        df = load_and_prepare(year)
        df = run_kmeans_and_plot(df, year)

    print(f'\nAll plots saved to: {OUTPUT_DIR}')
    print('Files:')
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.png'):
            print(f'  {f}')

if __name__ == '__main__':
    main()