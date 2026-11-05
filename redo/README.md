# Redo: Part 1 text-only benchmark และ handoff จาก Linear SVM

โฟลเดอร์นี้รัน Part 1 แบบ text-only ใหม่ทั้งหมดบน VM 490-18 (5 พ.ย. 2026) เทียบ 7 โมเดล
แล้วเลือกโมเดลจาก validation F1 ผลคือ **Linear SVM** ได้ F1 สูงสุด จึงสร้าง handoff ชุดใหม่
จากอีเมลใน test set ที่ Linear SVM ทำนายว่าเป็น phishing แทน handoff เดิมที่มาจาก
Logistic Regression ([`part2/part2_handoff.csv`](../part2/part2_handoff.csv))

## ไฟล์ในโฟลเดอร์

| ไฟล์ | เนื้อหา |
|---|---|
| [`dataset/svm_handoff.csv`](dataset/svm_handoff.csv) | 6,995 อีเมลใน test set ที่ Linear SVM ทำนายว่าเป็น phishing |
| [`comparison/validation_metrics.csv`](comparison/validation_metrics.csv) | ผล validation ของ 7 โมเดลจากรอบ benchmark |
| [`comparison/summary.json`](comparison/summary.json) | รายละเอียดรอบ benchmark: MD5 ข้อมูล, จำนวนแถว, การแบ่งชุด, เวอร์ชันไลบรารี, ผล test |
| [`comparison/test_metrics.csv`](comparison/test_metrics.csv) | ผล validation และ test ของทุกโมเดล (test ใช้เพื่อรายงานเท่านั้น ไม่ได้ใช้เลือกโมเดล) |
| [`comparison/comparison_summary.json`](comparison/comparison_summary.json) | จำนวนแถวที่ SVM กับ handoff ของ LR ตรงและต่างกัน |
| [`comparison/svm_vs_lr_rows.csv`](comparison/svm_vs_lr_rows.csv) | รายชื่อ 191 แถวที่ SVM กับ LR ไม่ตรงกัน พร้อม label จริง |
| [`scripts/benchmark_text.py`](scripts/benchmark_text.py) | สคริปต์ benchmark 7 โมเดล (สร้าง `comparison/summary.json` และ `validation_metrics.csv`) |
| [`scripts/make_redo.py`](scripts/make_redo.py) | สร้าง `svm_handoff.csv`, `test_metrics.csv` และไฟล์เปรียบเทียบกับ LR |
| [`scripts/time_single_row.py`](scripts/time_single_row.py) | จับเวลาทำนาย 1 อีเมลของ SVM และ LR |

## การเตรียมข้อมูล

1. **แหล่งข้อมูล:** [MeAJOR v2.0](https://zenodo.org/records/18471483) ไฟล์ `meajor_cleaned_preprocessed.csv`
   (MD5 `aa8f59e96787cbd696c0b650e5400dc9`) label `0` = อีเมลปกติ, `1` = phishing
   ข้อมูลใช้สัญญาอนุญาต CC BY 4.0 ถ้าเผยแพร่ผลให้อ้างอิง Cardoso et al., DOI `10.5281/zenodo.18471483`
2. **เก็บเฉพาะ label 0/1** ตัดแถวที่ label ไม่ใช่ตัวเลขดังกล่าว
3. **ทำความสะอาดข้อความ** ทั้ง subject และ body:
   - แปลง placeholder ตัวพิมพ์ใหญ่ในวงเล็บเหลี่ยมที่ยาวอย่างน้อย 2 ตัว เช่น `[NAME]` เป็น ` token_name ` ก่อนแปลงเป็นตัวพิมพ์เล็ก
   - แปลงเป็นตัวพิมพ์เล็ก และยุบช่องว่างหลายช่องให้เหลือช่องเดียว
4. **รวมข้อความ** เป็น `subject + " " + body` แล้วตัดแถวที่ข้อความว่าง
5. **ตัดแถวซ้ำ** ที่ subject + body หลังทำความสะอาดเหมือนกัน เก็บแถวแรกไว้ เหลือ **104,515 แถว**
   (ปกติ 57,911 / phishing 46,604)
6. **แบ่งชุดข้อมูล** แบบ stratified ด้วย seed 42 เป็น 70/15/15

   | ชุด | แถว | ปกติ | phishing | ใช้ทำอะไร |
   |---|---:|---:|---:|---|
   | Train | 73,160 | 40,537 | 32,623 | fit TF-IDF และฝึกโมเดล |
   | Validation | 15,677 | 8,687 | 6,990 | เทียบโมเดลและเลือกตัวที่ได้ F1 สูงสุด |
   | Test | 15,678 | 8,687 | 6,991 | วัดผลหลังเลือกโมเดลแล้ว และใช้สร้าง handoff |

7. **TF-IDF** fit กับ train เท่านั้น: 5,000 features, unigram + bigram, `sublinear_tf=True`

## การเปรียบเทียบโมเดล

ทุกโมเดลใช้ค่า default ของ scikit-learn 1.6.1 / XGBoost 3.4.1 ไม่ได้ปรับ hyperparameter
เลือกโมเดลจาก **validation F1** (ถ้าเท่ากันดู precision แล้ว recall) ส่วนคอลัมน์ test แสดงไว้เพื่อรายงานเท่านั้น

| โมเดล | การตั้งค่า | Val F1 | Test F1 | Test FP | Test FN |
|---|---|---:|---:|---:|---:|
| **Linear SVM** | `LinearSVC()` | **0.9765** | **0.9765** | 166 | 162 |
| Random Forest | default, `random_state=42` | 0.9762 | 0.9744 | 132 | 224 |
| Logistic Regression | `LogisticRegression()` | 0.9744 | 0.9726 | 183 | 200 |
| KNN | k=5, cosine, brute force | 0.9703 | 0.9684 | 229 | 213 |
| XGBoost | 100 trees, `hist`, `random_state=42` | 0.9660 | 0.9682 | 223 | 221 |
| Multinomial NB | default | 0.9455 | 0.9447 | 259 | 501 |
| Decision Tree | default, `random_state=42` | 0.9224 | 0.9223 | 576 | 515 |

Linear SVM ชนะ Random Forest บน validation ด้วยส่วนต่างเพียง 0.0003 แต่บน test ยังได้ F1 เท่าเดิม
(0.9765) แสดงว่าไม่ได้ overfit กับ validation ผลนี้ต่างจาก
[Part 1 text-only recheck](../docs/part1_text_only_recheck.md) ที่เทียบเพียง 4 โมเดล
และเลือก Logistic Regression

### เวลาทำนาย 1 อีเมล (CPU ของ VM 490-18, median จาก 2,000 อีเมล)

| ขั้นตอน | Linear SVM | Logistic Regression |
|---|---:|---:|
| ทำความสะอาดข้อความ | 0.07 ms | 0.07 ms |
| แปลง TF-IDF | 0.53 ms | 0.53 ms |
| predict | 0.13 ms | 0.13 ms |
| **รวม** | **0.73 ms** | **0.72 ms** |

## Handoff ของ SVM เทียบกับ handoff เดิมของ LR

| | แถว |
|---|---:|
| handoff เดิม (LR ทำนายว่าเป็น phishing) | 6,972 |
| handoff ใหม่ (SVM ทำนายว่าเป็น phishing) | 6,995 |
| แถวเดียวกันทั้งสองชุด | **6,888** |
| อยู่ใน LR แต่ SVM ไม่ได้ทำนายว่าเป็น phishing | 84 (phishing จริง 31, ปกติจริง 53) |
| อยู่ใน SVM แต่ไม่อยู่ใน LR | 107 (phishing จริง 69, ปกติจริง 38) |

แถวที่ต่างกันทั้งหมดอยู่ใน [`comparison/svm_vs_lr_rows.csv`](comparison/svm_vs_lr_rows.csv)

## รูปแบบของ `svm_handoff.csv`

คอลัมน์เหมือน `part2/part2_handoff.csv` ทุกคอลัมน์ ยกเว้น `phishing_result` เปลี่ยนเป็น `svm_result`
และ `xai` เปลี่ยนวิธีคำนวณ ไม่มีคอลัมน์ label จริงเหมือนไฟล์เดิม

- `id` = `meajor_test_<ลำดับแถวหลังทำความสะอาดและตัดแถวซ้ำ>` ใช้รูปแบบเดียวกับ handoff เดิม
  แถวที่อยู่ทั้งสองชุดจึงมี `id` ตรงกัน
- `test_row` = ลำดับแถวใน test set นับจาก 0
- `svm_result` = `{"prediction": 1, "decision_score": ...}` โดย `decision_score` คือระยะจากเส้นแบ่งของ SVM
  ค่ายิ่งมากยิ่งมั่นใจว่าเป็น phishing `LinearSVC` ไม่มีค่าความน่าจะเป็น ถ้าต้องการต้อง calibrate เพิ่ม
- `xai` = ค่า TF-IDF × น้ำหนักของ SVM สำหรับ 5 คำที่ดันไปทาง phishing มากที่สุด
  (`top_positive_terms`) และ 5 คำที่ดันไปทางอีเมลปกติมากที่สุด (`top_negative_terms`)
  หน่วยเป็น margin ของ SVM ไม่ใช่ log-odds แบบไฟล์เดิม จึงเทียบตัวเลขกับไฟล์เดิมตรง ๆ ไม่ได้

## รันซ้ำ

ต้องมี `meajor_cleaned_preprocessed.csv` และติดตั้ง `pandas`, `numpy`, `scikit-learn==1.6.1`, `xgboost==3.4.1`
รันจากโฟลเดอร์ `redo/scripts`:

```bash
python benchmark_text.py --input /path/to/meajor_cleaned_preprocessed.csv --out ../comparison/benchmark_run
python make_redo.py --input /path/to/meajor_cleaned_preprocessed.csv --lr-handoff ../../part2/part2_handoff.csv --out ../comparison/redo_run
python time_single_row.py /path/to/meajor_cleaned_preprocessed.csv
```

`make_redo.py` ฝึกทั้ง 7 โมเดลใหม่ทุกครั้ง ใช้เวลาประมาณ 5 นาทีบน VM 490-18 (44 vCPU)
เพราะ benchmark เดิมไม่ได้บันทึกไฟล์โมเดลไว้
