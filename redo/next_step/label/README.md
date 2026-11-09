# กติกาติด label

ใช้ [Prim v1.13](labeling_rules_v1.13.md) เป็นฉบับอ้างอิง มี [ฉบับภาษาไทย](labeling_rules_v1.13_TH.md) สำหรับอ่านประกอบ ใช้ [ข้อความคู่มือ](../vector_database/document/) และ [รหัส chunk](../vector_database/sources.json) ชุดเดียวกับ RAG

ไฟล์ผล final `gold.jsonl` ใช้หนึ่ง JSON object ต่ออีเมล โดยเก็บ `id` กับ `chunk_ids` จากคำตอบ v1.13 หากผลติด label ระบุ `fit: none` ให้ใช้ `chunk_ids: []` เก็บเหตุผลจากรอบทดลองแยกจากไฟล์ final
