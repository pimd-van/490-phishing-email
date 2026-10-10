# Project structure

## Main files

```text
490-phishing-email/
├── README.md
├── CONTEXT.md
├── structure.md
├── requirements-part2.txt
├── part2/
│   ├── part2_handoff.csv             # ต้นฉบับ handoff จาก Part 1
│   └── vector_database/
│       ├── config.json               # model, chunk และ path settings
│       ├── main.py                   # อ่านเอกสาร สร้าง chunks และบันทึก Chroma
│       └── document/                 # guidance documents สำหรับสร้างฐานข้อมูล
│   ├── data.csv                      # สำเนา 100 แถวแรกและคอลัมน์ chunk
│   └── RAG/
│       ├── check.py                  # retrieve top 5 chunks ต่ออีเมล
│       ├── result.json               # query_id และ chunk_ids ที่ค้นได้
│       └── .chroma/                  # persistent Chroma database (generated)
```

## Vector database

ใน `part2/vector_database/` มีรายการระดับบนเพียง 3 รายการตามนี้:

- `document/`: ไฟล์ `.md` และ `.txt` ที่นำเข้าเป็น guidance knowledge base
- `main.py`: อ่าน config, แบ่งเอกสารตาม token, สร้าง embeddings และเขียนลง Chroma
- `config.json`: ตั้ง embedding model, collection, chunk size/overlap, batch size,
  top-k, ตำแหน่งเอกสาร และตำแหน่ง Chroma database

รันจาก project root:

```bash
.venv/bin/python part2/vector_database/main.py
```

Chroma database อยู่ที่ `part2/RAG/.chroma/` เพื่อให้โฟลเดอร์ `vector_database/`
คงเหลือเฉพาะสามรายการข้างต้น

## Guidance documents

`document/` มีไฟล์ guidance ระดับบน 7 ไฟล์ที่ถูกนำเข้า:

- `nist_phishing.md`: การรู้จักสัญญาณ phishing และการป้องกัน
- `nist_phish_scale_summary.md`: สรุป NIST Phish Scale และข้อกำหนด license
- `cisa_joint_phishing_guidance.md`: มาตรการป้องกันและตอบสนอง phishing จาก CISA/NSA/FBI/MS-ISAC
- `cisa_email_attachments.md`: ความเสี่ยงและการจัดการ email attachments
- `owasp_unvalidated_redirects.md`: การป้องกัน open redirect ที่นำไปใช้กับ phishing
- `apwg_q1_2026_summary.md`: แนวโน้ม phishing จากรายงาน APWG ไตรมาส 1 ปี 2026
- `google_spot_scams_summary.md`: สัญญาณ scam และการตอบสนองตามคำแนะนำของ Google

`document/extras/nist_multi_factor_authentication.md` เป็นข้อมูลเสริมใน subfolder;
`main.py` ค้นเฉพาะไฟล์ระดับบน จึงไม่ถูกนำเข้า

## Retrieval check (`part2/RAG/`)

### `data.csv`

สำเนาพร้อม header และ 100 data rows แรกจาก `part2/part2_handoff.csv` ใช้เป็น
input สำหรับตรวจการค้นคืน โดยไฟล์ต้นฉบับไม่ถูกเปลี่ยน หลังรัน `check.py` จะมี
คอลัมน์ `chunk` เพิ่มขึ้น โดยเก็บ JSON array ของ `required_chunk` IDs ตามสถานการณ์
แต่ละ query อาจมีจำนวน required chunks ไม่เท่ากัน และไม่จำเป็นต้องมีครบ 5 รายการ

### `check.py`

อ่านข้อความอีเมลแต่ละแถวและเติมคำถามเพื่อหาแนวทาง action plan ที่เหมาะสม จากนั้น
เลือก `required_chunk` ตามตัวบ่งชี้ใน subject/body (เช่น credential/financial risk,
attachment หรือบริบทองค์กร) แยกจาก retrieval แล้ว embedding ด้วย model และ query
prefix เดียวกับตอน build เพื่อค้น 5 chunks ที่ใกล้ที่สุด

รันจาก project root:

```bash
.venv/bin/python part2/RAG/check.py
```

### `result.json`

JSON array มีหนึ่งรายการต่อ query มี input จริง, required chunks ที่คาดว่าควรใช้,
คะแนนของแต่ละ chunk ที่ค้นได้ และ IDs ที่ค้นได้เรียงตามอันดับ:

```json
{
  "query_id": "id ของแถวจาก data.csv",
  "input": "query ที่ส่งเข้า embedding model",
  "required_chunk": ["<required chunk id 1>", "..."],
  "score_chunk": 66.67,
  "top_retrieved_chunk": ["<retrieved chunk id 1>", "<retrieved chunk id 2>", "..."]
}
```

`required_chunk` เป็น reference ที่ต้องมีเพื่อรองรับ action plan ตามสถานการณ์
ไม่ได้คัดลอกมาจากผล top 5 ส่วน `top_retrieved_chunk` คือ IDs ที่ Chroma ค้นได้จริง
`score_chunk` คือ coverage percentage: จำนวน required IDs ที่พบใน top retrieved
หารด้วยจำนวน required IDs ทั้งหมด คูณ 100 คอลัมน์ CSV `chunk` เก็บเฉพาะ required
IDs ของแถวที่ `id` ตรงกับ `query_id`

### `.chroma/`

ฐานข้อมูล Chroma แบบ persistent เก็บ chunks, embeddings และ metadata ที่สร้างโดย
`main.py`; เป็น generated data และถูก Git ignore

## Other project files

- `README.md`: ภาพรวมและวิธีใช้โปรเจกต์
- `CONTEXT.md`: glossary ของ handoff email, guidance document, chunk และ index
- `requirements-part2.txt`: dependencies ของ ChromaDB และ Sentence Transformers
- `.gitignore`: ระบุไฟล์ local/generated ที่ไม่ควร commit
- `.venv/`: Python environment ในเครื่อง ไม่ใช่ source code
- `.git/`: ประวัติและ metadata ของ Git
