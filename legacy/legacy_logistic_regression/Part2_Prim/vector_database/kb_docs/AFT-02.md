# AFT-02: You may have lost money to a phishing message

| Field | Value |
|---|---|
| Group | AFT |
| Layer | 4 After and reporting |
| Word count | 61 |
| Primary source | S03 |
| All sources | S03 |
| Gold use (100 rows) | 0 rows, first chunk in 0 |

## Text

> If money left your account because of a phishing message, contact your bank or card provider immediately and ask what can be done. Write down what happened, including dates, amounts and the sender's details, and keep the emails. Tell your workplace IT team if a work account was involved, and report the incident to the police or your country's fraud service.

## Embedded string (`embed_text`)

```
You may have lost money to a phishing message. If money left your account because of a phishing message, contact your bank or card provider immediately and ask what can be done. Write down what happened, including dates, amounts and the sender's details, and keep the emails. Tell your workplace IT team if a work account was involved, and report the incident to the police or your country's fraud service.
```

## When to assign (labeling rules v1.5)

- **Assign when:** ONLY when the email itself is about money already lost
- **Do not assign when:** Normal lures
- **Constraint:** Never with ADV-01, MED-01, INV-01 or JOB-01.

## Sources

### S03 (primary): Protect yourself from phishing

- **Publisher:** Microsoft Support
- **URL:** https://support.microsoft.com/en-us/security/protect-yourself-from-phishing
- **Page date:** last updated 2026-09-11 (as seen)
- **Licence:** (c) Microsoft; Terms of use allow personal, non-commercial use of Documents without modification (risk: medium). Attribution: Keep the (c) Microsoft notice with the citation. Caveat: support.microsoft.com not named in the terms; chunks are paraphrases; author decided to keep the source; confirm with the advisor before publishing.
- **Why this topic matters:** Kaspersky blocked over 893 million phishing attempts in 2024, up 26% from about 710 million, often impersonating well-known brands ([Kaspersky, 19 Feb 2025](https://www.kaspersky.com/about/press-releases/2025_kaspersky-reports-nearly-900-million-phishing-attempts-in-2024-as-cyber-threats-increase)). This supports brand impersonation in general; no Microsoft-specific statistic was found
- **Weaknesses:** Commercial vendor; copyright terms unverified; keep chunks paraphrased

## Change history

- 2026-10-24: renumbered from old AFT-03 (lost money); text unchanged.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
