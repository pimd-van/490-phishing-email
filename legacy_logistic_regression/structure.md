# Project structure

## Main files

```text
490-phishing-email/
├── README.md
├── CONTEXT.md
├── structure.md
├── requirements-part2.txt
└── part2/
    ├── part2_handoff.csv             # ต้นฉบับ handoff จาก Part 1
    ├── data.csv                      # สำเนา 100 แถวแรกและคอลัมน์ chunk
    ├── vector_database/
    │   ├── config_vector_database.json  # model, chunk และ path settings
    │   ├── main_vector_database.py      # อ่านเอกสาร สร้าง chunks และบันทึก Chroma
    │   ├── result_vector_database.json  # chunk_id, token, content ของแต่ละ chunk
    │   ├── sources.json                 # แหล่งอ้างอิงและ letter ของแต่ละเอกสาร
    │   └── document/                 # guidance documents สำหรับสร้างฐานข้อมูล
    ├── RAG/
    │   ├── config_RAG.json           # retrieval query, top-k และความยาวอีเมล
    │   ├── main_RAG.py              # retrieve top-k chunks ต่ออีเมล
    │   ├── result_RAG.json          # query_id และ chunk_ids ที่ค้นได้
    │   └── .chroma/                  # persistent Chroma database (generated)
    └── LLM/
        ├── config_LLM.json           # prompt และ generation settings ร่วมกัน
        ├── main_LLM.py              # สร้าง action plan จากอีเมลและ retrieved chunks
        └── result_LLM.json          # subject, body และคำตอบ model1–model4 (generated)
```

## Vector database

ใน `part2/vector_database/` มีรายการหลักดังนี้:

- `document/`: ไฟล์ `.md` และ `.txt` ที่นำเข้าเป็น guidance knowledge base
- `main_vector_database.py`: อ่าน config, แบ่งเอกสารตาม token, สร้าง embeddings และเขียนลง Chroma
- `result_vector_database.json`: JSON array ของ chunks แต่ละรายการมี `chunk_id`, `token` (จำนวน tokens) และ `content` (ข้อความเต็ม)
- `sources.json`: ข้อมูลที่มา สิทธิ์การใช้ และ `letter` ของ guidance documents
- `config_vector_database.json`: ตั้ง embedding model, collection, chunk size/overlap, batch size,
  query prefix, ตำแหน่งเอกสาร และตำแหน่ง Chroma database แต่ละตัวแปรอยู่หนึ่งบรรทัด
  โดยคอมเมนต์ `//` บรรทัดก่อนหน้าบอกค่าที่ใส่ได้และผลเมื่อเปลี่ยนค่า
  การเปลี่ยน model, ขนาด chunk หรือที่เก็บเอกสารต้องสร้าง index ใหม่และตรวจ
  `required_chunk` IDs อีกครั้ง เพราะ ID ที่คาดหวังอ้าง passages เดิม

Chunk ID ใช้ `letter` จาก `sources.json` ตามด้วยเลขลำดับ chunk เริ่มที่ 1 เช่น
`a1`, `a2`, `a3` มาจาก `nist_phishing.md`; `d1` มาจาก
`cisa_email_attachments.md` แต่ละเอกสารต้องมี letter a–z ไม่ซ้ำกัน
ชื่อสั้นและจำง่าย แต่ถ้าเปลี่ยนการแบ่ง chunk ต้องตรวจว่าเลขเดิมยังชี้ข้อความที่ต้องการ

รันจาก project root:

```bash
.venv/bin/python part2/vector_database/main_vector_database.py
```

Chroma database อยู่ที่ `part2/RAG/.chroma/`; การรัน `main_vector_database.py` จะอัปเดต
`part2/vector_database/result_vector_database.json` หลังสร้าง index สำเร็จ

## Guidance documents

`document/` มีไฟล์ guidance ระดับบน 7 ไฟล์ที่ถูกนำเข้า:

- `nist_phishing.md`: การรู้จักสัญญาณ phishing และการป้องกัน
- `nist_phish_scale_summary.md`: สรุป NIST Phish Scale และข้อกำหนด license
- `cisa_joint_phishing_guidance.md`: มาตรการป้องกันและตอบสนอง phishing จาก CISA/NSA/FBI/MS-ISAC
- `cisa_email_attachments.md`: ความเสี่ยงและการจัดการ email attachments
- `owasp_unvalidated_redirects.md`: การป้องกัน open redirect ที่นำไปใช้กับ phishing
- `apwg_q1_2026_summary.md`: แนวโน้ม phishing จากรายงาน APWG ไตรมาส 1 ปี 2026
- `google_spot_scams_summary.md`: สัญญาณ scam และการตอบสนองตามคำแนะนำของ Google

`sources.json` จอง letter `h` ให้ข้อมูลเสริม `extras/nist_multi_factor_authentication.md`;
`main_vector_database.py` ค้นเฉพาะไฟล์ระดับบน จึงไม่นำรายการใน subfolder เข้า index

## Retrieval check (`part2/RAG/`)

### `data.csv`

สำเนาพร้อม header และ 100 data rows แรกจาก `part2/part2_handoff.csv` ใช้เป็น
input สำหรับตรวจการค้นคืน โดยไฟล์ต้นฉบับไม่ถูกเปลี่ยน หลังรัน `main_RAG.py` จะมี
คอลัมน์ `chunk` เพิ่มขึ้น โดยเก็บ JSON array ของ `required_chunk` IDs ตามสถานการณ์
แต่ละ query อาจมีจำนวน required chunks ไม่เท่ากัน และไม่จำเป็นต้องมีครบ 5 รายการ

### `main_RAG.py`

อ่านข้อความอีเมลแต่ละแถวและเติมคำถามเพื่อหาแนวทาง action plan ที่เหมาะสม จากนั้น
เลือก `required_chunk` ตามตัวบ่งชี้ใน subject/body (เช่น credential/financial risk,
attachment หรือบริบทองค์กร) แยกจาก retrieval แล้ว embedding ด้วย model และ query
prefix ที่กำหนดใน vector database config เพื่อค้น chunks ที่ใกล้ที่สุด จำนวนผล
และคำถามตั้งใน `part2/RAG/config_RAG.json` โดยแต่ละตัวแปรอยู่หนึ่งบรรทัด
และคอมเมนต์ `//` บรรทัดก่อนหน้าบอกค่าที่ใส่ได้และผลเมื่อเปลี่ยนค่า
ค่า `max_email_chars` จำกัดเฉพาะข้อความที่ส่งเข้า embedding;
การเลือก `required_chunk` ยังดูอีเมลเต็ม BGE รุ่นนี้รับ input สูงสุด 512 tokens
แม้ค่า `max_email_chars` เป็น 0 และส่งข้อความยาวกว่านั้น

รันจาก project root:

```bash
.venv/bin/python part2/RAG/main_RAG.py
```

### `result_RAG.json`

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
ไม่ได้คัดลอกมาจากผล top-k ส่วน `top_retrieved_chunk` คือ IDs ที่ Chroma ค้นได้จริง
`score_chunk` คือ coverage percentage: จำนวน required IDs ที่พบใน top retrieved
หารด้วยจำนวน required IDs ทั้งหมด คูณ 100 คอลัมน์ CSV `chunk` เก็บเฉพาะ required
IDs ของแถวที่ `id` ตรงกับ `query_id`

### `.chroma/`

ฐานข้อมูล Chroma แบบ persistent เก็บ chunks, embeddings และ metadata ที่สร้างโดย
`main_vector_database.py`; เป็น generated data และถูก Git ignore

## Action-plan generation (`part2/LLM/`)

`config_LLM.json` มีเฉพาะค่าที่ปรับได้: prompt, generation options, ความยาวสูงสุด
ของ body ที่ส่งให้ LLM และ timeout โดยแต่ละตัวแปรอยู่หนึ่งบรรทัดและมีคอมเมนต์ `//`
บรรทัดก่อนหน้าบอกค่าที่ใส่ได้และผลเมื่อเปลี่ยนค่า ทั้งสามไฟล์ config รองรับคอมเมนต์
เต็มบรรทัดเท่านั้น จึงต้องอ่านผ่าน `main_*.py` ไม่ใช่ตัวอ่าน JSON มาตรฐาน URL และชื่อโมเดล
ไม่อยู่ใน config; `main_LLM.py` ใช้ local Ollama และ 4 โมเดลเดิม:
`llama3.1:8b`, `mistral:7b`, `qwen2.5:7b`, `phi3:mini`

`main_LLM.py` อ่านอีเมลจาก `part2/data.csv` ใช้ `top_retrieved_chunk` ใน `part2/RAG/result_RAG.json`
เพื่อดึงเนื้อหา guidance จาก `.chroma/` แล้วส่ง prompt เดียวกันและค่า generation
เดียวกันให้ทั้ง 4 โมเดลผ่าน Ollama รันจาก project root:

```bash
.venv/bin/python part2/LLM/main_LLM.py
```

ใช้ `--prompt "..."` เพื่อแทน prompt ใน config ชั่วคราว และ `--limit N` เพื่อทดลอง
กับ N แถวแรก ผลลัพธ์อยู่ใน `part2/LLM/result_LLM.json` เป็น JSON array มี `id`,
`subject`, `body` และ `model1` ถึง `model4` โดยแต่ละ model มีชื่อรุ่นและ
`action_plan` ของตัวเอง โปรแกรมบันทึกผลหลังคำตอบแต่ละครั้ง; ถ้ารันไม่จบ
`result_LLM.json` จะยังมีบาง model ที่ไม่มีคำตอบ

ค่า `temperature`, `top_p`, `top_k`, `repeat_penalty`, `seed`, `num_ctx` และ
`num_predict` เป็น Ollama runtime options ใช้ API เดียวกันทั้งสี่โมเดล แต่ผลของ
แต่ละค่าอาจต่างกัน ค่า `num_ctx` ที่ตั้งร่วมกันไม่ควรเกิน 32,768 สำหรับโมเดล
ที่ติดตั้งอยู่ เพราะ Mistral และ Qwen รองรับ 32,768 ส่วน `stop` เป็น token
เฉพาะโมเดลจึงไม่เปิดเป็นค่าร่วม อ้างอิง [Ollama parameters](https://docs.ollama.com/modelfile),
[Ollama chat API](https://docs.ollama.com/api/chat), [BGE model card](https://huggingface.co/BAAI/bge-large-en-v1.5)
และ [Chroma query docs](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## Other project files

- `README.md`: ภาพรวมและวิธีใช้โปรเจกต์
- `CONTEXT.md`: glossary ของ handoff email, guidance document, chunk และ index
- `requirements-part2.txt`: dependencies ของ ChromaDB และ Sentence Transformers
- `.gitignore`: ระบุไฟล์ local/generated ที่ไม่ควร commit
- `.venv/`: Python environment ในเครื่อง ไม่ใช่ source code
- `.git/`: ประวัติและ metadata ของ Git
