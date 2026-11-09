# MED-01: Email selling medicine without a prescription or at very low prices

| Field | Value |
|---|---|
| Group | MED |
| Layer | 1 Story |
| Word count | 70 |
| Primary source | S06 |
| All sources | S06 |
| Gold use (100 rows) | 31 rows, first chunk in 31 |

## Text

> Unsolicited emails offering prescription drugs with no prescription, very large discounts, or shipping from abroad are warning signs of unsafe online pharmacies. Sites that copy the look of a real shop are also common. Products may be fake, contaminated or wrong, and your card details may be misused. Do not buy through the email. Delete it, and talk to your doctor or a local pharmacist if you need the medicine.

## Embedded string (`embed_text`)

```
Email selling medicine without a prescription or at very low prices. Unsolicited emails offering prescription drugs with no prescription, very large discounts, or shipping from abroad are warning signs of unsafe online pharmacies. Sites that copy the look of a real shop are also common. Products may be fake, contaminated or wrong, and your card details may be misused. Do not buy through the email. Delete it, and talk to your doctor or a local pharmacist if you need the medicine.
```

## When to assign (labeling rules v1.5)

- **Assign when:** Advertises drugs, pills or supplements with health claims (ED, weight loss, enhancement, "meds")
- **Do not assign when:** Non-medical products
- **Fit:** Sold like medicine or by a pharmacy = good; enhancement patches or supplements with no pharmacy framing = partial.

## Sources

### S06 (primary): Navigating the world of online pharmacies (Q&A)

- **Publisher:** US FDA
- **URL:** https://www.fda.gov/drugs/news-events-human-drugs/navigating-world-online-pharmacies-cdr-lysette-deshields
- **Page date:** no date shown
- **Licence:** Not copyrighted; public domain unless otherwise noted (risk: low). Attribution: Not required by the policy as read; cite the page. Caveat: Check the page has no third-party material.
- **Why this topic matters:** USTR 2024 Notorious Markets report as reported by CBS (9 Jan 2025): of about 35,000 online pharmacies, 96% broke the law and about 20 new illegal sites appear daily ([CBS News](https://www.cbsnews.com/amp/texas/news/online-pharmacies-illegal-selling-ineffective-drugs); the USTR report itself was not opened). Historically, pharmaceutical spam was about 59.1% of all spam in Jan 2011 and up to 85% in May 2010 ([Dark Reading on MessageLabs](https://www.darkreading.com/cyber-risk/symantec-low-spam-levels-a-result-of-shifts-in-botnets-pharmaceutical-spam-gangs))
- **Weaknesses:** Justified by health-safety risk and distinct official guidance, not by current frequency: the FTC 2024 category list does not mention pharmacy. Spam figures are old

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
