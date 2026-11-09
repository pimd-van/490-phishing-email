# LNK-01: Email with a link whose destination you cannot confirm

| Field | Value |
|---|---|
| Group | LNK |
| Layer | 2 Mechanism |
| Word count | 62 |
| Primary source | S03 |
| All sources | S03 |
| Gold use (100 rows) | 61 rows, first chunk in 0 |

## Text

> Before clicking a link in an email, hover your mouse over it, or press and hold on a phone, to see the real web address. If it does not match what the text says or the sender's organisation, or the address looks odd or misspelled, do not click. Instead, open the organisation's website yourself by typing its address or using a bookmark.

## Embedded string (`embed_text`)

```
Email with a link whose destination you cannot confirm. Before clicking a link in an email, hover your mouse over it, or press and hold on a phone, to see the real web address. If it does not match what the text says or the sender's organisation, or the address looks odd or misspelled, do not click. Instead, open the organisation's website yourself by typing its address or using a bookmark.
```

## When to assign (labeling rules v1.5)

- **Assign when:** `urls` is not empty AND `fit` is not `none` AND at least one URL leads to the offer or the lure. Click wording is not needed: a shop, product, company or offer URL counts even when the text only names it or the subject alone carries the lure
- **Do not assign when:** `urls` empty; `fit` = none; every URL is a signature, webmail footer, image, unsubscribe or reference link (for example w3.org, join.msn.com, a logo .gif)
- **Constraint:** Never together with LNK-02.

## Sources

### S03 (primary): Protect yourself from phishing

- **Publisher:** Microsoft Support
- **URL:** https://support.microsoft.com/en-us/security/protect-yourself-from-phishing
- **Page date:** last updated 2026-09-11 (as seen)
- **Licence:** (c) Microsoft; Terms of use allow personal, non-commercial use of Documents without modification (risk: medium). Attribution: Keep the (c) Microsoft notice with the citation. Caveat: support.microsoft.com not named in the terms; chunks are paraphrases; author decided to keep the source; confirm with the advisor before publishing.
- **Why this topic matters:** Kaspersky blocked over 893 million phishing attempts in 2024, up 26% from about 710 million, often impersonating well-known brands ([Kaspersky, 19 Feb 2025](https://www.kaspersky.com/about/press-releases/2025_kaspersky-reports-nearly-900-million-phishing-attempts-in-2024-as-cyber-threats-increase)). This supports brand impersonation in general; no Microsoft-specific statistic was found
- **Weaknesses:** Commercial vendor; copyright terms unverified; keep chunks paraphrased

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
