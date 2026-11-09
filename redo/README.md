# SVM รอบอังกฤษ

- [Part 1 pipeline](part1/README.md) อธิบายการฝึก SVM และวิธีเลือกชุดตัวอย่าง
- [MeaJoR.csv](dataset/MeaJoR.csv) เป็น master 6,334 แถวที่ SVM ทำนายว่าเป็น phishing มีข้อความที่ preprocess แล้ว, XAI, label ต้นฉบับ และข้อมูล clustering
- [sample_10per.csv](dataset/sample_10per.csv) มี 633 แถวจาก master ตามสัดส่วนของทั้ง 60 กลุ่ม สำหรับติด label และทดสอบ RAG
- [แผนงาน Part 2](next_step/next_step.md) ครอบคลุมการติด label ทดสอบ RAG และเปรียบเทียบ Local LLM
