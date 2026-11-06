# Semantic clustering ของ SVM handoff

ผลและวิธีอยู่ใน [research/semantic_clustering_results.md](../../research/semantic_clustering_results.md) และงานวิจัยอ้างอิงใน [research/semantic_clustering_research.md](../../research/semantic_clustering_research.md)

- `svm_bge_m3/`: vectors, ต้นไม้, การจัดกลุ่ม, 700 แถวที่สุ่ม และสคริปต์ `svm_clustering.py`
- `svm_clusters.html`: หน้าแสดงผลแบบ interactive เปิดในเบราว์เซอร์ได้เลย
- `viz_template.html`: template ที่ใช้สร้างหน้าแสดงผลจาก `viz_data.json`
- `svm_dendrogram.png`: dendrogram ของ 20 กลุ่มย่อย สีตาม 8 กลุ่มแม่ เส้นประคือระดับที่ตัดเป็นกลุ่มแม่
- `svm_dendrogram_60.png`: dendrogram 60 ขา (ตัดที่ 8 / 20 / 60 กลุ่ม)
- `svm_bge_m3/deep_tree.json`: กลุ่มชั้นที่ 60 พร้อมชื่อ คำเด่น และรายชื่ออีเมล (สร้างด้วย `deep_tree.py`)
- `build_page.py`, `plot_dendrogram.py`: สร้างหน้าแสดงผลและรูป dendrogram ใหม่
