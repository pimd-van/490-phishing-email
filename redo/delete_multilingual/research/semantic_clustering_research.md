# Semantic clustering ของอีเมล phishing: งานวิจัยปัจจุบันและแนวทางที่ใช้

สรุปเมื่อ 5 พ.ย. 2026 สำหรับงาน hierarchical clustering ของอีเมลที่ Linear SVM ทำนายว่าเป็น phishing
(6,995 แถว) แล้วสุ่ม 700 แถวตามสัดส่วนขนาดกลุ่ม เพื่อให้คนติด label และทดสอบ LLM ก่อนทำ RAG

## สรุปสั้น

งานปัจจุบันส่วนใหญ่ใช้ pipeline เดียวกันสี่ขั้น:

1. **Embedding จากโมเดลภาษา** แทน TF-IDF/LDA เพราะจับความหมายได้ดีกว่า LDA ในอีเมลให้หัวข้อกว้างและคลุมเครือ
2. **Clustering** บน embedding: HDBSCAN (มักลดมิติด้วย UMAP ก่อน), agglomerative/hierarchical หรือ k-means แบบซ้อนชั้น
3. **อธิบายกลุ่ม** ด้วยคำเด่นแบบ c-TF-IDF แล้วให้ LLM ตั้งชื่อและคำอธิบายกลุ่ม
4. **ประเมิน** ด้วย silhouette, coherence, diversity และสุดท้ายต้องให้คนตรวจ เพราะตัวชี้วัดอัตโนมัติเป็นแค่ค่าประมาณ

แนวโน้มปี 2025–2026 คือทำเป็น **ลำดับชั้น** (กลุ่มย่อยรวมเป็นหัวข้อใหญ่) และใช้ **LLM ช่วยตั้งชื่อหรือรวมกลุ่ม**

## งานวิจัยที่เกี่ยวข้อง

### Clustering แบบลำดับชั้นด้วย LLM embedding

- **Haschka & Bakarji (arXiv 2512.23471, ธ.ค. 2025)** สร้างต้นไม้ความหมายจาก embedding ของ LLM ด้วยการซ้อน
  density cluster แล้วค่อย ๆ ผ่อนเกณฑ์ความหนาแน่น ให้กลุ่มย่อยที่แน่นรวมเป็นธีมใหญ่ ผลบน benchmark
  พบว่าความสอดคล้องเชิงความหมายดีที่สุดที่ความละเอียดระดับกลาง ไม่ใช่ละเอียดสุดหรือหยาบสุด
  [arXiv](https://arxiv.org/abs/2512.23471v2)
- **HERCULES (Petnehazi & Aradi, arXiv 2506.19992, 2025)** ทำ k-means ซ้ำเป็นชั้น ๆ แล้วให้ LLM
  เขียนชื่อและคำอธิบายของแต่ละกลุ่มในทุกชั้น มีโหมด cluster บนคำอธิบายของ LLM และเครื่องมือดูผลแบบ interactive
  [arXiv](https://arxiv.org/abs/2506.19992)
- **Hanley & Durumeric (ACL 2025)** จัดกลุ่มข่าวเป็นชั้นด้วย Matryoshka embedding ที่ใช้มิติต่างกันในแต่ละชั้น
  [ACL 2025](https://papers.cool/venue/2025.acl-long.124@ACL)

### LLM กับการสร้าง taxonomy

- **TnT-LLM (Microsoft, KDD 2024)** ให้ LLM สร้างและปรับ taxonomy ของ label เอง แล้วใช้ LLM ติด label
  ให้ข้อมูลบางส่วนเพื่อฝึก classifier ขนาดเล็ก รายงานว่าได้ taxonomy ดีกว่าการ cluster embedding
  แล้วให้ LLM ตั้งชื่อ โดยเฉพาะเมื่อต้องตีความลึกกว่าความคล้ายผิวเผิน
  [arXiv](https://arxiv.org/abs/2403.12173)
- งานที่ใช้ BERTopic แล้วให้ LLM รวมหัวข้อที่คล้ายกัน พบว่าการแทนกลุ่มด้วยชื่อจาก LLM หรือ 10 คำเด่น
  ดีกว่ากันขึ้นกับจำนวนหัวข้อ ([สรุปจาก Emergent Mind](https://api.emergentmind.com/topics/bertopic-based-topic-modeling))

### อีเมล phishing / spam โดยตรง

- **Yakymovych & Singh (arXiv 2407.08888, 2024)** ใช้ BERTopic กับอีเมลที่ส่งไฟล์แนบอันตรายและ URL
  ใช้ **BGE-M3** ทำ embedding (โมเดลเดียวกับที่ใช้ในงานนี้) เทียบ HDBSCAN กับ OPTICS ด้วยจำนวนหัวข้อ,
  coherence และ diversity และใช้ Phi-3 ช่วยวิเคราะห์ความหมาย [arXiv](https://arxiv.org/abs/2407.08888)
- **SpamClus (NLPAICS 2024)** จัดกลุ่ม spam campaign ด้วย agglomerative clustering บน BERT embedding
  [PDF](https://preview.aclanthology.org/moar-dois/2024.nlpaics-1.8.pdf)
- **Althobaiti et al. (IEEE Access 2023)** ใช้ clustering จับ phishing campaign จาก feature ต้นทางและ URL
  พบว่า Mean Shift ดีกว่า DBSCAN ([บทคัดย่อ](https://aminer.org/pub/6523b750939a5f40821be434/using-clustering-algorithms-to-automatically-identify-phishing-campaigns))
- งาน LDA บนอีเมลพบว่าหัวข้อกว้างและคลุมเครือเกินไป ([NSF PAR](https://par.nsf.gov/servlets/purl/10482032))

### การสุ่มตัวอย่างตามกลุ่มเพื่อให้คน/LLM ติด label

- **SubLIME (arXiv 2406.15527)** สร้าง subset ตัวแทนด้วย stratified sampling ตามกลุ่มหัวข้อ เทียบกับสุ่มธรรมดา
  [arXiv](https://arxiv.org/abs/2406.15527)
- **ALPHA (arXiv 2509.05936)** cluster embedding ด้วย k-means แล้วเลือกตัวอย่างที่ใกล้ centroid ส่งให้ LLM ติด label
  [arXiv](https://arxiv.org/abs/2509.05936)
- **Latent-space stratification (NeurIPS 2026)** แบ่ง strata จาก latent space และจัดสรรตัวอย่างแบบ Neyman
  ตามขนาดและความแปรปรวนของ strata [NeurIPS](https://neurips.cc/virtual/2026/178254)
- **tinyBenchmarks (arXiv 2402.14992)** และ **AnchorPoints** ใช้ตัวแทนของกลุ่มเพื่อประเมิน LLM ด้วยตัวอย่างน้อย
  [arXiv](https://arxiv.org/abs/2402.14992)

### ข้อควรระวังเชิงเทคนิค

- **Ward linkage ต้องใช้ระยะแบบ Euclidean** ถ้าใช้ cosine ให้ normalize เวกเตอร์ให้ยาว 1 ก่อน
  ระยะ Euclidean ของเวกเตอร์ยาว 1 แปรผันตาม cosine จึงใช้ Ward ได้ถูกต้อง
  ([Enhancement of Short Text Clustering by Iterative Classification](https://arxiv.org/pdf/2001.11631))
- **Average linkage + cosine** นิยมใช้ และเลือกจำนวนกลุ่มจาก silhouette
  ([Combining Neural Language Models for Word Sense Induction](https://arxiv.org/pdf/2006.13200))
  แต่ในข้อมูลจริงมักได้กลุ่มใหญ่หนึ่งกลุ่มกับกลุ่มเล็กมาก ๆ จำนวนมาก
- **เลือกจำนวนกลุ่ม** ด้วย silhouette หลายระดับ แล้วดูประกอบกับขนาดกลุ่มใหญ่สุดและจำนวนกลุ่มเล็ก
  ([Exploring the Sensory Spaces of English Perceptual Verbs](https://arxiv.org/pdf/2110.09721))
- ตัวชี้วัดอัตโนมัติเป็นค่าประมาณ ควรให้คนดูตัวอย่างของแต่ละกลุ่มด้วย

## แนวทางที่เลือกในงานนี้

| ขั้นตอน | สิ่งที่ทำ | เหตุผลจากงานวิจัย |
|---|---|---|
| ข้อมูล | `redo/delete_multilingual/dataset/svm_handoff.csv` 6,995 อีเมล | ชุดที่ Linear SVM ทำนายว่าเป็น phishing |
| ข้อความ | `Subject: ...\nBody: ...` แทน URL ด้วย `token_url` | ไม่ให้ URL สุ่มทำให้อีเมลธีมเดียวกันห่างกัน |
| Embedding | BAAI/bge-m3, dense, normalize, ยาวสุด 2,048 tokens | ใช้ใน Yakymovych & Singh, รองรับหลายภาษา และตรงกับ Part 2 |
| Vector DB | Chroma (cosine) + `vectors.npz` | reuse ได้ทั้งตอน RAG และงานวิเคราะห์ |
| Clustering | agglomerative 2 แบบ: Ward บนเวกเตอร์ normalize และ average-cosine | ต้นไม้เดียวตัดได้หลายระดับ จึงได้กลุ่มแม่และกลุ่มลูกที่ซ้อนกันพอดี |
| เลือกระดับ | กลุ่มลูก 10–40 กลุ่ม: ไม่มีกลุ่มใดเกิน 25% และทุกกลุ่มได้ตัวอย่างอย่างน้อย 1 แถว จากนั้นเลือก silhouette สูงสุด; กลุ่มแม่ 4–8 กลุ่ม เลือก silhouette สูงสุดบนต้นไม้เดียวกัน | silhouette + ข้อจำกัดเรื่องขนาด |
| อธิบายกลุ่ม | คำเด่น c-TF-IDF, 5 อีเมลที่ใกล้ centroid, สัดส่วน source/ภาษา/URL/ไฟล์แนบ, ชื่อกลุ่มจาก qwen2.5:7b ผ่าน Ollama | แบบ BERTopic และ HERCULES |
| สุ่ม 700 | จัดสรรตามจำนวนอีเมลของแต่ละกลุ่ม (largest remainder) แล้วสุ่มในกลุ่มด้วย seed 42 | stratified sampling ตามกลุ่ม |
| ภาพ | t-SNE 2 มิติ (cosine) และต้นไม้ของกลุ่ม | ดูภาพรวมว่าแต่ละกลุ่มอยู่ตรงไหน |

ไม่ใช้ HDBSCAN/UMAP ในรอบนี้ เพราะ HDBSCAN จะตัดอีเมลจำนวนหนึ่งเป็น noise ซึ่งไม่เข้ากับการสุ่มจากทุกแถว
และ VM ยังไม่ได้ติดตั้ง `umap-learn` ถ้าจะเทียบเพิ่ม ให้ลองเป็นขั้นต่อไป

ผลการ cluster อยู่ใน [`semantic_clustering_results.md`](semantic_clustering_results.md)
