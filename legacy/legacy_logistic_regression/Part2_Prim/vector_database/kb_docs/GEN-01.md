# GEN-01: How to report a suspicious email and who to tell

| Field | Value |
|---|---|
| Group | GEN |
| Layer | 4 After and reporting |
| Word count | 86 |
| Primary source | S04 |
| All sources | S04, S01 |
| Gold use (100 rows) | 9 rows, first chunk in 0 |

## Text

> Report a suspicious email instead of just deleting it. Use the report phishing or report spam option in your email service, and forward it to your country's official phishing-reporting service if one exists. Also tell the organisation being impersonated, and your IT or security team for workplace mail. Include the full message or a screenshot, do not click anything while reporting, and do not reply to the sender. If you lost money or shared personal information, also report it to the police or your consumer-protection agency.

## Embedded string (`embed_text`)

```
How to report a suspicious email and who to tell. Report a suspicious email instead of just deleting it. Use the report phishing or report spam option in your email service, and forward it to your country's official phishing-reporting service if one exists. Also tell the organisation being impersonated, and your IT or security team for workplace mail. Include the full message or a screenshot, do not click anything while reporting, and do not reply to the sender. If you lost money or shared personal information, also report it to the police or your consumer-protection agency.
```

## When to assign (labeling rules v1.5)

Assign when the layer-1 story is BRD-01, BRD-02, ADV-01 or STR-01 (fraud notices rather than adverts). Do not assign when the story is MED-01, INV-01 or JOB-01 or when there is no story.
- **Constraint:** Only when the story chunk is BRD-01, BRD-02, ADV-01 or STR-01.

## Sources

### S04 (primary): Phishing: spot and report scam emails, texts, websites and calls

- **Publisher:** UK NCSC
- **URL:** https://www.ncsc.gov.uk/collection/phishing-scams
- **Page date:** no date shown
- **Licence:** Crown copyright under Open Government Licence v3.0 (risk: low). Attribution: Required: acknowledge the source and link to the OGL (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Caveat: Third-party images and logos excluded.
- **Why this topic matters:** NCSC's Suspicious Email Reporting Service had over 10.5 million reports and 76,000 scams taken down by March 2022 ([NCSC, 18 Mar 2022](https://www.ncsc.gov.uk/news/nation-of-digital-defenders-blow-the-whistle-on-over-10-million-suspect-emails))
- **Weaknesses:** Figures are from 2022; UK reporting channels; the page was not re-read in the latest round

### S01 (secondary): How to Recognize and Avoid Phishing Scams

- **Publisher:** US Federal Trade Commission (consumer.ftc.gov)
- **URL:** https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams
- **Page date:** published 2019-05-03; modified 2024-10-11
- **Licence:** US federal government work; public domain for most website material (risk: low). Attribution: Requested where feasible. Caveat: Policy page does not name consumer.ftc.gov explicitly; third-party content excluded.
- **Why this topic matters:** FTC 2024 data: imposter scams were the most reported category ([FTC, Mar 2025](https://www.ftc.gov/news-events/news/press-releases/2025/03/new-ftc-data-show-big-jump-reported-losses-fraud-125-billion-2024)). FBI IC3 2024: about 193,000 phishing complaints, out of about 860,000 complaints and over $16 billion in losses ([Axios, 23 Apr 2025](https://axios.com/2025/04/23/fbi-internet-crime-loss-record-high-2024), secondary report)
- **Weaknesses:** US-centric. The page has no content on spam marking, prizes or money-transfer requests (checked)

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
