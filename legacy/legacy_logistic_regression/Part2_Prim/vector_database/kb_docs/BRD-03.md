# BRD-03: Email that asks for passwords, card numbers or other sensitive details

| Field | Value |
|---|---|
| Group | BRD |
| Layer | 2 Mechanism |
| Word count | 73 |
| Primary source | S02 |
| All sources | S02 |
| Gold use (100 rows) | 9 rows, first chunk in 0 |

## Text

> Be very careful with any email that asks you to send or type sensitive information such as a password, a card number, a national ID number or bank details. Treat the request itself as a warning sign, especially when the sender is unfamiliar. Do not answer with the details. Confirm the request through a separate channel you already trust, such as a phone number from the organisation's official website, before you share anything.

## Embedded string (`embed_text`)

```
Email that asks for passwords, card numbers or other sensitive details. Be very careful with any email that asks you to send or type sensitive information such as a password, a card number, a national ID number or bank details. Treat the request itself as a warning sign, especially when the sender is unfamiliar. Do not answer with the details. Confirm the request through a separate channel you already trust, such as a phone number from the organisation's official website, before you share anything.
```

## When to assign (labeling rules v1.5)

- **Assign when:** Asks the reader to send, type, confirm or supply passwords, card numbers, ID numbers, bank account or personal details. Includes claim forms, "contact the agent with your details", and forms or card details asked for to order, apply or qualify in an advert ("fill in this short form", "send your card number and expiry date")
- **Do not assign when:** No such request; a plain "order now" or "call us"

## Sources

### S02 (primary): Phishing (Small Business Cybersecurity Corner)

- **Publisher:** NIST
- **URL:** https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing
- **Page date:** published 2021-10-22; updated 2025-08-19
- **Licence:** Public information unless marked as copyrighted (risk: low). Attribution: Credit requested. Caveat: Check the page carries no copyright marking.
- **Why this topic matters:** Verizon DBIR 2025: phishing was 16% of breaches and the third most common initial-access vector; about 60% of breaches involve the human element ([HIPAA Journal summary](https://www.hipaajournal.com/verizon-dbir-2025/))
- **Weaknesses:** Aimed at small businesses; reuse terms not verified; the statistic is from a third party

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
