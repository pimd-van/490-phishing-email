# ATT-01: Attachment or link in a message from a first-time sender

| Field | Value |
|---|---|
| Group | ATT |
| Layer | 2 Mechanism |
| Word count | 61 |
| Primary source | S03 |
| All sources | S03 |
| Gold use (100 rows) | 3 rows, first chunk in 0 |

## Text

> Be cautious when someone writes to you for the first time and includes an attachment or link, especially with a vague subject or an offer that seems too good. Do not open the file or follow the link. Check the sender's address carefully for lookalike spellings, search for the organisation yourself, and report the message as phishing if anything feels wrong.

## Embedded string (`embed_text`)

```
Attachment or link in a message from a first-time sender. Be cautious when someone writes to you for the first time and includes an attachment or link, especially with a vague subject or an offer that seems too good. Do not open the file or follow the link. Check the sender's address carefully for lookalike spellings, search for the organisation yourself, and report the message as phishing if anything feels wrong.
```

## When to assign (labeling rules v1.5)

- **Assign when:** The text mentions a file to open or download (judge from the text, not from attachment columns; images embedded in HTML do not count)
- **Do not assign when:** No mention of a file

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
