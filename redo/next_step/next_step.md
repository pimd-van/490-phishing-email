# ส่งต่องาน Part 2: ติด label

## 1. ไฟล์ dataset อยู่ที่ไหน

อยู่ใน `redo/dataset/` ใช้ `id` เชื่อมข้อมูลทุกไฟล์ ดูวิธีเตรียมข้อมูลได้ใน [pipeline ของ Part 1](../part1/README.md)

- [sample_10per.csv](../dataset/sample_10per.csv) **633 แถว** ไม่มีคอลัมน์ `label` ต้นฉบับ ใช้สำหรับงานนี้
- [MeaJoR.csv](../dataset/MeaJoR.csv) master **6,334 แถว** มีคอลัมน์ `label` ต้นฉบับ **ห้ามเปิดดูหรือส่งให้โมเดลระหว่างติด label** เพื่อไม่ให้เสีย blind

## 2. ให้โฟกัสการ label ก่อน

ตอนนี้โฟกัสการติด label ให้จบก่อน โดยใช้ [กฎ Prim v1.13](label/labeling_rules_v1.13.md) ที่มีอยู่ ([ฉบับภาษาไทย](label/labeling_rules_v1.13_TH.md) สำหรับอ่านประกอบ) และดูรูปแบบไฟล์เฉลยใน [label/README.md](label/README.md)

## 3. สร้าง CSV 2 แบบ

สร้างใน `redo/next_step/label/` โดย copy จาก sample 10% ทั้ง 633 แถว แล้วเพิ่มคอลัมน์ `round` (`trial`/`final`), `batch_id` และคอลัมน์ label

**แบบที่ 1 `label_gold.csv` (เฉลย/ต้นทางสำหรับเปรียบเทียบ)**

- ผู้ทำติด label เองก่อน จะให้ AI ของตัวเองช่วยก็ได้
- รีวิวไปพร้อมกับ **Opus 5.5 Medium** ว่าแต่ละจุดควรเป็นอย่างไร ผู้ทำเป็นคนตัดสินสุดท้าย
- ต้องได้ต้นทางนี้ก่อนจึงไปแบบที่ 2

**แบบที่ 2 `label_sonnet.csv`**

- เมื่อได้ต้นทางแล้ว ให้ **Sonnet 5.5 Medium** ติด label ด้วยกฎชุดเดียวกัน
- ไม่ให้เห็นเฉลยแบบที่ 1 และไม่นำผล Sonnet ไปปรับเฉลยในรอบ final

**คอลัมน์ label**

- ขั้นต่ำต้องมี `chunk_ids` แนะนำให้เก็บเป็น JSON array เช่น `["INV-01","SPM-03"]` แถวที่ไม่มี chunk ใช้ `[]` ส่วนช่องว่างหมายถึงยังไม่ได้ติด label
- จะเก็บอย่างอื่น เช่น `fit` ให้เป็นไปตามสมควร ผู้เขียนไฟล์นี้ยังไม่เข้าใจแนวคิด good/partial จึงยังไม่กำหนดตายตัว ให้ผู้ทำอ่านกฎข้อ 7 แล้วพิจารณา และบันทึกสิ่งที่เลือก

## 4. วิธีใช้ subagent

ทำใน **Claude Code**

- สร้าง subagent หลายตัวได้ แต่ **1 subagent ทำ 1 รอบเท่านั้น** รอบละ 25 แถว จะ label รอบอื่นให้สร้างตัวใหม่ **ห้ามใช้แบบ fork** เพราะรับประวัติแชต
- สิ่งที่ส่งให้ subagent มีแค่ dataset ของรอบนั้น คำสั่ง (รวมกฎ) และ tools
- ส่งเฉพาะ `id`, `subject`, `body`, สรุป `urls` ของ batch นั้น ห้ามให้เห็น CSV เต็ม (มี `source`, `xai`, `svm_result`), เฉลย, ผลรอบอื่น, repo ส่วนอื่น หรือเว็บ
- กำหนด tools ให้น้อยที่สุด ถ้าทำได้ไม่ให้ tool เลย แล้วส่ง data กับกฎใน prompt
- ผู้ทำต้องตรวจในรอบทดลองว่า subagent ไม่เห็นข้อมูลอื่นจริง

ข้อจำกัดของ Claude Code ที่ต้องจัดการ (จากเอกสาร `code.claude.com/docs/en/sub-agents`):

- ถ้าไม่ใส่ `tools` subagent จะได้ tool ทั้งหมด เอกสารไม่มีวิธีตั้งแบบไม่มี tool เลย และถ้า `tools` ไม่เหลือ tool ที่ใช้ได้มักเปิดไม่ขึ้น (`spawned with zero tools`) ถ้าเจอกรณีนี้ให้ใส่ tool น้อยที่สุด แล้วตรวจ transcript ว่าไม่มีการเรียกใช้
- subagent ได้ `CLAUDE.md`, working directory และ git status มาด้วย ให้ตั้ง `omitClaudeMd: true` และเปิด session จากโฟลเดอร์ว่างนอก repo ที่ไม่ใช่ git
- Claude Code โหลด definition จาก `.claude/agents/` หรือ `--agents` เท่านั้น ไฟล์ใน `label/` เป็นต้นฉบับ ตอนใช้ให้ copy ไปที่ `.claude/agents/` ของโฟลเดอร์ที่เปิด session

ไฟล์สำหรับการส่งเพื่อทำซ้ำได้ เก็บใน `redo/next_step/label/` (ชื่อเป็นคำแนะนำ)

- ไฟล์ batch แต่ละรอบ: `batches/<batch_id>.jsonl`
- คำสั่งรอบทดลอง: `prompt_trial.md`
- คำสั่งรอบเทสจริง: `prompt_final.md`
- agent definition: `agent_labeler_sonnet.md` ระบุ `model: claude-sonnet-5-5`, `effort: medium` และ tools ที่อนุญาต

คำสั่งแต่ละแบบ

- **รอบทดลอง:** ให้ subagent บอกเหตุผลที่ติด label ได้ เก็บเหตุผลแยกจากไฟล์ final
- **รอบเทสจริง:** ให้ติด label อย่างเดียว ไม่ต้องมีเหตุผล คำสั่งรอบนี้ต้องระบุว่า **override ข้อ 9 และ 13 ของกฎเรื่อง `chunk_rationale` และ `email_summary`** รวมถึงการเขียนหมายเลข marker ลง `chunk_rationale`

## 5. การแบ่งรอบ

ไฟล์ sample เรียงตาม cluster 25 แถวแรกเป็น cluster 1 ทั้งหมด จึง**ห้ามตัดตามลำดับ** ให้สุ่มแบบนี้จาก repo root

```python
import csv, random
with open("redo/dataset/sample_10per.csv", encoding="utf-8-sig", newline="") as f:
    ids = [row["id"] for row in csv.DictReader(f)]  # ตามลำดับไฟล์
random.Random(42).shuffle(ids)
```

| รอบ | แถวหลังสุ่ม | จำนวน | `batch_id` |
|---|---|---|---|
| ทดลอง | 50 แถวแรก | 2 รอบ รอบละ 25 | `trial_01`, `trial_02` |
| เทสจริง | 583 แถวที่เหลือ | 24 รอบ (23 รอบเต็ม รอบละ 25 และรอบสุดท้าย 8 แถว) | `final_01` ถึง `final_24` |

- ตรวจการสุ่มได้จาก `id` แรกของ `trial_01` ต้องเป็น `meajor_en_v1_test_80468`
- บันทึกการแบ่งเป็นไฟล์ เช่น `split.csv` (`id`, `round`, `batch_id`)
- แถวทดลองไม่นับในผล final
- ปรับกฎ/คำสั่งได้จากรอบทดลองเท่านั้น แล้วล็อกก่อนเทสจริง ถ้ากฎเปลี่ยน ให้ทบทวน `label_gold.csv` แถวที่กระทบให้ตรงกฎที่ล็อกก่อนเริ่มเทสจริง

## 6. ส่วนที่ต้องเจอก่อน

- **หาอะไรไม่เจอ:** ให้ AI ไปค้นใน `legacy/` ก่อน ไฟล์บางอย่างอยู่ที่นั่นเท่านั้น เช่น `human_review_possible_minors.csv` ซึ่งไม่ได้ copy มาที่ `redo/Part2_Prim`
- **กฎเขียนสำหรับรอบเก่า:** อ้าง `data.csv` และ `phishing_result` รอบนี้ใช้ `sample_10per.csv` และ `svm_result` ตัวอย่างในกฎใช้ ID `meajor_test_*` ส่วนชุดนี้เป็น `meajor_en_v1_test_*`
- **gold เก่าใช้ไม่ได้:** gold 100 แถวและ [gold.csv เก่าใน legacy](../../legacy/legacy_logistic_regression/Part2_Prim/labels/gold.csv) ใช้กฎ/ID คนละชุด ไม่นำมาเป็นเฉลยรอบนี้ และยังไม่ได้ยืนยันการ map ID ข้อกำหนดข้อ 13 เรื่องฝัง gold 100 แถวจึงใช้ `label_gold.csv` แทน
- **[profile_caps.py](../../legacy/legacy_logistic_regression/Part2_Prim/labels/profile_caps.py):** ใช้สร้างสรุป `urls` และ cap ของ body ผลลัพธ์มีเฉพาะ `id`, `subject`, `body`, `truncated` และฟิลด์สรุป `urls` ใช้ตัดเป็นไฟล์ batch ได้ คำสั่งจาก repo root

  ```bash
  python legacy/legacy_logistic_regression/Part2_Prim/labels/profile_caps.py redo/dataset/sample_10per.csv --params redo/next_step/label/params.json --out redo/next_step/label/model_input.jsonl
  ```

  ทดสอบกับ sample แล้วได้ BODY_CAP 6,500 (ตัด 5 แถว) และ URL_CAP 9 (26 แถวเกิน cap) รูปแบบ `urls` ใช้ได้ และจะขึ้นเตือนว่าค่าเป็นชั่วคราวเพราะต่ำกว่า 1,000 แถว
- **ลักษณะข้อความ:** ตัวพิมพ์เล็กทั้งหมด มี token แทนข้อมูล เช่น `token_url`, `token_name` 232 จาก 633 แถวมี `<|email_separator|>` และ 56 แถวในนั้นทุกส่วนซ้ำกัน 5 แถว subject ว่าง 127 แถว `urls` ว่าง ไม่มีไฟล์แนบใน sample และกฎให้ตัดสิน `ATT-01` จากข้อความเท่านั้น
- **กรณี C38 (อาจเกี่ยวกับสื่อทางเพศของผู้เยาว์):** `uncertain` และ `uncertain_reason` ไม่อยู่ใน schema ข้อ 9 ต้องเพิ่มในรูปแบบผล ให้หยุดแถวนั้นและส่งให้มนุษย์ตรวจและรายงาน ไม่ส่งต่อเป็นแถว label ปกติ
- **`source_rationale.md` ที่กฎอ้าง** อยู่ที่ [legacy](../../legacy/legacy_logistic_regression/Part2_Prim/vector_database/source_rationale.md)
- **ตรวจผลทุกรอบตามข้อ 13 ของกฎ:** ID ครบไม่ซ้ำ รหัสอยู่ใน [catalog](vector_database/sources.json) ไม่มี `GEN-02` เป็นต้น รอบเทสจริงไม่ต้องตรวจ `chunk_rationale` และถ้าไม่เก็บ `fit` ให้ข้ามข้อที่ต้องใช้ `fit` แล้วบันทึกไว้

## 7. งานหลัง label

ยังมี RAG, Local LLM และการขยายไป master รายละเอียดเจ้าของงานจะเพิ่มเอง ดู [rag/main_RAG.py](rag/main_RAG.py) และ [local_llm/main_LLM.py](local_llm/main_LLM.py)

**แนวทาง RAG (แนวคิดตั้งต้น ยังไม่ใช่ข้อสรุป)**

เมื่อติด label เสร็จ ขั้นต่อไปคือการใช้ RAG คิดว่าคงใช้ metric **recall** เหมือนเดิม (คือ `score_chunk` ใน [rag/main_RAG.py](rag/main_RAG.py)) ส่วนจำนวนที่ retrieve มีให้เลือก 2 ทาง

1. เอามา 5 ตัวเหมือนเดิม (`top_k: 5` ใน [rag/config_RAG.json](rag/config_RAG.json))
2. เอามา 5 ตัวหรือ n ตัว แล้วตัด chunk ตาม logic ที่เขียนไว้ใน[กฎ Prim v1.13](label/labeling_rules_v1.13.md) หรือใช้คะแนนความคล้าย หรือ reranking ก็ได้

หมายเหตุ: `main_RAG.py` รับ `gold.jsonl` (`id`, `chunk_ids`) จึงต้องแปลงจาก CSV และ RAG/LLM ปัจจุบันยังไม่ส่ง `urls`

**แนวทาง Local LLM (แนวคิดตั้งต้น ยังไม่ใช่ข้อสรุป)**

Local LLM ต้องอธิบายว่าอีเมลนี้มีเป้าหมายอะไร และให้ action plan ว่าผู้รับควรทำอะไรต่อ [Part2_Prim](../Part2_Prim/README_part2.md) และ [rubric](../Part2_Prim/LLM/human_eval/rubric_TH.md) เอามาให้ดูเป็นตัวอย่างว่างานก่อนเคยทำอย่างไร จึงไม่ต้องสนใจ path ในไฟล์เหล่านั้น

สรุปการประเมิน

| องค์ประกอบ | สิ่งที่ตรวจ |
|---|---|
| Experimental Design | ทุกโมเดลตอบอีเมลชุดเดียวกัน, เทียบ `rag` / `oracle` / `no_rag`, ล็อกค่าก่อนเทส, กำหนดกติกาตัดสินก่อนเห็นผล |
| Retrieval Evaluation | Recall@k, Hit@1, MRR, nDCG@k, Context Precision และเทียบกับ popularity baseline |
| Output Validity | **Schema compliance rate**, invalid citation rate, truncation rate |
| Intent Explanation | **Intent identification accuracy**, **Source fidelity**, feature alignment กับ SHAP/LIME |
| Groundedness | Claim-level faithfulness, **Hallucination rate**, citation precision/recall/F1, **Attribution accuracy** |
| **Response Quality** | ให้คะแนนตาม rubric แบบ 1/3/5: Correctness, Completeness, Actionability, Relevance, Readability |
| Safety | Safety gate, unsafe recommendation rate, prompt-injection compliance rate |
| **Abstention and Robustness** | Negative rejection, abstention precision/recall, false abstention rate, noise robustness, test-retest consistency |
| Annotation and Inference | Blind scoring, inter-rater reliability, ตรวจ LLM judge เทียบกับคน, สถิติแบบจับคู่, กติกาจัดอันดับ, reproducibility |
| Supplementary Metrics | ROUGE-L, BERTScore, RAGAS Faithfulness, Response Relevancy |

ความเห็นเจ้าของงาน: สิ่งที่สำคัญคือ

- **Schema compliance rate:** คำตอบมีโครงสร้างถูกตามกำหนด
- **Intent identification accuracy:** บอกเป้าหมายของอีเมลถูกต้อง
- **Source fidelity:** คำอธิบายยึดตามเนื้อหาอีเมล ไม่แต่งเพิ่ม
- **Hallucination rate:** ข้อความที่แต่งขึ้นหรือไม่มีหลักฐานต้องน้อย
- **Attribution accuracy:** แต่ละขั้นตอนอ้างถูก chunk
- **Response Quality:** คำตอบถูก ครบ ทำตามได้จริง ตรงกับอีเมล และอ่านเข้าใจง่าย
- **Abstention and Robustness:** ไม่ฝืนตอบเมื่อไม่มีข้อมูล และยังตอบได้ดีเมื่อมีข้อมูลรบกวน

ขั้นตอนรอบนี้

1. ทดสอบกับ [sample 633 แถว](../dataset/sample_10per.csv) ชุดเดิมก่อน เพื่อทำ prompt ที่ LLM ทั้ง 4 ตัวใช้ร่วมกัน
2. เจ้าของงานแนะนำว่า prompt ไม่ควร specific ควรอธิบายแบบ general ไม่เจาะจงไปที่คำใดคำหนึ่ง แต่เน้นสิ่งที่เจอหรือสิ่งที่เกี่ยวข้อง
3. เมื่อได้ prompt แล้วให้ล็อก และเทสจริงกับทั้งหมด เวลารายงานผลให้แยก 633 แถวที่ใช้ปรับ prompt ออกมา
4. ให้ **Sonnet 5.5 Medium** ตรวจเหมือนเดิม คือใช้ subagent 1 ตัวต่อ 1 รอบ รอบละ 25 แถว และให้เห็นเฉพาะข้อมูลกับเกณฑ์ที่ต้องใช้

ข้อกังวลเรื่องปริมาณงาน: เทส 4 โมเดลกับ master 6,334 แถวจะได้ 25,336 คำตอบ ถ้า Sonnet ตรวจรอบละ 25 คำตอบจะเป็นประมาณ 1,014 รอบ และถ้ารันครบ `rag` / `oracle` / `no_rag` จะเป็น 3 เท่า ควรเช็กเวลากับโควตาตั้งแต่รอบ 633 แถว เจ้าของงานคิดว่า `rag` / `oracle` / `no_rag` อาจไม่จำเป็นต้องมี ให้ผู้ทำตัดสินใจเอง

## 8. การปล่อยรัน label และตรวจ Local LLM

- ตอนปล่อยรัน label หรือตรวจ Local LLM ให้ตั้งให้กลับมาทำงานต่อเมื่อ token reset
- ใช้ Claude จาก VS Code และ CLI ทำ label แบบ parallel ไปพร้อมกัน โดยใช้คนละ account
- แบ่ง batch ให้แต่ละฝั่งไม่ซ้ำกัน และเก็บผลแยกไฟล์ต่อ batch เพื่อทำต่อจาก batch ที่ค้างได้
