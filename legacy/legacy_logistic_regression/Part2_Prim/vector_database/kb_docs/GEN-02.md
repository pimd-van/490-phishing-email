# GEN-02: A short routine for checking any suspicious email

| Field | Value |
|---|---|
| Group | GEN |
| Layer | Runtime fallback only |
| Word count | 68 |
| Primary source | S02 |
| All sources | S02 |
| Gold use (100 rows) | 0 rows, first chunk in 0 |

## Text

> Use a simple routine for any email that feels wrong. Stop and look at the sender's address, the greeting and the wording. Do not click links or open attachments. Check the claim through a separate channel you already trust, such as an official website or phone number. If it still looks suspicious, report it and delete it. When in doubt, ask someone you trust or your IT team.

## Embedded string (`embed_text`)

```
A short routine for checking any suspicious email. Use a simple routine for any email that feels wrong. Stop and look at the sender's address, the greeting and the wording. Do not click links or open attachments. Check the claim through a separate channel you already trust, such as an official website or phone number. If it still looks suspicious, report it and delete it. When in doubt, ask someone you trust or your IT team.
```

## When to assign (labeling rules v1.5)

- **Assign when:** Never a gold label; used by the runtime fallback (section 11)
- **Do not assign when:** Always

## Sources

### S02 (primary): Phishing (Small Business Cybersecurity Corner)

- **Publisher:** NIST
- **URL:** https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing
- **Page date:** published 2021-10-22; updated 2025-08-19
- **Licence:** Public information unless marked as copyrighted (risk: low). Attribution: Credit requested. Caveat: Check the page carries no copyright marking.
- **Why this topic matters:** Verizon DBIR 2025: phishing was 16% of breaches and the third most common initial-access vector; about 60% of breaches involve the human element ([HIPAA Journal summary](https://www.hipaajournal.com/verizon-dbir-2025/))
- **Weaknesses:** Aimed at small businesses; reuse terms not verified; the statistic is from a third party

## Change history

- Never a gold label; returned by the runtime fallback when retrieval confidence is low.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
