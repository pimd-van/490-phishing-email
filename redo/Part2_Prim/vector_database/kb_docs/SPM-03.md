# SPM-03: Spam keeps arriving or looks like a scam

| Field | Value |
|---|---|
| Group | SPM |
| Layer | 3 Spam |
| Word count | 65 |
| Primary source | S07 |
| All sources | S07 |
| Gold use (100 rows) | 42 rows, first chunk in 18 |

## Text

> When unwanted email keeps coming, or one message looks like a scam, report it using your email provider's spam or phishing reporting option, and to a national reporting service if one exists in your country. Keep your devices protected by installing updates and running security software. Never click links or open files in suspicious bulk email, because that is how many scams and infections start.

## Embedded string (`embed_text`)

```
Spam keeps arriving or looks like a scam. When unwanted email keeps coming, or one message looks like a scam, report it using your email provider's spam or phishing reporting option, and to a national reporting service if one exists in your country. Keep your devices protected by installing updates and running security software. Never click links or open files in suspicious bulk email, because that is how many scams and infections start.
```

## When to assign (labeling rules v1.5)

See the spam rules below.

Apply when the email promotes something (goods, services, a website, a scheme) in bulk. Do not apply when the story is pure fraud with no promotion (a lottery notice, a stranger's offer, a bank impersonation).

Adverts disguised as a notice (marker 5): if the email asks the reader to act on the fake notice (update records, confirm details, follow the notice's link to supply information), add the story chunk (usually BRD-01) and GEN-01 as well as SPM-03. If the disguise is only in the subject or opening line and the rest is a plain advert, use SPM-03 without a story chunk and without GEN-01.

**SPM-01 or SPM-03, exactly one:**
- If the text shows at least one deception marker below, use SPM-03.
- Otherwise use SPM-01.
- Write the marker number in `chunk_rationale`.

Deception markers (closed list):
1. Guaranteed result or profit ("double by end of week", "100% safe", "risk free", "guaranteed").
2. Exaggerated health or body claim: the product is said to do something it cannot credibly do. Ask: could this product really deliver what the email claims? Counts, with or without numbers:
   - body or organ enlargement ("add 3+ inches", "increase length and girth", "enlarge your size", "size and drive go through the roof");
   - permanent results or a cure ("permanent results", "cures", "never again");
   - weight loss with no effort, or a pill that removes fat from food ("blocks fat from every meal", "lose weight while you sleep");
   - many unrelated benefits from one product (weight loss, muscle, hair and memory from one supplement);
   - reversing ageing or similar ("look 20 years younger").
   Does not count: general praise or service claims ("high quality", "safe", "no side effects" on its own (but "100% safe" or "completely safe" is marker 1), "fast shipping", "best prices", "discreet"), a plain statement of what the drug treats ("for erectile dysfunction", "pain relief"), testimonials or "millions of men use it" on their own.
3. Approval without checks ("no credit check", "approved regardless", "pre-approved" with no check).
4. Counterfeit goods, replicas, or software and brand goods at abnormally low prices. The dataset replaces amounts with `token_financial_info`; when the price is masked, judge from the wording: "OEM", "replica", "exact copies", brand software titles "on special", "starting at", "for only", "x% off" count.
5. The message poses as something else: a delivery or order notice, a records update, a note from an acquaintance or an independent research report, while it is an advert.
6. A get-rich-quick scheme or secret windfall offered in bulk.

Not markers: odd spelling, low price alone, junk text at the end of the email.

Context rule for authority claims: an authority claim is any claim of approval, licence, certification, verification or meeting standards ("FDA approved", "doctor approved", "doctor-established", "licensed", "certified", "verified by", "meeting all pharmaceutical standards"). On its own it is not a marker. It becomes one when the same email also sells a prescription drug without any prescription step, or has a price pitch or an exaggerated health claim (marker 2). Context decides.

Stock mail: a stock alert with a target price or a call to act but no guarantee is SPM-01; with a guarantee or "double" claim it is SPM-03.

**SPM-02:** assign only when the text contains unsubscribe, opt-out, stop receiving, remove-from-list or preference-update wording (obfuscated spelling counts). Never guess that it "probably" exists. It needs SPM-01 or SPM-03 alongside it.
- **Constraint:** Exactly one of SPM-01 or SPM-03.

## Sources

### S07 (primary): How To Get Less Spam in Your Email

- **Publisher:** US FTC
- **URL:** https://consumer.ftc.gov/node/78364
- **Page date:** published 2021-05-04; modified 2024-10-21
- **Licence:** US federal government work; public domain for most website material (risk: low). Attribution: Requested where feasible. Caveat: Policy page does not name consumer.ftc.gov explicitly; third-party content excluded.
- **Why this topic matters:** Kaspersky: spam was 47% of global email traffic in corporate mailboxes in 2024 (+1.27 points), mostly unsolicited advertising and not always malicious ([Kaspersky, 19 Feb 2025](https://www.kaspersky.com/about/press-releases/2025_kaspersky-reports-nearly-900-million-phishing-attempts-in-2024-as-cyber-threats-increase))
- **Weaknesses:** URL checked 2026-10-24: the node link resolves to this article. The page recommends unsubscribing through the email provider and does not warn about unsubscribing from unknown senders

## Change history

- No change since the 20-chunk catalog was fixed on 2026-10-24.

Text is a plain-English paraphrase written for this knowledge base, not a copy of the source.
