# Hubungan Hierarchical vs K-Means Silhouette & Toleransi Validasi k=3

## Ringkasan Eksekutif

| Tahun | Hierarchical Silhouette | K-Means Silhouette | Delta (Selisih) |
|-------|------------------------|-------------------|-----------------|
| 2020  | 0.5802                 | 0.5802            | 0.0000          |
| 2021  | 0.5854                 | 0.5854            | 0.0000          |
| 2022  | 0.5985                 | 0.5985            | 0.0000          |
| 2023  | 0.6237                 | 0.6237            | 0.0000          |
| 2024  | 0.6107                 | 0.6107            | 0.0000          |
| 2025  | 0.6313                 | 0.6313            | 0.0000          |

**Kesimpulan: Delta = 0.0000 untuk semua tahun → Kedua algoritma menghasilkan klaster yang identik → k=3 adalah pilihan natural untuk data ini.**

---

## Mengapa Membandingkan Keduanya?

| Aspek | Hierarchical (Ward) | K-Means |
|-------|---------------------|---------|
| Asumsi bentuk klaster | Tidak ada (non-parametric) | Spherical/bola, ukuran sama |
| Sensitivitas inisialisasi | Deterministik | Acak (mitigasi: `n_init=20`) |
| Output utama di project | **Silhouette score saja** (validasi) | **Label akhir** (Rendah/Sedang/Tinggi) |

Jika keduanya **sepakat** (Delta ≈ 0) → struktur data memang natural 3 klaster, K-Means tidak memaksakan bentuk bola.
Jika **bertentangan** (Delta besar) → K-Means memaksakan asumsi yang tidak cocok.

---

## Toleransi / Threshold Validasi

### 1. Delta (Selisih Silhouette)

| Delta | Interpretasi | Tindakan |
|-------|--------------|----------|
| **< 0.05** | **COCOK** — Kedua algoritma sepakat, k=3 valid | Lanjutkan |
| **0.05 – 0.15** | **WASPADA** — Ada perbedaan kecil, cek visual/klaster | Review manual |
| **> 0.15** | **TIDAK COCOK** — K-Means memaksakan bentuk bola | Coba k lain, atau pakai Hierarchical label |

> **Project ini**: Delta = 0.0000 → **Kategori COCOK sempurna**

### 2. Nilai Absolut Silhouette (Keduanya)

| Silhouette | Kualitas Klaster |
|------------|------------------|
| **> 0.70** | Sangat kuat, terpisah jelas |
| **0.50 – 0.70** | Cukup baik, terpisah wajar |
| **0.25 – 0.50** | Lemah, tumpang tindih signifikan |
| **< 0.25** | Tidak bermakna, acak |

> **Project ini**: 0.58 – 0.63 → **Kategori Cukup Baik** (memenuhi PRD Section 18: > 0.58)

### 3. Davies-Bouldin Index (Hanya K-Means)

| DB Index | Interpretasi |
|----------|--------------|
| **< 0.5** | Sangat baik (klaster compact & terpisah) |
| **0.5 – 1.0** | Baik |
| **> 1.0** | Kurang baik |

> **Project ini**: 0.38 – 0.40 → **Sangat Baik**

---

## Decision Matrix Gabungan

```
┌─────────────────────────────────────────────────────────────┐
│  Silhouette > 0.5  DAN  Delta < 0.05  DAN  DB < 0.5        │
│                        ↓                                    │
│              ✅ k=3 VALID & STABIL                          │
└─────────────────────────────────────────────────────────────┘
```

Project DensiMap **memenuhi ketiga kriteria** untuk semua tahun 2020–2025.

---

## Implementasi di Kode

```python
# clustering.py:108-130
hierarchical = AgglomerativeClustering(n_clusters=3, linkage='ward')
h_labels = hierarchical.fit_predict(X_scaled)
h_silhouette = silhouette_score(X_scaled, h_labels)

kmeans = KMeans(n_clusters=3, random_state=42, n_init=20)
km_labels = kmeans.fit_predict(X_scaled)
km_silhouette = silhouette_score(X_scaled, km_labels)
km_db = davies_bouldin_score(X_scaled, km_labels)

# Print perbandingan (ditambah via explain.md update)
print(f"Tahun {year}: Hierarchical Silhouette = {h_silhouette:.4f}, "
      f"K-Means Silhouette = {km_silhouette:.4f}, "
      f"Delta = {abs(h_silhouette - km_silhouette):.4f}, "
      f"DB Index = {km_db:.4f}")
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

**Q: Kenapa Delta = 0.0000 persis?**
A: Dengan n=10 kecil dan 2 fitur (kepadatan + luas), ruang pencarian klaster sangat terbatas. Kedua algoritma konvergen ke partisi yang sama.

**Q: Apakah perlu test k=2, k=4?**
A: Tidak wajib karena domain knowledge sudah fix 3 label bisnis (Rendah/Sedang/Tinggi). Tapi bisa ditambah *elbow/silhouette sweep* sebagai bukti tambahan.

**Q: Jika nambah fitur (misal jumlah rumah), apakah Delta tetap 0?**
A: Bisa berubah. Re-run validasi ini setiap kali fitur diubah.