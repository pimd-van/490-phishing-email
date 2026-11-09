# LNK-02: Email asking you to click a link to sign in, enter details or fix a payment

| Field | Value |
|---|---|
| Group | LNK |
| Layer | 2 Mechanism |
| Word count | 90 |
| Primary source | S04 |
| All sources | S04, S01 |
| Gold use (100 rows) | 5 rows, first chunk in 0 |

## Text

> Do not click links in unexpected messages that ask you to sign in, confirm something, type in details or fix a failed payment or card problem. A fake page can look the same as the real one. Instead, go to the real website yourself by typing the address or using a saved bookmark, or contact the company using a phone number you already know is genuine, such as the one on your statement or card. Never enter passwords or payment information on a page you reached from a doubtful message.

## Embedded string (`embed_text`)

```
Email asking you to click a link to sign in, enter details or fix a payment. Do not click links in unexpected messages that ask you to sign in, confirm something, type in details or fix a failed payment or card problem. A fake page can look the same as the real one. Instead, go to the real website yourself by typing the address or using a saved bookmark, or contact the company using a phone number you already know is genuine, such as the one on your statement or card. Never enter passwords or payment information on a page you reached from a doubtful message.
```

## When to assign (labeling rules v1.5)

- **Assign when:** A lure URL asks the reader to log in, verify, enter details or fix a payment, or the URL itself imitates a sign-in or account page of a known brand (see BRD-02). Use instead of LNK-01, never both
- **Do not assign when:** The link only leads to a product page or a gift claim without details
- **Constraint:** Never together with LNK-01.

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
