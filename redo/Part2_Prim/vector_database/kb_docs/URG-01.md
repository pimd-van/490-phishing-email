# URG-01: Email that threatens consequences or demands immediate action

| Field | Value |
|---|---|
| Group | URG |
| Layer | 2 Mechanism |
| Word count | 90 |
| Primary source | S03 |
| All sources | S03, S02 |
| Gold use (100 rows) | 10 rows, first chunk in 0 |

## Text

> Phishing messages often threaten that your account will be closed, a payment will fail or something bad will happen unless you act at once. Others set a tight deadline or claim to come from a manager or authority. The pressure is meant to make you skip checking. Pause before reacting and look at the sender's address and wording. Do not use the contact details or links in the message. Confirm the request through an official channel you find yourself, such as a phone call, before replying, paying or sharing anything.

## Embedded string (`embed_text`)

```
Email that threatens consequences or demands immediate action. Phishing messages often threaten that your account will be closed, a payment will fail or something bad will happen unless you act at once. Others set a tight deadline or claim to come from a manager or authority. The pressure is meant to make you skip checking. Pause before reacting and look at the sender's address and wording. Do not use the contact details or links in the message. Confirm the request through an official channel you find yourself, such as a phone call, before replying, paying or sharing anything.
```

## When to assign (labeling rules v1.5)

- **Assign when:** Any explicit time limit or pressure: deadlines, "hurry", "expires", "final notice", "limited time only", "valid till [date]", "until [date]", "today only", threats, or claimed authority demanding action
- **Do not assign when:** No time limit stated; "limited stock" alone; a plain call to action such as "click now" or "order now"; "24 hours a day"; a delivery time ("within 12 hours of your order")

## Sources

### S03 (primary): Protect yourself from phishing

- **Publisher:** Microsoft Support
- **URL:** https://support.microsoft.com/en-us/security/protect-yourself-from-phishing
- **Page date:** last updated 2026-09-11 (as seen)
- **Licence:** (c) Microsoft; Terms of use allow personal, non-commercial use of Documents without modification (risk: medium). Attribution: Keep the (c) Microsoft notice with the citation. Caveat: support.microsoft.com not named in the terms; chunks are paraphrases; author decided to keep the source; confirm with the advisor before publishing.
- **Why this topic matters:** Kaspersky blocked over 893 million phishing attempts in 2024, up 26% from about 710 million, often impersonating well-known brands ([Kaspersky, 19 Feb 2025](https://www.kaspersky.com/about/press-releases/2025_kaspersky-reports-nearly-900-million-phishing-attempts-in-2024-as-cyber-threats-increase)). This supports brand impersonation in general; no Microsoft-specific statistic was found
- **Weaknesses:** Commercial vendor; copyright terms unverified; keep chunks paraphrased

### S02 (secondary): Phishing (Small Business Cybersecurity Corner)

- **Publisher:** NIST
- **URL:** https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing
- **Page date:** published 2021-10-22; updated 2025-08-19
- **Licence:** Public information unless marked as copyrighted (risk: low). Attribution: Credit requested. Caveat: Check the page carries no copyright marking.
- **Why this topic matters:** Verizon DBIR 2025: phishing was 16% of breaches and the third most common initial-access vector; about 60% of breaches involve the human element ([HIPAA Journal summary](https://www.hipaajournal.com/verizon-dbir-2025/))
- **Weaknesses:** Aimed at small businesses; reuse terms not verified; the statistic is from a third party

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
