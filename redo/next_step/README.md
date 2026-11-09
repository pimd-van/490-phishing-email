# พื้นที่ทำงาน Part 2

อ่าน [แผนงาน](next_step.md) และใช้ [sample_10per.csv](../dataset/sample_10per.csv) เป็นชุดติด label 633 แถวจาก [master MeaJoR.csv](../dataset/MeaJoR.csv)

- [label/](label/README.md) มีคำสั่งติด label ของ Prim v1.13 และรูปแบบไฟล์เฉลย
- [vector_database/](vector_database/) มีข้อความคู่มือ 20 chunks, รายการรหัส และโค้ดสร้าง Chroma
- [rag/](rag/) มี config และโค้ดค้นคืนคู่มือ
- [local_llm/](local_llm/) มี config และโค้ดสร้างแผนรับมือผ่าน Ollama

รันจาก root ของ repo ด้วย Python environment ที่มี dependencies ตาม [requirements.txt](requirements.txt)

```bash
python -m pip install -r redo/next_step/requirements.txt
python redo/next_step/vector_database/main_vector_database.py
python redo/next_step/rag/main_RAG.py
python redo/next_step/local_llm/main_LLM.py --limit 5
```

เมื่อมีเฉลยสำหรับชุดวัดผล ให้เพิ่ม `--labels redo/next_step/label/gold.jsonl` ในคำสั่ง RAG แต่ละบรรทัดของเฉลยมี `id` และ `chunk_ids` ตามกฎ v1.13 ผลค้นจะบันทึกลงใน `rag/result_RAG.json` ส่วนแผนรับมือจะอยู่ใน `local_llm/result_LLM.json`
