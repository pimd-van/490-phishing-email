# MED-02: Email from an online pharmacy inviting you to order medicine

| Field | Value |
|---|---|
| Group | MED |
| Layer | 2 Mechanism |
| Word count | 72 |
| Primary source | S06 |
| All sources | S06 |
| Gold use (100 rows) | 11 rows, first chunk in 0 |

## Text

> Before buying medicine online, check that the pharmacy requires a prescription, lists a real physical address and phone number, is licensed in your country and has a pharmacist you can speak to. When goods arrive, look for damaged packaging or expired products, and watch your card statement for charges you did not expect. If a seller breaks the rules or sends something you did not order, report it to your health authority.

## Embedded string (`embed_text`)

```
Email from an online pharmacy inviting you to order medicine. Before buying medicine online, check that the pharmacy requires a prescription, lists a real physical address and phone number, is licensed in your country and has a pharmacist you can speak to. When goods arrive, look for damaged packaging or expired products, and watch your card statement for charges you did not expect. If a seller breaks the rules or sends something you did not order, report it to your health authority.
```

## When to assign (labeling rules v1.5)

- **Assign when:** The email presents itself as an online pharmacy or drugstore and invites ordering (order, ship, pharmacy, licensed meds). Requires MED-01
- **Do not assign when:** Plain drug advertising; enhancement products with no pharmacy framing
- **Constraint:** Requires MED-01 in the same list.

## Sources

### S06 (primary): Navigating the world of online pharmacies (Q&A)

- **Publisher:** US FDA
- **URL:** https://www.fda.gov/drugs/news-events-human-drugs/navigating-world-online-pharmacies-cdr-lysette-deshields
- **Page date:** no date shown
- **Licence:** Not copyrighted; public domain unless otherwise noted (risk: low). Attribution: Not required by the policy as read; cite the page. Caveat: Check the page has no third-party material.
- **Why this topic matters:** USTR 2024 Notorious Markets report as reported by CBS (9 Jan 2025): of about 35,000 online pharmacies, 96% broke the law and about 20 new illegal sites appear daily ([CBS News](https://www.cbsnews.com/amp/texas/news/online-pharmacies-illegal-selling-ineffective-drugs); the USTR report itself was not opened). Historically, pharmaceutical spam was about 59.1% of all spam in Jan 2011 and up to 85% in May 2010 ([Dark Reading on MessageLabs](https://www.darkreading.com/cyber-risk/symantec-low-spam-levels-a-result-of-shifts-in-botnets-pharmaceutical-spam-gangs))
- **Weaknesses:** Justified by health-safety risk and distinct official guidance, not by current frequency: the FTC 2024 category list does not mention pharmacy. Spam figures are old

## Change history

- 2026-10-24: header changed from "Checking an online pharmacy before using it, and reporting a bad one" to describe the email; advice text unchanged. Re-embed.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
