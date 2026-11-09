# Part 2: KB คำแนะนำ + RAG + Local LLM

Part 2 รับอีเมลที่ Part 1 ทายว่าเป็นฟิชชิง (ถือว่าเป็นฟิชชิงทั้งหมด) ค้น chunk คำแนะนำจาก KB 20 chunk แล้วให้ Local LLM 4 ตัวเขียนเหตุผลและขั้นตอนป้องกัน พร้อมวัดผลเทียบกับเฉลยที่ติดป้ายไว้

## ติดตั้ง (ครั้งเดียว)

```bash
.venv/bin/python -m pip install -r requirements-part2.txt
ollama list        # ต้องมี llama3.1:8b, mistral:7b, qwen2.5:7b, phi3:mini
```

ครั้งแรกที่รัน vector_database จะดาวน์โหลด BAAI/bge-m3 (~2.3 GB) จาก Hugging Face

## ลำดับการรัน (จาก project root)

| ขั้น | คำสั่ง | ได้อะไร |
| --- | --- | --- |
| 0 | `.venv/bin/python part2/labels/build_gold.py` | `labels/gold.csv` (มีแล้ว; รันใหม่เมื่อเพิ่ม labels_fold*.csv) |
| 1 | `.venv/bin/python part2/vector_database/main_vector_database.py` | collection `phishing_kb20_bge_m3` ใน `RAG/.chroma` |
| 2 | `.venv/bin/python part2/RAG/main_RAG.py --set dev` | ผลค้นบน dev ใช้ปรับค่า |
| 3 | `.venv/bin/python part2/RAG/main_RAG.py --set fold1` | ผลค้นบนชุดทดสอบหลัก (ไฟล์ที่ LLM ใช้) |
| 4 | `.venv/bin/python part2/LLM/main_LLM.py --dry-run` | ดู prompt ที่จะส่งจริง ไม่เรียกโมเดล |
| 5 | `.venv/bin/python part2/LLM/main_LLM.py --limit 5` | ทดสอบความเร็ว 5 อีเมล × 4 โมเดล × 3 เงื่อนไข |
| 6 | `.venv/bin/python part2/LLM/main_LLM.py` | รันจริง (fold1, prompt full) รันต่อจากที่ค้างได้ |
| 7 | `.venv/bin/python part2/LLM/main_LLM.py --prompt-version simple --conditions rag` | prompt อย่างง่ายสำหรับเทียบ |
| 8 | `.venv/bin/python part2/LLM/evaluate_LLM.py --set fold1` | `summary_LLM.json`, `scored_LLM.csv` (M1, M2, M5) |
| 9 | `.venv/bin/python part2/LLM/human_eval/make_human_eval.py --n 50` | แบบฟอร์มให้คนให้คะแนน (M3, M4) |
| 10 | `.venv/bin/python part2/LLM/render_output.py --model <ชื่อ> --condition rag` | ผลลัพธ์แบบที่ผู้ใช้เห็น (`--hide-chunk-ids` = ไม่แสดง ID) |

ถ้า `main_LLM.py` หยุดกลางทาง (ไฟดับ, timeout) ให้รันคำสั่งเดิมอีกครั้ง ระบบข้ามคำตอบที่เสร็จแล้ว

## ชุดข้อมูล (`--set`)

| ชุด | แถว | ใช้ทำอะไร |
| --- | --- | --- |
| `dev` | 658 | ปรับค่า RAG และ prompt ได้ไม่จำกัด |
| `fold1` | 597 | **ชุดทดสอบหลัก** รันครั้งเดียวหลังล็อกค่าทั้งหมด |
| `fold2` | 597 | ทดสอบซ้ำ ยืนยันว่าผลนิ่ง |
| `test` | 5,965 | RAG บน test ทั้งหมด (fold3–10 ใช้เฉลยรอบ 1) |

เฉลยของ fold1 และ fold2 ใช้กฎ v1.13 ที่แช่แข็งและ Opus ตรวจครบทุกแถว ส่วนแถวอื่นใช้เฉลยรอบ 1 (`gold.csv` คอลัมน์ `gold_source` บอกที่มา) แถวที่ `excluded = 1` (49 แถวที่อาจเกี่ยวกับผู้เยาว์ และ 1 แถวที่เสีย) ไม่ถูกใช้ในทุกขั้น

**ห้ามปรับ prompt หรือค่าใด ๆ โดยดูผลจาก fold1** ไม่อย่างนั้นผลวัดจะสูงเกินจริง (overfitting)

## โครงสร้าง

```text
part2/
├── README_part2.md
├── part2_handoff.csv, data.csv     # ไฟล์จาก Part 1 (ไม่ถูกแก้ไข)
├── labels/                         # เฉลยและไฟล์ที่ใช้ทำเฉลย
│   ├── gold.csv                    # เฉลยรวมที่ทุกขั้นอ่าน
│   ├── labels_fold1.csv, labels_fold2.csv, labels_round1.csv
│   ├── model_input.jsonl, params.json   # อีเมลที่ตัดความยาวแล้ว (BODY_CAP 6,500, URL_CAP 10)
│   ├── split.json, test_folds.json      # dev/test และ 10 fold
│   ├── build_gold.py, make_folds.py, profile_caps.py
│   ├── rules/                      # กฎ v1.13 และ CHANGELOG (อังกฤษ + ไทย)
│   └── human_review_possible_minors.csv, non_english_rows_round1.csv
├── vector_database/
│   ├── config_vector_database.json            # หลัก: BGE-M3 + KB 20 chunk
│   ├── config_vector_database_bge_large.json  # ทดลอง: โมเดลเดิม bge-large-en-v1.5
│   ├── config_vector_database_kb17.json       # ทดลอง: KB 17 chunk
│   ├── main_vector_database.py
│   ├── document/                   # 20 ไฟล์ .txt = 20 chunk (ข้อความที่ embed จริง)
│   ├── document_17/                # 17 chunk สำหรับการทดลอง
│   ├── sources.json, sources_kb17.json        # แหล่งของแต่ละไฟล์ (รูปแบบเดิมของเพื่อน + chunk_id)
│   ├── sources_detail.json, source_rationale.md, kb_docs/  # รายละเอียดแหล่ง ลิขสิทธิ์ และเอกสาร chunk
│   └── mapping_20_to_17.json
├── RAG/
│   ├── config_RAG.json, main_RAG.py
│   ├── result_RAG.json, summary_RAG.json      # (สร้างตอนรัน)
│   └── .chroma/                    # (สร้างตอนรัน)
└── LLM/
    ├── config_LLM.json             # โมเดล, เงื่อนไข, prompt full/simple, ค่า generation
    ├── main_LLM.py, evaluate_LLM.py, render_output.py
    ├── result_LLM.jsonl, models_info.json, summary_LLM.json, scored_LLM.csv, output_LLM.*   # (สร้างตอนรัน)
    └── human_eval/                 # make_human_eval.py, score_human_eval.py, rubric_TH.md
```

## เปลี่ยนจากโค้ดเดิมของเพื่อน

| เรื่อง | เดิม | ตอนนี้ | เหตุผล |
| --- | --- | --- | --- |
| KB | 7 เอกสาร ตัดตาม token, ID `a1` | 20 chunk ตามสถานการณ์, ID `BRD-01` | ID ตรงกับเฉลย 6,973 แถว |
| embedding | bge-large-en-v1.5 (512 tokens, อังกฤษ) | BGE-M3 (เก็บตัวเดิมไว้เป็นการทดลอง) | อีเมลยาว ~1,500 tokens และมีภาษาอื่น 327 แถว |
| คำค้น | คำสั่งยาวเหมือนกันทุกฉบับ + อีเมล | อีเมล + URL 3 ตัวแรก | คำสั่งเดียวกันดึงทุกอีเมลไปหา chunk ทั่วไป |
| เฉลย RAG | regex (`a2`, `g1` ทุกแถว) | `gold.csv` จากการติดป้าย | วัดผลได้จริง |
| `data.csv` | ถูกเขียนทับทุกครั้งที่รัน | ไม่มีขั้นไหนแก้ไฟล์ input | ข้อมูลต้นฉบับต้องไม่เปลี่ยน |
| คำตอบ LLM | ข้อความอิสระ, `num_predict` 500 ถูกตัด | JSON (chunk ที่ใช้ + เหตุผล + ขั้นตอน), 1,000 | วัด M1–M2 อัตโนมัติได้ |
| เงื่อนไข | RAG อย่างเดียว | rag / oracle / no_rag | แยกว่าผิดเพราะค้นหรือเพราะเลือก |
| รันต่อ | เริ่มใหม่ทั้งหมด | ต่อท้ายทีละคำตอบ ข้ามที่เสร็จแล้ว | 600 × 4 × 3 = 7,164 คำตอบ |

## ข้อควรรู้

- **แถวเสีย 1 แถว:** body ของ `meajor_test_22699` ยาวถึง 32,759 ตัวอักษร (ชนเพดานเซลล์ของโปรแกรมตาราง 32,767) ส่วนที่เกินล้นไปเป็นแถวใหม่ที่ id เป็นข้อความอีเมล จึงนับได้ 6,973 แทน 6,972 แถวที่ล้นถูกตัดออก
- **baseline ของ RAG แรงมาก:** chunk อย่าง LNK-01, SPM-01, SPM-03 อยู่ในเฉลยหลายพันแถว รายการคงที่ 5 ตัวจึงได้ Recall@5 สูง ให้ดู nDCG@5, MRR และ Hit@1 ประกอบเสมอ
- **ตัวเลขใน `summary_*.json` จากการทดสอบในเครื่องผู้พัฒนาไม่มีความหมาย** เพราะใช้ตัวจำลองแทนโมเดลจริง ต้องรันบนเครื่องจริงใหม่ทั้งหมด
- **ไฟล์ที่ห้ามส่งเข้าโมเดล:** กฎติดป้าย, `gold.csv` และไฟล์ ground truth ของ Part 1
- เกณฑ์วัดผล rubric และเหตุผลจากงานวิจัยอยู่ในเอกสาร Literature review ของโปรเจกต์
