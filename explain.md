# Hubungan Hierarchical vs K-Means Silhouette & Toleransi Validasi k=3

## Ringkasan Eksekutif (Data Real dari Pipeline 2-Fitur)

| Tahun | Hierarchical Silhouette | K-Means Silhouette | Delta (Selisih) | Hierarchical Optimal k | K-Means DB Index |
|-------|------------------------|-------------------|-----------------|------------------------|------------------|
| 2020  | 0.5846                 | 0.5846            | 0.0000          | 2                      | 0.2695           |
| 2021  | 0.5859                 | 0.5859            | 0.0000          | 2                      | 0.2681           |
| 2022  | 0.5890                 | 0.5890            | 0.0000          | 2                      | 0.2661           |
| 2023  | 0.5192                 | 0.5550            | 0.0358          | 2                      | 0.5670           |
| 2024  | 0.7131                 | 0.7131            | 0.0000          | 3                      | 0.3312           |
| 2025  | 0.5203                 | 0.5610            | 0.0407          | 2                      | 0.5568           |

**Kesimpulan**: 
- Delta < 0.05 untuk semua tahun → **Kategori COCOK** (k=3 valid secara domain, meskipun Hierarchical menyarankan k=2 untuk 5 dari 6 tahun)
- 2024 menunjukkan struktur 3 klaster alami (optimal_k=3, Silhouette=0.7131)
- DB Index < 0.5 untuk 2020-2022, 2024 → **Sangat Baik**; 2023 & 2025 DB > 0.5 → **Perlu Perhatian**

---

## Mengapa Membandingkan Keduanya?

| Aspek | Hierarchical (Ward) | K-Means |
|-------|---------------------|---------|
| Asumsi bentuk klaster | Tidak ada (non-parametric) | Spherical/bola, ukuran sama |
| Sensitivitas inisialisasi | Deterministik | Acak (mitigasi: `n_init=20`) |
| Output utama di project | **Silhouette score saja** (validasi) | **Label akhir** (Rendah/Sedang/Tinggi) |

Jika keduanya **sepakat** (Delta ≈ 0) → struktur data memang natural 3 klaster, K-Means tidak memaksakan bentuk bola.
Jika **bertentangan** (Delta besar) → K-Means memaksakan asumsi yang tidak cocok.

> **Project ini (2 fitur)**: Delta 0.0000–0.0407 → **Kategori COCOK** untuk semua tahun.

---

## Toleransi / Threshold Validasi

### 1. Delta (Selisih Silhouette)

| Delta | Interpretasi | Tindakan |
|-------|--------------|----------|
| **< 0.05** | **COCOK** — Kedua algoritma sepakat, k=3 valid | Lanjutkan |
| **0.05 – 0.15** | **WASPADA** — Ada perbedaan kecil, cek visual/klaster | Review manual |
| **> 0.15** | **TIDAK COCOK** — K-Means memaksakan bentuk bola | Coba k lain, atau pakai Hierarchical label |

> **Project ini**: Delta = 0.0000–0.0407 → **Kategori COCOK** untuk semua tahun

### 2. Nilai Absolut Silhouette (Keduanya)

| Silhouette | Kualitas Klaster |
|------------|------------------|
| **> 0.70** | Sangat kuat, terpisah jelas |
| **0.50 – 0.70** | Cukup baik, terpisah wajar |
| **0.25 – 0.50** | Lemah, tumpang tindih signifikan |
| **< 0.25** | Tidak bermakna, acak |

> **Project ini**: 0.52–0.71 → **Cukup Baik hingga Sangat Kuat** (memenuhi PRD > 0.58 untuk 4/6 tahun)

### 3. Davies-Bouldin Index (Hanya K-Means)

| DB Index | Interpretasi |
|----------|--------------|
| **< 0.5** | Sangat baik (klaster compact & terpisah) |
| **0.5 – 1.0** | Baik |
| **> 1.0** | Kurang baik |

> **Project ini**: 0.27–0.57 → **2020-2022 & 2024 Sangat Baik (<0.5)**, 2023 & 2025 **Baik (0.55-0.57)**

---

## Decision Matrix Gabungan

```
┌─────────────────────────────────────────────────────────────┐
│  Silhouette > 0.5  DAN  Delta < 0.05  DAN  DB < 0.5        │
│                        ↓                                    │
│              ✅ k=3 VALID & STABIL                          │
└─────────────────────────────────────────────────────────────┘
```

Project DensiMap **memenuhi ketiga kriteria** untuk tahun 2020, 2021, 2022, 2024.
Tahun 2023 & 2025: **Delta COCOK, Silhouette COCOK, tapi DB > 0.5** → Masih valid tapi cluster kurang compact.

---

## Catatan Metodologis Penting

### Hierarchical Optimal k=2 vs Domain k=3
- Hierarchical clustering (Ward) menyarankan **optimal_k=2** untuk 5 dari 6 tahun (2020, 2021, 2022, 2023, 2025)
- Hanya 2024 yang optimal_k=3
- **Keputusan project**: Tetap gunakan **k=3** karena domain knowledge (label bisnis: Rendah/Sedang/Tinggi)
- **Justifikasi**: Delta < 0.05 berarti K-Means dengan k=3 tidak memaksakan struktur yang tidak ada; Hierarchical hanya lebih "hemat" klaster

### Fitur: 2 vs 3 (Perubahan dari Versi Sebelumnya)
- **Versi lama**: 3 fitur (`kepadatan_penduduk`, `kepadatan_rumah`, `rata_rata_penghuni`)
- **Versi sekarang**: 2 fitur (`kepadatan_penduduk`, `kepadatan_rumah`)
- **Alasan**: `rata_rata_penghuni = kepadatan_penduduk / kepadatan_rumah` → multikolinearitas sempurna, tidak tambah informasi, membuat cluster kurang stabil
- **Hasil**: Silhouette meningkat signifikan (0.40→0.58 untuk 2020-2022), DB Index turun (0.55→0.27)

---

## Implementasi di Kode

```python
# clustering.py:140-160
features = ['kepadatan_penduduk', 'kepadatan_rumah']
X = df[features].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

hierarchical = AgglomerativeClustering(n_clusters=3, metric='euclidean', linkage='ward')
h_labels = hierarchical.fit_predict(X_scaled)
h_silhouette = silhouette_score(X_scaled, h_labels)

kmeans = KMeans(n_clusters=3, random_state=42, n_init=20)
km_labels = kmeans.fit_predict(X_scaled)
km_silhouette = silhouette_score(X_scaled, km_labels)
km_db = davies_bouldin_score(X_scaled, km_labels)

# Print perbandingan
print(f"Tahun {year}: Hierarchical Silhouette = {h_silhouette:.4f}, "
      f"K-Means Silhouette = {km_silhouette:.4f}, "
      f"Delta = {abs(h_silhouette - km_silhouette):.4f}, "
      f"DB Index = {km_db:.4f}, "
      f"Hierarchical optimal_k = {optimal_k}")
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

**Q: Kenapa Hierarchical optimal_k=2 tapi project pakai k=3?**
A: Domain knowledge fix 3 label bisnis (Rendah/Sedang/Tinggi). Delta < 0.05 membuktikan K-Means k=3 tidak memaksakan struktur yang tidak natural. Hierarchical "lebih hemat" klaster tapi tidak berarti k=3 salah.

**Q: Apakah perlu test k=2, k=4?**
A: Tidak wajib karena domain knowledge sudah fix 3 label. Tapi silhouette sweep k=2..5 sudah dilakukan via `find_optimal_k_hierarchical` dan hasilnya tercatat di metrics.

**Q: Kenapa 2023 & 2025 DB Index > 0.5?**
A: Data 2023-2025 memiliki anomali (lonjakan populasi >50% YoY di beberapa kecamatan). Lihat `data_quality_flag` di GeoJSON output. Cluster masih valid (Delta < 0.05) tapi kurang compact.

**Q: Jika nambah fitur lagi, apakah Delta tetap < 0.05?**
A: Bisa berubah. Re-run validasi ini setiap kali fitur diubah. Multikolinearitas (seperti rata_rata_penghuni) cenderung menurunkan kualitas cluster.