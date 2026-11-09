# AFT-01: You clicked a phishing link, or your account or device may be compromised

| Field | Value |
|---|---|
| Group | AFT |
| Layer | 4 After and reporting |
| Word count | 95 |
| Primary source | S01 |
| All sources | S01, S04 |
| Gold use (100 rows) | 1 rows, first chunk in 0 |

## Text

> If you only clicked a link and entered nothing, you have most likely avoided harm: close the page, do not reopen the message, and watch your accounts for odd activity. If you typed a password or personal details, or think an account was taken over, change the password on the real site and on any account that uses it, use the service's recovery process, and turn on multi-factor authentication. If you opened or installed a file, run a full scan with up-to-date security software. Warn your contacts if your account sent messages in your name.

## Embedded string (`embed_text`)

```
You clicked a phishing link, or your account or device may be compromised. If you only clicked a link and entered nothing, you have most likely avoided harm: close the page, do not reopen the message, and watch your accounts for odd activity. If you typed a password or personal details, or think an account was taken over, change the password on the real site and on any account that uses it, use the service's recovery process, and turn on multi-factor authentication. If you opened or installed a file, run a full scan with up-to-date security software. Warn your contacts if your account sent messages in your name.
```

## When to assign (labeling rules v1.5)

- **Assign when:** ONLY when the email itself is about an incident (virus detected, account taken over)
- **Do not assign when:** Normal lures; never "just in case"
- **Constraint:** Never with ADV-01, MED-01, INV-01 or JOB-01.

## Sources

### S01 (primary): How to Recognize and Avoid Phishing Scams

- **Publisher:** US Federal Trade Commission (consumer.ftc.gov)
- **URL:** https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams
- **Page date:** published 2019-05-03; modified 2024-10-11
- **Licence:** US federal government work; public domain for most website material (risk: low). Attribution: Requested where feasible. Caveat: Policy page does not name consumer.ftc.gov explicitly; third-party content excluded.
- **Why this topic matters:** FTC 2024 data: imposter scams were the most reported category ([FTC, Mar 2025](https://www.ftc.gov/news-events/news/press-releases/2025/03/new-ftc-data-show-big-jump-reported-losses-fraud-125-billion-2024)). FBI IC3 2024: about 193,000 phishing complaints, out of about 860,000 complaints and over $16 billion in losses ([Axios, 23 Apr 2025](https://axios.com/2025/04/23/fbi-internet-crime-loss-record-high-2024), secondary report)
- **Weaknesses:** US-centric. The page has no content on spam marking, prizes or money-transfer requests (checked)

### S04 (secondary): Phishing: spot and report scam emails, texts, websites and calls

- **Publisher:** UK NCSC
- **URL:** https://www.ncsc.gov.uk/collection/phishing-scams
- **Page date:** no date shown
- **Licence:** Crown copyright under Open Government Licence v3.0 (risk: low). Attribution: Required: acknowledge the source and link to the OGL (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Caveat: Third-party images and logos excluded.
- **Why this topic matters:** NCSC's Suspicious Email Reporting Service had over 10.5 million reports and 76,000 scams taken down by March 2022 ([NCSC, 18 Mar 2022](https://www.ncsc.gov.uk/news/nation-of-digital-defenders-blow-the-whistle-on-over-10-million-suspect-emails))
- **Weaknesses:** Figures are from 2022; UK reporting channels; the page was not re-read in the latest round

## Change history

- 2026-10-24: old AFT-01 (clicked a link) and old AFT-02 (account or device compromised) merged; they gave the same actions.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
