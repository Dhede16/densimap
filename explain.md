# Hubungan Hierarchical vs K-Means Silhouette & Toleransi Validasi (Dynamic k)

## Ringkasan Eksekutif (Data Real dari Pipeline 2-Fitur, Dynamic k)

| Tahun | Hierarchical Silhouette | K-Means Silhouette | Delta (Selisih) | Hierarchical Optimal k | K-Means n_clusters | K-Means DB Index |
|-------|------------------------|-------------------|-----------------|------------------------|-------------------|------------------|
| 2020  | 0.6386                 | 0.6386            | 0.0000          | 2                      | 2                 | 0.3289           |
| 2021  | 0.6400                 | 0.6400            | 0.0000          | 2                      | 2                 | 0.3279           |
| 2022  | 0.6421                 | 0.6421            | 0.0000          | 2                      | 2                 | 0.3277           |
| 2023  | 0.5472                 | 0.5472            | 0.0000          | 2                      | 2                 | 0.4656           |
| 2024  | 0.7131                 | 0.7131            | 0.0000          | 3                      | 3                 | 0.3312           |
| 2025  | 0.5478                 | 0.5478            | 0.0000          | 2                      | 2                 | 0.4655           |

**Kesimpulan**: 
- Delta = 0.0000 untuk semua tahun → **Kategori COCOK sempurna** (Hierarchical & K-Means sepakat)
- 2020-2023, 2025: optimal_k=2 → K-Means menggunakan **k=2 (Rendah, Tinggi)**
- 2024: optimal_k=3 → K-Means menggunakan **k=3 (Rendah, Sedang, Tinggi)**
- DB Index < 0.5 untuk semua tahun → **Sangat Baik** (klaster compact & terpisah)
- Silhouette 0.55–0.71 → **Cukup Baik hingga Sangat Kuat**

---

## Mengapa Membandingkan Keduanya?

| Aspek | Hierarchical (Ward) | K-Means |
|-------|---------------------|---------|
| Asumsi bentuk klaster | Tidak ada (non-parametric) | Spherical/bola, ukuran sama |
| Sensitivitas inisialisasi | Deterministik | Acak (mitigasi: `n_init=20`) |
| Output utama di project | **optimal_k suggestion** (validasi) | **Label akhir** (Rendah/Tinggi atau Rendah/Sedang/Tinggi) |

Jika keduanya **sepakat** (Delta ≈ 0) → struktur data memang natural, K-Means tidak memaksakan bentuk bola.
Jika **bertentangan** (Delta besar) → K-Means memaksakan asumsi yang tidak cocok.

> **Project ini (2 fitur, Dynamic k)**: Delta = 0.0000 untuk semua tahun → **Kategori COCOK sempurna**

---

## Toleransi / Threshold Validasi

### 1. Delta (Selisih Silhouette)

| Delta | Interpretasi | Tindakan |
|-------|--------------|----------|
| **< 0.05** | **COCOK** — Kedua algoritma sepakat, k valid | Lanjutkan |
| **0.05 – 0.15** | **WASPADA** — Ada perbedaan kecil, cek visual/klaster | Review manual |
| **> 0.15** | **TIDAK COCOK** — K-Means memaksakan bentuk bola | Coba k lain, atau pakai Hierarchical label |

> **Project ini**: Delta = 0.0000 → **Kategori COCOK sempurna** untuk semua tahun

### 2. Nilai Absolut Silhouette (Keduanya)

| Silhouette | Kualitas Klaster |
|------------|------------------|
| **> 0.70** | Sangat kuat, terpisah jelas |
| **0.50 – 0.70** | Cukup baik, terpisah wajar |
| **0.25 – 0.50** | Lemah, tumpang tindih signifikan |
| **< 0.25** | Tidak bermakna, acak |

> **Project ini**: 0.55–0.71 → **Cukup Baik hingga Sangat Kuat**

### 3. Davies-Bouldin Index (Hanya K-Means)

| DB Index | Interpretasi |
|----------|--------------|
| **< 0.5** | Sangat baik (klaster compact & terpisah) |
| **0.5 – 1.0** | Baik |
| **> 1.0** | Kurang baik |

> **Project ini**: 0.33–0.47 → **Sangat Baik** untuk semua tahun

---

## Decision Matrix Gabungan

```
┌─────────────────────────────────────────────────────────────┐
│  Silhouette > 0.5  DAN  Delta < 0.05  DAN  DB < 0.5        │
│                        ↓                                    │
│              ✅ k=optimal VALID & STABIL                    │
└─────────────────────────────────────────────────────────────┘
```

Project DensiMap **memenuhi ketiga kriteria** untuk semua tahun 2020–2025.

---

## Dynamic k Implementation

### Hierarchical Optimal k → K-Means n_clusters

Project ini menggunakan **Hierarchical Clustering (Ward) sebagai validator** untuk menentukan `optimal_k`, lalu menerapkannya langsung ke K-Means:

```python
# clustering.py
optimal_k, h_scores = find_optimal_k_hierarchical(X_scaled, max_k=5)
n_clusters = optimal_k  # Gunakan optimal_k dari hierarchical

kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
```

### Label Mapping Dinamis

| n_clusters | Label Mapping (berurutan by mean density) |
|------------|-------------------------------------------|
| 2          | `[0] → Rendah`, `[1] → Tinggi`           |
| 3          | `[0] → Rendah`, `[1] → Sedang`, `[2] → Tinggi` |
| >3         | `Cluster 1`, `Cluster 2`, ...             |

### Hasil per Tahun

| Tahun | optimal_k | Label Digunakan | Jumlah Kecamatan per Label |
|-------|-----------|-----------------|---------------------------|
| 2020  | 2         | Rendah, Tinggi  | 5 Rendah, 5 Tinggi        |
| 2021  | 2         | Rendah, Tinggi  | 5 Rendah, 5 Tinggi        |
| 2022  | 2         | Rendah, Tinggi  | 5 Rendah, 5 Tinggi        |
| 2023  | 2         | Rendah, Tinggi  | 5 Rendah, 5 Tinggi        |
| 2024  | 3         | Rendah, Sedang, Tinggi | 3 Rendah, 4 Sedang, 3 Tinggi |
| 2025  | 2         | Rendah, Tinggi  | 5 Rendah, 5 Tinggi        |

---

## Catatan Metodologis Penting

### Mengapa Dynamic k?
- **Data-driven**: Hierarchical Ward linkage memberikan `optimal_k` berdasarkan silhouette analysis
- **Konsisten**: Delta = 0.0000 membuktikan Hierarchical & K-Means **sepakat sepenuhnya** untuk semua tahun
- **Tanpa paksaan**: K-Means tidak memaksakan k=3 jika data naturalnya 2 klaster
- **Interpretabilitas**: 2024 adalah satu-satunya tahun dengan struktur 3 klaster alami (Silhouette 0.71)

### Fitur: 2 Fitur (kepadatan_penduduk, kepadatan_rumah)
- `rata_rata_penghuni` dihapus karena multikolinearitas sempurna dengan rasio dua kepadatan
- Hasil: Silhouette meningkat (0.40→0.64 untuk 2020-2022), DB Index turun (0.55→0.33)

### Data Quality Flags
- Tahun 2023-2025 memiliki anomali data (lonjakan >50% YoY)
- Flag `data_quality_flag` (clean/warning/suspect) ditambahkan ke GeoJSON output
- Clustering tetap valid (Delta=0) tapi interpretasi需谨慎

---

## Implementasi di Kode

```python
# clustering.py:214-238
features = ['kepadatan_penduduk', 'kepadatan_rumah']
X = df[features].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Hierarchical: suggest optimal k
optimal_k, h_scores = find_optimal_k_hierarchical(X_scaled, max_k=5)
n_clusters = optimal_k  # Dynamic!

hierarchical = AgglomerativeClustering(n_clusters=n_clusters, metric='euclidean', linkage='ward')
h_labels = hierarchical.fit_predict(X_scaled)
h_silhouette = silhouette_score(X_scaled, h_labels)

# K-Means dengan n_clusters = optimal_k
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
km_labels = kmeans.fit_predict(X_scaled)
km_silhouette = silhouette_score(X_scaled, km_labels)
km_db = davies_bouldin_score(X_scaled, km_labels)

# Dynamic label mapping
cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
cluster_order = list(cluster_densities.index)

if n_clusters == 2:
    label_map = {cluster_order[0]: 'Rendah', cluster_order[1]: 'Tinggi'}
elif n_clusters == 3:
    label_map = {cluster_order[0]: 'Rendah', cluster_order[1]: 'Sedang', cluster_order[2]: 'Tinggi'}
else:
    label_map = {cluster_order[i]: f'Cluster {i+1}' for i in range(n_clusters)}

df['cluster_label'] = df['raw_cluster'].map(label_map)
```

---

## Referensi Threshold (Literatur)

| Metrik | Sumber Threshold Umum |
|--------|----------------------|
| Silhouette | Kaufman & Rousseeuw (1990): >0.5 reasonable, >0.7 strong |
| Delta (stability) | Tibshirani & Walther (2005): Gap statistic stability; praktik industri <0.05–0.1 |
| Davies-Bouldin | Davies & Bouldin (1979): lower better, <0.5 excellent |

---

## FAQ

**Q: Kenapa tidak fix k=3 seperti versi sebelumnya?**
A: Hierarchical Ward linkage menyarankan optimal_k=2 untuk 5/6 tahun. Memaksa k=3 akan menciptakan klaster "Sedang" buatan yang tidak didukung struktur data. Delta=0 membuktikan k=2 valid.

**Q: Apakah 2024 benar-benar 3 klaster natural?**
A: Ya. 2024 memiliki optimal_k=3, Silhouette 0.7131 (Sangat Kuat), DB 0.33. Satu-satunya tahun dengan struktur 3 klaster alami.

**Q: Bagaimana frontend handle dynamic labels?**
A: Frontend menggunakan `currentClusterLabels` computed property yang mengekstrak label unik dari data tahun aktif, lalu generate warna & legend dinamis.

**Q: Jika nambah fitur, apakah optimal_k berubah?**
A: Bisa. Re-run validasi ini setiap kali fitur diubah. Multikolinearitas cenderung menurunkan kualitas cluster.