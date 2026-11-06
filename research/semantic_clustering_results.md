# ผล semantic clustering ของอีเมล phishing จาก Linear SVM

รันบน VM 490-18 เมื่อ 5–6 พ.ย. 2026 วิธีที่เลือกและงานวิจัยอ้างอิงอยู่ใน
[`semantic_clustering_research.md`](semantic_clustering_research.md)

- ข้อมูล: อีเมล 6,995 ฉบับที่ Linear SVM ทำนายว่าเป็น phishing (`redo/dataset/svm_handoff.csv`)
- Embedding: BAAI/bge-m3 (dense, normalize, ยาวสุด 2,048 tokens) ค่ากลางความยาว 257 tokens ถูกตัด 61 ฉบับ
  ใช้ CPU 49 นาที เพราะ PyTorch บน VM ไม่ได้ build มาให้ใช้ CUDA
- Clustering: Ward บนเวกเตอร์ normalize ตัดต้นไม้เดียวกันเป็น **8 กลุ่มแม่** และ **20 กลุ่มย่อย**
  กลุ่มย่อยทุกกลุ่มอยู่ในกลุ่มแม่เดียว
- ชื่อกลุ่ม: qwen2.5:7b ผ่าน Ollama ตั้งชื่อจากคำเด่นและ 5 อีเมลที่ใกล้ centroid ของกลุ่มที่สุด
  ชื่อเหล่านี้ยังไม่ได้ให้คนตรวจทาน
- หน้าแสดงผล: [กลุ่มอีเมล phishing ของ SVM](https://claude.ai/artifact/GjzAga3Uvi8hgiaT8XvExB)
  (ไฟล์ [`redo/semantic_clustering/svm_clusters.html`](../redo/semantic_clustering/svm_clusters.html))

## การเลือกจำนวนกลุ่ม

| linkage | กลุ่ม | silhouette (cosine) | กลุ่มใหญ่สุด | กลุ่มเล็กสุด |
|---|---:|---:|---:|---:|
| Ward | 8 (กลุ่มแม่) | 0.088 | 34.6% | 279 |
| Ward | 15 | 0.110 | 15.1% | 94 |
| **Ward** | **20 (กลุ่มย่อย)** | **0.111** | 15.1% | 84 |
| Ward | 25 | 0.069 | 12.3% | 57 |
| average-cosine | 20 | −0.007 | 98.5% | 1 |

average-cosine ได้กลุ่มใหญ่กลุ่มเดียวที่มีอีเมลเกือบทั้งหมด (85–99%) และกลุ่มเล็ก ๆ ที่มีอีเมลฉบับเดียวจำนวนมาก
จึงใช้สุ่มตามสัดส่วนไม่ได้ ส่วน Ward ที่ 20 กลุ่มได้ silhouette สูงสุดในช่วงที่ผ่านเงื่อนไข ซึ่งต้องไม่มีกลุ่มใดเกิน 25%
และทุกกลุ่มต้องได้ตัวอย่างอย่างน้อย 1 แถว

ค่า silhouette 0.11 ถือว่าต่ำ แปลว่ากลุ่มยังซ้อนทับกันมาก ซึ่งพบได้ทั่วไปเมื่อ cluster embedding ข้อความมิติสูง
ควรตัดสินจากตัวอย่างอีเมลในแต่ละกลุ่มประกอบด้วย

## กลุ่มที่ได้

| กลุ่มแม่ | กลุ่มย่อย | ชื่อจาก LLM | อีเมล | สุ่ม | คำเด่น |
|---|---|---|---:|---:|---|
| 1 Product Update | C1 | Product Inquiry | 1,054 | 106 | organization, initials, said, address |
| | C2 | Product Offer | 583 | 58 | reference number, file, product, date |
| | C3 | dating site | 298 | 30 | url, want, site, meet, girls |
| | C4 | Product Financial | 296 | 30 | product, softwares, financial info |
| | C5 | Replica Watches | 191 | 19 | watches, replica, watch, gift |
| 2 Financial Savings | C6 | Pharmaceutical Savings | 603 | 60 | low financial, meds, info product |
| | C7 | Generic Drugs | 338 | 34 | drugs, medications, quality, generic |
| | C8 | Pills and Savings | 117 | 12 | pills, save financial |
| 3 Free Financial Services | C9 | Financial Gain | 758 | 76 | organization, address, url, receive |
| | C10 | Refinance Offer | 199 | 20 | credit, loan, approval, lenders |
| 4 Weight Loss | C11 | Penis Enlargement | 472 | 47 | men, size, penis, increase |
| | C12 | Weight Loss | 233 | 23 | weight, people, life, food |
| | C13 | Erection Enhancement | 102 | 10 | prescription, effects, long |
| 5 Symbolic Emojis | C14 | Symbolic Emojis | 613 | 61 | simbol, emoji, symbol |
| 6 Financial Alert | C15 | Financial Alert | 284 | 29 | company, gas, investment, shares |
| | C16 | Financial Trading | 214 | 22 | target price, news, price |
| 7 Bank Transaction | C17 | Foreign Wealth | 183 | 18 | account, money, bank, fund, kin |
| | C18 | Job Position | 94 | 9 | reference number, company, payments, position |
| | C19 | Lottery Prize | 84 | 8 | lottery, winning, prize |
| 8 Price Savings | C20 | Low Price Software | 279 | 28 | retail price, product |
| | | **รวม** | **6,995** | **700** | |

### สิ่งที่เห็นจากกลุ่ม

- **ธีม spam คลาสสิกแยกได้ชัด:** ยา (C6–C8), ยาเสริมสมรรถภาพทางเพศ (C11, C13), ลดน้ำหนัก (C12),
  นาฬิกาปลอม (C5), ซอฟต์แวร์ราคาถูก (C20), หาคู่ (C3), กู้เงิน/รีไฟแนนซ์ (C10), ปั่นหุ้น (C15–C16),
  มรดก/โอนเงินต่างประเทศแบบ 419 (C17), รับสมัครงานรับโอนเงิน (C18) และถูกลอตเตอรี่ (C19)
  กลุ่มเหล่านี้มี cohesion สูง (0.78–0.92)
- **อีเมล phishing ที่หลอกขอบัญชีหรือรหัสผ่านโดยตรงไม่มีกลุ่มของตัวเอง:** ข้อมูลส่วนใหญ่มาจาก TREC 2005–2007
  ซึ่งเป็น spam เชิงขายของ อีเมลขอ login น่าจะกระจายอยู่ใน C1, C2 และ C9
- **placeholder จากการทำข้อมูลนิรนามมีผลต่อการจัดกลุ่ม:** C1, C2, C4 และ C9 มีคำเด่นเป็น `organization`,
  `product`, `initials`, `reference number` ซึ่งมาจาก `[ORGANIZATION]`, `[PRODUCT]` ที่ MeAJOR ใส่แทนข้อมูลจริง
  กลุ่มพวกนี้จึงจัดตามความถี่ของ placeholder ส่วนหนึ่ง ไม่ได้จัดตามเนื้อหาอย่างเดียว ชื่อจาก LLM ก็กว้างตามไปด้วย
- **C14 (613 อีเมล) คือข้อความที่ถูกแทนด้วย `<|SIMBOL|>` หรือ emoji เกือบทั้งหมด** มีหลายภาษาปนกัน
  (อังกฤษ 183, รัสเซีย 100) อ่านความหมายได้น้อย ถ้าให้คนติด label กลุ่มนี้อาจตัดสินยาก

## 700 แถวสำหรับติด label

`sample_700.csv` จัดสรรตามจำนวนอีเมลของแต่ละกลุ่มย่อยด้วยวิธี largest remainder แล้วสุ่มภายในกลุ่มด้วย seed 42
ทุกกลุ่มได้อย่างน้อย 8 แถว คอลัมน์เหมือน `svm_handoff.csv` และเพิ่ม `parent_cluster_id`, `cluster_id`
ข้อความที่ขึ้นต้นด้วย `= + - @` ถูกเติม `'` นำหน้า เพื่อไม่ให้ Excel ตีความเป็นสูตร

## ไฟล์

| ไฟล์ | เนื้อหา |
|---|---|
| `vectors.npz` | `ids`, `embeddings` (6,995 × 1,024, float32, normalize แล้ว), `meta` |
| `chroma/` (ไม่อยู่ใน Git เพราะมีขนาด 98 MB) | Chroma collection `svm_handoff_bge_m3` (cosine) มีเอกสาร, embedding และ metadata (`test_row`, `source`, `language`, `url_count`, `has_attachments`, `sender_domain`, `svm_decision_score`) |
| `assignments.csv` | ทุกอีเมล: `parent_cluster_id`, `cluster_id`, `in_sample_700` |
| `sample_700.csv` | 700 แถวที่สุ่มไว้ให้ติด label |
| `clusters.json` | โปรไฟล์ของแต่ละกลุ่ม: คำเด่น, ตัวอย่าง, สัดส่วน source/ภาษา/URL, ชื่อและคำอธิบายจาก LLM |
| `diagnostics.json` | silhouette และขนาดกลุ่มของทุกระดับที่ทดลอง |
| `linkage_ward.npy`, `linkage_average_cosine.npy` | ต้นไม้ scipy สำหรับตัดระดับอื่นโดยไม่ต้องคำนวณใหม่ |
| `viz_data.json` | พิกัด t-SNE และข้อมูลที่หน้าแสดงผลใช้ |
| `svm_clustering.py` | สคริปต์ทั้งหมด (`--stage embed|cluster|profile|sample|viz|all`) |

ไฟล์อยู่ที่ [`redo/semantic_clustering/svm_bge_m3/`](../redo/semantic_clustering/svm_bge_m3/) ใน repo นี้
ส่วน Chroma ฉบับเต็มอยู่บน VM 490-18 ที่ `~/benchmark_runs/semantic_clustering/out/chroma`
และบนเครื่อง Windows ที่ `C:\pimd\ย้าย\pimdej\490\semantic_clustering\svm_bge_m3\chroma`
ถ้าไม่มี ให้สร้างใหม่จาก `vectors.npz` ได้ในไม่กี่วินาทีโดยไม่ต้อง embed ใหม่:

```python
import csv, json, chromadb, numpy as np
csv.field_size_limit(1 << 30)
z = np.load("redo/semantic_clustering/svm_bge_m3/vectors.npz")
rows = {r["id"]: r for r in csv.DictReader(open("redo/dataset/svm_handoff.csv", encoding="utf-8-sig", newline=""))}
col = chromadb.PersistentClient(path="redo/semantic_clustering/svm_bge_m3/chroma").get_or_create_collection(
    "svm_handoff_bge_m3", metadata={"hnsw:space": "cosine"})
for i in range(0, len(z["ids"]), 500):
    ids = z["ids"][i:i + 500].tolist()
    col.add(ids=ids, embeddings=z["embeddings"][i:i + 500].tolist(),
            documents=[f"Subject: {rows[x]['subject']}\nBody: {rows[x]['body']}" for x in ids])
```

ใช้ vector DB ซ้ำได้แบบนี้:

```python
import chromadb, numpy as np
col = chromadb.PersistentClient(path="svm_bge_m3/chroma").get_collection("svm_handoff_bge_m3")
z = np.load("svm_bge_m3/vectors.npz"); ids, emb = z["ids"], z["embeddings"]
col.query(query_embeddings=[emb[0].tolist()], n_results=5)
```

## ขั้นต่อไปที่ควรลอง

1. ลบ placeholder (`[ORGANIZATION]`, `[PRODUCT]`, `<|SIMBOL|>`) ออกจากข้อความก่อน embed แล้วเทียบผลกับรอบนี้
2. ลอง UMAP + HDBSCAN แบบ BERTopic เป็นตัวเปรียบเทียบ โดยจัดอีเมลที่เป็น noise เข้ากลุ่มที่ใกล้ที่สุด
3. ให้คนตรวจชื่อกลุ่มจาก 3–5 ตัวอย่างต่อกลุ่ม ก่อนใช้เป็นหมวดตอนติด label
