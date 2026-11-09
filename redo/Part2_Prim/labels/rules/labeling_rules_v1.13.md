# Labeling rules: assigning knowledge-base chunk IDs to phishing-email rows

Version 1.13 (2026-10-27, round 1 of the full labeling run). Changes from 1.12: section 23 adds clarifications for cases raised on rows 5001-5900; nothing earlier is reversed. Changes from 1.11 to 1.12: section 22 adds clarifications for cases raised on rows 4201-5000; nothing earlier is reversed. Changes from 1.10 to 1.11: section 21 adds clarifications for cases raised on rows 3301-4200; nothing earlier is reversed. Changes from 1.9 to 1.10: section 20 adds clarifications for cases raised on rows 2501-3300; nothing earlier is reversed. Changes from 1.8 to 1.9: section 19 adds clarifications for cases raised on rows 1751-2400; nothing earlier is reversed. Changes from 1.7 to 1.8: section 18 adds clarifications for cases raised on rows 1001-1500; nothing earlier is reversed. Changes from 1.6 to 1.7: section 17 adds clarifications for cases raised on rows 501-1000; nothing earlier is reversed. Changes from 1.5 to 1.6: section 16 adds clarifications for cases raised by the reviewer on the first 500 rows; no earlier rule or author decision is reversed and the chunk catalog is unchanged. Changes from 1.4 (author decisions after the three-model pilot): LNK-01 no longer needs click wording; masked prices do not block marker 4; one fixed chunk order and a drop order above five IDs; URG-01 counts any explicit time limit; brand-imitating URLs can set BRD-02 and LNK-02; disguised notices carry a story chunk only when the reader is asked to act on the notice; BRD-03 covers order and application forms; ADV-01 only when the reader has already won; authority claims include any approval, licence, verification or standards claim; a subject-only lure needs a product or effect word. Seven gold labels changed and all lists re-ordered. Changes from 1.3.1 to 1.4: deception marker 2 widened from "miracle or permanent result" to exaggerated health or body claims, with examples that count and do not count (section 5); one gold label changed (meajor_test_35621, SPM-01 to SPM-03). Changes from 1.3 to 1.3.1: input file named `data.csv` and columns to ignore listed (section 2); MED-02 header now describes the email; output for several rows (section 9). No label changes. Changes from 1.2 to 1.3: four-layer structure; STR-01 added, AFT chunks merged; SPM-01 and SPM-03 are exclusive and SPM-03 uses a closed list of deception markers plus a context rule; GEN-01 tied to the main story; MED-02 narrowed; JOB-01 is `good` when money or goods are received or forwarded; ATT-01 means files only; caps computed automatically. These rules are the instructions given to the labeling model and to a human labeler. Rules and the human-reviewed 100-row gold set must agree: if you change a gold label during review, change the rule that caused it and re-run the pilot.

## 1. Task
For each email row, choose 0-5 chunk IDs from the catalog, best match first, and rate how well the best chunk fits the email. If neither subject nor body contains a readable lure, the list is empty and `fit` is `none`. Output JSON only. The task is English only; some rows contain French, German or Russian fragments, which are read as they are.

## 2. Input per row (use only these fields)
The input file is `data.csv` in the Part 1 output format (the 100-row test file and the full file use the same columns).
Use only `id`, `subject`, `body` (full text up to BODY_CAP), `urls` (summary, section 12).
Ignore every other column, including `url_count`, `language`, `has_attachments`, `attachment_types`, `phishing_result`, `xai`, `source` and `chunk`. The `chunk` column, if present, holds old labels made by someone else under different rules; never read or copy it.
In a batch run, send only the four fields. In a chat test where the whole file is attached, read only the four fields; caps from section 12 do not apply, so read the full body and all URLs. Labels depend on what the email says and asks, not on the classifier or its terms. All rows are already predicted to be phishing; do not judge whether they are.

## 3. Four layers
| Layer | Question | Chunks | Rule |
|---|---|---|---|
| 1. Story | What is the email about? | BRD-01, BRD-02, ADV-01, STR-01, MED-01, INV-01, JOB-01 | At most one, except BRD-01 + BRD-02 together |
| 2. Mechanism | What does it ask the reader to do? | BRD-03, LNK-01, LNK-02, ATT-01, URG-01, MED-02 | Any number, each only if the text really shows it |
| 3. Spam | What kind of bulk mail is it? | SPM-01 or SPM-03 (exactly one), and SPM-02 | See section 5 |
| 4. After and reporting | What next? | AFT-01, AFT-02, GEN-01 | See sections 4 and 6 |

Order in the list (fixed, so that two labelers with the same set give the same list):
1. Story: BRD-01, BRD-02, ADV-01, STR-01, MED-01, INV-01, JOB-01 (BRD-01 before BRD-02 when both apply).
2. Mechanism, in this order: MED-02, BRD-03, LNK-02 or LNK-01, ATT-01, URG-01.
3. SPM-01 or SPM-03.
4. SPM-02.
5. AFT-01, AFT-02.
6. GEN-01.
If the email has no layer-1 story (plain advertising), SPM-01 or SPM-03 moves to the front and the rest keep this order (for example SPM-03, LNK-01, URG-01, SPM-02). If more than five IDs apply, drop in this order until five remain: SPM-02, ATT-01, URG-01. Never invent IDs. GEN-02 is never a gold label.

## 4. Catalog and triggers
| ID | Situation | Assign when | Do not assign when |
|---|---|---|---|
| BRD-01 | Account, order or problem from a company | The email tells a story about an account, order, delivery, billing, refund or record problem from a company the reader may not use | Plain advertising with no claim about the reader's account or order |
| BRD-02 | Claims to be bank, employer or service | Sender presents as a bank, employer, utility, government body, security system or known service and asks the reader to check or act. Also when a URL imitates a known brand: the brand name appears in the path or subdomain of a host that is not the brand's own domain, or the host is a bare IP address (for example `http://148.244.88.114/accesd.desjardins.com/...`) | Generic company ads; links to the brand's real domain (for example `images.desjardins.com`) |
| BRD-03 | Asks for sensitive information | Asks the reader to send, type, confirm or supply passwords, card numbers, ID numbers, bank account or personal details. Includes claim forms, "contact the agent with your details", and forms or card details asked for to order, apply or qualify in an advert ("fill in this short form", "send your card number and expiry date") | No such request; a plain "order now" or "call us" |
| ADV-01 | Prize or lottery | The reader has already "won", been "selected" or been "approved" for money, a prize or a free item, or a fee is needed to receive money or a prize | Ordinary discounts and sales; an invitation to enter a contest; a "free gift" offered inside an advert |
| STR-01 | Stranger offers money, inheritance or relationship | A stranger offers a share of a fortune, an inheritance, a large transfer, or a romantic approach | The reader "won" something (that is ADV-01) |
| MED-01 | Medicine offers | Advertises drugs, pills or supplements with health claims (ED, weight loss, enhancement, "meds") | Non-medical products |
| MED-02 | Email from an online pharmacy inviting you to order | The email presents itself as an online pharmacy or drugstore and invites ordering (order, ship, pharmacy, licensed meds). Requires MED-01 | Plain drug advertising; enhancement products with no pharmacy framing |
| INV-01 | Investment or stock tip | Stock, penny-stock, crypto or forex tips, "target price", "get in now", promised returns | Loans and mortgages (not covered) |
| JOB-01 | Job offer | Job, vacancy, work-from-home, courier, "account or investment manager" | Plain recruitment with no money handling |
| LNK-01 | Link of unknown destination | `urls` is not empty AND `fit` is not `none` AND at least one URL leads to the offer or the lure. Click wording is not needed: a shop, product, company or offer URL counts even when the text only names it or the subject alone carries the lure | `urls` empty; `fit` = none; every URL is a signature, webmail footer, image, unsubscribe or reference link (for example w3.org, join.msn.com, a logo .gif) |
| LNK-02 | Link to sign in or enter details | A lure URL asks the reader to log in, verify, enter details or fix a payment, or the URL itself imitates a sign-in or account page of a known brand (see BRD-02). Use instead of LNK-01, never both | The link only leads to a product page or a gift claim without details |
| ATT-01 | Attachment or file | The text mentions a file to open or download (judge from the text, not from attachment columns; images embedded in HTML do not count) | No mention of a file |
| URG-01 | Threat or pressure | Any explicit time limit or pressure: deadlines, "hurry", "expires", "final notice", "limited time only", "valid till [date]", "until [date]", "today only", threats, or claimed authority demanding action | No time limit stated; "limited stock" alone; a plain call to action such as "click now" or "order now"; "24 hours a day"; a delivery time ("within 12 hours of your order") |
| AFT-01 | Clicked a link, or account or device compromised | ONLY when the email itself is about an incident (virus detected, account taken over) | Normal lures; never "just in case" |
| AFT-02 | Lost money | ONLY when the email itself is about money already lost | Normal lures |
| GEN-01 | Reporting | See section 6 | See section 6 |
| SPM-01, SPM-02, SPM-03 | Spam | See section 5 | |
| GEN-02 | General routine | Never a gold label; used by the runtime fallback (section 11) | Always |

Not covered by any chunk (rate `partial` and use the nearest chunk): counterfeit goods and pirated software, adult content, loans and mortgages, plain advertising (travel, design services, business-to-business), business email compromise, extortion, list selling. Advance-fee contract proposals ("share a USD 10 million transfer") use STR-01 by pattern and are `partial`, because no official source read describes that email directly. AFT chunks cannot normally be reached from the email text alone; they apply only to emails that describe an incident.

Layer-1 constraints: AFT chunks never appear with ADV-01, MED-01, INV-01 or JOB-01. MED-02 never appears without MED-01. LNK-01 and LNK-02 never appear together.

## 5. Spam chunks (SPM)
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

## 6. GEN-01 (reporting)
Assign when the layer-1 story is BRD-01, BRD-02, ADV-01 or STR-01 (fraud notices rather than adverts). Do not assign when the story is MED-01, INV-01 or JOB-01 or when there is no story.

## 7. Fit rating (for the first chunk)
- `good`: the first chunk's situation matches the email's main lure and its advice applies directly.
  - Stock mail: a guarantee, target price or clear call to act = `good`; news and price only = `partial`.
  - Medicine: sold like medicine or by a pharmacy = `good`; enhancement patches or supplements with no pharmacy framing = `partial`.
  - JOB-01: money or goods are received or forwarded, or the worker must pay = `good`; only a vacancy or an unstated money flow = `partial`.
  - STR-01: a romance approach or an inheritance offer = `good`; a contract-transfer proposal = `partial`.
- `partial`: only a nearby or generic chunk applies; the topic has no chunk of its own; the lure is signalled only by the subject (obfuscated spelling allowed) while the body is unrelated, provided the subject names a product type or an effect (meds, pills, viagra, size, weight, loan, stock, vacancy, software); a slogan that only hints ("separate yourself from other men", "lovers package at discount") does not set a story chunk; or part of the chunk's condition is missing (for example an "approved" phone with no fee).
- `none`: neither subject nor body contains a readable lure (random or literary text, technical text, symbols, jokes, keyword lists). `chunk_ids` is empty; no LNK.

## 8. Procedure
1. Read `subject`, `body` and `urls`. Find the lure; a subject that names a product type or effect counts (section 7); a URL that imitates a brand counts (BRD-02).
2. No readable lure: `fit = none`, empty list, stop.
3. Choose at most one layer-1 story chunk. Uncovered topic: skip to step 5 and use `partial`.
4. Add layer-2 mechanism chunks the text really shows.
5. If the email promotes something, choose SPM-01 or SPM-03 (section 5) and add SPM-02 if the wording is there.
6. Add GEN-01 under section 6.
7. Order as in section 3 (fixed order; drop SPM-02, then ATT-01, then URG-01 if more than five apply), keep 1-5 unique IDs, rate `fit`.

## 9. Output (one JSON object per row, no text outside JSON)
```json
{"id": "meajor_test_...", "chunk_ids": ["INV-01", "SPM-03"], "fit": "good",
 "fit_note": "", "email_summary": "one sentence, what the email is about",
 "chunk_rationale": {"INV-01": "why", "SPM-03": "marker 1: why"}, "truncated": false}
```
When several rows are labeled in one reply, return one JSON array with one object per input row, in input order, with every `id` exactly as in the file. Do not skip rows; if the reply would be too long, stop after a whole row and say which `id` comes next.
`fit_note` is empty for `good`; for `partial` and `none` give a short reason. `chunk_rationale` has exactly one entry per chunk ID (empty object for an empty list), one sentence each, in English. Do not copy long text from the email.

## 10. Worked examples (from the 100-row set)
| id | Email in short | chunk_ids | fit |
|---|---|---|---|
| meajor_test_2712 | tadalafil "soft tabs", claims FDA approval, no prescription step | MED-01, LNK-01, SPM-03 | good |
| meajor_test_64367 | penny stock "double by end of week" | INV-01, SPM-03 | good |
| meajor_test_34457 | stock alert, no guarantee, paid-promotion note | INV-01, SPM-01, SPM-02 | good |
| meajor_test_12236 | lottery winner, claim deadline | ADV-01, BRD-03, URG-01, GEN-01 | good |
| meajor_test_46622 | payment-service class-action payout, confirm bank account | BRD-02, BRD-03, LNK-02, URG-01, GEN-01 | good |
| meajor_test_104409 | car-centre job: accept transfers and forward them | JOB-01, BRD-03, LNK-01 | good |
| meajor_test_84651 | woman says she found your picture | STR-01, GEN-01 | good |
| meajor_test_28995 | share of a USD 10 million contract payout | STR-01, BRD-03, GEN-01 | partial |
| meajor_test_77486 | replica watch store | SPM-03, LNK-01 | partial |
| meajor_test_82372 | French bank-card contest; link host is a bare IP carrying the bank's sign-in path | BRD-02, LNK-02, URG-01, GEN-01 | good |
| meajor_test_90413 | subject "your mixer is ready to ship", body a plain baking advert | SPM-03 (marker 5), LNK-01, SPM-02 | partial |
| meajor_test_73044 | enhancement patches, "size and drive go through the roof", "for a limited time only" | MED-01, LNK-01, URG-01, SPM-03 (marker 2) | partial |
| meajor_test_61371 | ED treatment, "join the millions of men", visit store | MED-01, LNK-01, SPM-01 (no marker) | good |
| meajor_test_86167 | subject offers viagra, body religious text, no URL | MED-01, SPM-01 | partial |
| meajor_test_75971 | random quotations | [] | none |
| meajor_test_22198 | forwarded joke | [] | none |

## 11. Runtime fallback (not part of the gold)
When the system judges an email to be `none`, it shows the general routine chunks SPM-01 + GEN-02 with `used_fallback: true`. Keep two columns: `chunk_ids_gold` (answer key, may be empty) and `chunk_ids_system`. The output must say it is general guidance, not a matched scenario. The threshold that decides when the fallback applies is tuned on a separate dev set, not on test rows.

## 12. Parameters (computed automatically from the input file)
Run `profile_caps.py INPUT.csv`; it reads the file and writes `params.json` and the model input.
- `BODY_CAP`: smallest body length that truncates at most 1% of rows, rounded up to the next 500, within 2,000-20,000 characters. Longer bodies keep the first 70% and last 30% of the allowed length with `[truncated N characters]` and `"truncated": true`.
- `URL_CAP` (N): smallest number of unique URLs kept so that at most 5% of rows lose links, within 5-50. Each URL is cut to 200 characters; the summary carries the total count and a domain summary when most URLs share a domain.
- The values are set at the start of every run from the whole file, written to `params.json` with the file hash and date, and not changed during the run. If a rerun gives different values, rerun the gold rows and the affected rows.
- With under 1,000 rows the script warns that the values are provisional. On the 100-row pilot it gives BODY_CAP 4,500 and URL_CAP 8.
- URLs are used to decide whether a lure link exists and where it leads, and to detect a brand-imitating host (BRD-02, LNK-02). Never choose any other chunk from a domain name.

## 13. Checks after each run (script, not the model)
- every ID exists in the catalog; 0-5 unique IDs; no GEN-02; no LNK-01 with LNK-02; LNK only when `urls` is not empty and `fit` is not `none`
- no SPM-01 with SPM-03; SPM-02 only with SPM-01 or SPM-03; at most one layer-1 story chunk (BRD-01 + BRD-02 allowed); GEN-01 if and only if the story is BRD, ADV-01 or STR-01; MED-02 only with MED-01; no AFT chunk with ADV-01, MED-01, INV-01 or JOB-01
- list order follows section 3
- `fit` in {good, partial, none}; `none` iff the list is empty; `fit_note` empty iff `good`; `chunk_rationale` keys equal `chunk_ids`
- row count and `id` set equal the input; report the number of `truncated` rows and include them in the audit
- gold rows (put the 100 reviewed rows inside each run) agree with the gold: first chunk (excluding `none`), Jaccard of the set, and `fit`
- audit by hand a random 5%, plus every row where the first chunk is SPM-01 and `fit` is `good`, plus every hybrid row (SPM chunk with a fraud story)

## 14. Evaluation notes
- Exclude `none` rows from first-chunk metrics and report results by `fit`.
- Compare with baselines "always SPM-01" and "always SPM-03" (on the 100-row set under v1.3 they are the first chunk on 15 and 16 of 85 non-`none` rows).
- The labeler is one model (Claude Sonnet 5.5), so the gold is not independent until the human review is done; say so in the thesis.
- Report, side by side, the real-world impact of each chunk group (loss and complaint figures with sources, see `source_rationale.md`) and the share of that group in the labeled 6,000 rows. Never change labels to make the shares match. Also report accuracy weighted by impact, and say how any stratified evaluation subset was drawn.

## 15. Open items
None. MED-02's header was changed on 2026-10-24 to describe the email; the advice text is unchanged and the chunk must be re-embedded. The unsupported SPM-02 clause (scammers use unsubscribe links to confirm an address is active) was removed on 2026-10-24; no label depended on it.

## 16. Clarifications (v1.6, from the first 500 rows)
These settle cases the earlier sections left open. They do not reverse any earlier rule.

**Deception markers (section 5)**
- C1. Authority-claim context rule: in `chunk_rationale` write "context rule: ..." instead of a marker number. "Recommended by [organisation]" is an authority claim like "approved" or "verified by".
- C2. Medicines: a discount, low price or "x% off" on a medicine (named or masked) is not marker 4; marker 4 covers counterfeit goods, replicas, software and other brand goods. A medicine email becomes SPM-03 only through marker 1, marker 2, marker 5 or the context rule.
- C3. Marker 4 for software and brand goods: any "x% off" or "for only" wording counts, whatever the stated size of the discount.
- C4. Marker 1: close paraphrases of a guarantee count ("without running any risks", "money-back guarantee", "satisfaction guaranteed"). A boast without a promise ("100% customer satisfaction", "best service") does not.
- C5. Marker 2: an enlargement or cure claim counts even when it is made inside a testimonial. A generic boast ("effective cures", "works great") without a specific impossible result does not.
- C6. Marker 3: "no matter what your income", "bad credit OK" and similar promises of approval regardless of circumstances count.
- C7. A personal-style note that only pushes a link (no product named) and promotes a site is SPM-03 under marker 5; with no URL it is `none`.

**Story chunks (section 4)**
- C8. Loans, mortgages and credit offers ("pre-approved", "you are approved") never take ADV-01; they stay uncovered (SPM-03 marker 3 when no check is promised, `partial`).
- C9. ADV-01 needs prize, lottery, award or free-item wording. "You are a beneficiary, money will be credited" with no prize wording is STR-01 (a stranger offers a transfer). "Selected for a chance to receive" is an invitation, not ADV-01.
- C10. JOB-01 is assigned when the email offers the reader paid work (vacancy, work from home, mystery shopper, paid surveys, earnings from a role); `partial` if no money handling is stated, `good` under section 7. It is not assigned to job-board newsletters, recruitment-agency adverts or business-opportunity schemes that offer no job to the reader (use SPM, marker 6 for get-rich schemes).
- C11. Security and delivery system notices with no promotion:
  - virus-scan or blocked-attachment notice: BRD-02, AFT-01, GEN-01 (add ATT-01 only if the reader is asked to open a file), `partial`;
  - mail-delivery failure or bounce that carries or points to an attachment: BRD-01, ATT-01, GEN-01, `partial`;
  - e-card or "you have a message" notice from a service with a link to view it: BRD-02, LNK-01, GEN-01, `partial`.
- C12. A disguised order or refill notice whose link only leads to buying a medicine is MED-01 with SPM-03 (marker 5); no BRD-01 or GEN-01, because the reader is asked to buy, not to supply information.
- C13. A notice that presents itself as a known brand or service and asks the reader to verify or log in takes BRD-02 (and LNK-02) through the sender trigger even when every link is on the brand's real domain.

**Mechanisms (section 4)**
- C14. BRD-03 includes a request to send a CV or resume, because it carries personal details.
- C15. LNK-02 needs a request for personal, account or payment details. An age-verification click on an adult site is LNK-01.
- C16. A news or reference URL quoted to support a story is a reference link, not LNK-01.
- C17. URG-01: "urgent", "immediately" or "as soon as possible" count when they demand that the reader act; "urgent" describing the sender's own situation, with no demand on the reader, does not.
- C18. MED-02: a seller of several medicines that invites ordering online counts as an online pharmacy or drugstore even without the word "pharmacy" ("online store", "verified shop", "meds online").

**Fit and lures (sections 7 and 8)**
- C19. The subject-only product words are examples, not a closed list: any word that names what is sold counts (a brand software title such as "cs3", "payday" for a loan, credit card, education help, scholarship giveaway). A slogan that does not say what is sold ("separate yourself from other men", "lovers package at discount") sets no story chunk; such a row is `partial` with SPM and LNK chunks if a URL leads to an offer, otherwise `none`.
- C20. When subject and body are unreadable, a URL alone (a form page or a bare IP with no brand in it) is not a readable lure: `none`. A brand-imitating URL (BRD-02 rule) still counts.
- C21. Section 1 names French, German and Russian only as examples: an email in any language is translated by the labeler and labeled by its meaning.

## 17. Clarifications (v1.7, from rows 501-1000)
**Deception markers**
- C22. Marker 2 also covers other effortless or impossible results ("stop smoking without willpower") and three or more distinct body or mind benefits from one product (weight loss plus mood, energy and libido), including inside testimonials.
- C23. "Doctors and celebrities endorse" is an authority claim under the context rule.
- C24. Marker 4 needs "for only", "x% off", "OEM", "replica", "copies", "on special" or "starting at" wording on software or brand goods; vague "low low prices" alone does not count. Services (for example TV on a PC, subscriptions) are not software or brand goods.
- C25. Marker 3 covers diploma or degree offers without study or exams.
- C26. Marker 6 covers gambling or casino adverts that promise earnings ("start earning real money", "change your life") and easy-income schemes for trivial tasks ("make a living by returning phone calls"); these are SPM-03 without JOB-01. A refer-friends-for-a-gift offer is not marker 6.
- C27. A "re:" or casual subject alone ("wassup") is not marker 5.
- C28. A bulk dating or webcam site advert written as a personal note is SPM-03 (marker 5) with LNK-01, not STR-01. STR-01 applies when the stranger asks the reader to reply or write to them personally and no site membership is sold.

**Story chunks**
- C29. Bank or service impersonation: add BRD-01 to BRD-02 when the email claims a problem with the reader's account, order, billing or delivery (suspended, locked, unpaid, failed); BRD-02 alone for other requests (verify details, receive a payout).
- C30. A brand name inside a registered look-alike domain (typosquatting, for example articulomercadolibre.com.ar next to the real articulo.mercadolibre.com.ar) counts as brand imitation under BRD-02. A brand name in the path of an ad-network or tracking image URL inside a plain retailer advert does not.
- C31. A proposal to pose as next of kin of a dead depositor or client and claim the funds is STR-01 `partial` (a transfer proposal); STR-01 `good` for inheritance is when the reader is told they are the heir.
- C32. Survey-reward and gift-card offers that require a survey, sign-up or purchase are adverts, not ADV-01, even with "selected" or "claim your gift" wording; use SPM (marker 5 when it poses as a personal notice).
- C33. Supplements with fitness, purity or body claims count as MED-01 (`partial` without pharmacy framing).

**Mechanisms**
- C34. URG-01: "immediately", "right now", "at once", "as soon as possible" and "your early response is needed" count even inside a call to action ("call your broker right now"); "now" or "today" alone in a plain call to action ("order now", "click now") does not.
- C35. SPM-02: any text or link label whose purpose is to stop the mailing counts ("not again plz", "remove me", an account-deletion link that removes the reader from the list). An advert for an anti-spam product does not.

**Fit and lures**
- C36. An advert whose product name is masked (`token_product`) still has a readable lure when the text shows it is selling something (price, "buy", "order", an offer link): `partial` with SPM. A masked token in the subject alone is not a product word under C19.
- C37. A newsletter or institutional letter with nothing promoted or requested (no offer, no request for money or details) is `none`; one that promotes products, services or paid content is SPM-01 `partial`.
- C38. If an email appears to advertise sexual material involving minors, label it as uncovered adult content, set `uncertain` to true and write "possible material involving minors; needs human review and reporting" in `uncertain_reason`.

## 18. Clarifications (v1.8, from rows 1001-1500)
**Deception markers**
- C39. Marker 4 "brand goods" means designer or luxury goods (watches, bags, jewellery) and software. Ordinary retailer sales (department stores, clothing, travel) at "x% off" are not marker 4.
- C40. Marker 4 wording also covers near-equivalents of "for only": "only [price]", "below [price]", "under [price]".
- C41. Marker 3 covers any credential issued without checks (degrees, ordination, licences, certificates).
- C42. Marker 1 covers guaranteed results, profit, safety or satisfaction. A guarantee about a service condition ("full confidentiality guaranteed", "discreet shipping guaranteed") is not marker 1.
- C43. Marker 5 covers a stock tip written as a news article, bulletin or analyst report.
- C44. Casino deposit bonuses and "jackpots waiting" are not marker 6 unless the email promises earnings or a changed life (C26).

**Story chunks and URLs**
- C45. A brand name in a tracking or ad-server subdomain of a plain retailer advert (for example macys.p03.com) is not brand imitation, unless the email asks the reader to log in or enter details.
- C46. When an email has another story (for example MED-01) and also a brand-imitating URL, keep the story chunk; the URL sets LNK-02 if it imitates a sign-in or account page, otherwise LNK-01. Mention the URL in the rationale.
- C47. A subject that names an invoice, payment, account or delivery notice ("pro-forma invoice attached") is a readable lure even when the body is junk: BRD-01 (ATT-01 if a file is mentioned) and GEN-01, `partial`.
- C48. MED-02 needs the email to present a shop selling several medicines and invite ordering (a multi-drug price list with "buy now" or "order" counts). A single-drug advert without shop framing is MED-01 without MED-02.

**Mechanisms**
- C49. A link to a loan, credit or application form where the reader enters personal or financial details is LNK-02.

**Fit and lures**
- C50. Drug or product names hidden by spacing, interleaving or symbols count as readable when a careful reader can decode them.
- C51. A personal-style subject over an unreadable body with only site links is `none` under C20; C7 applies only when the note itself is readable.
- C52. An academic event, conference or summer-school announcement with no fee, offer or request is `none` under C37.

## 19. Clarifications (v1.9, from rows 1751-2400)
- C53. Paid surveys: JOB-01 when the email offers ordinary paid survey work; when it promises large or effortless income ("earn $X a day from home, no skills"), it is SPM-03 under marker 6 without JOB-01 (C26).
- C54. Words that name adult services or content ("hot girls available", "companion", "webcam") name what is sold under C19.
- C55. A product brand (fashion, watches) on an unrelated shop site is not BRD-02; BRD-02 brand imitation is for banks, payment services, email or account providers and other services the reader may log in to. Designer goods at low prices fall under marker 4.
- C56. A consumer survey that offers a gift is an advert (C32), not marker 5; marker 5 needs the email to pose as independent research or news.
- C57. Marker 1 needs certainty ("guaranteed", "sure", "shoo-in", "will double", "500% profit" stated as a fact). A return framed as "potential", "expected", "could" or a target price is not marker 1.
- C58. Topical body and slimming products (wraps, creams, patches) with body claims count as MED-01.
- C59. Effect words such as "man's power", "stamina", "last longer" count as effect words under C19.
- C60. A charity or disaster appeal from a stranger asking for money to a bank account is STR-01 `partial` (BRD-03 if account or card details are asked, GEN-01).
- C61. A stock profile or press release that openly says "strong buy" or discloses paid promotion is not marker 5; marker 5 is for a tip that poses as independent news or research without saying it is promotion.
- C62. A slogan subject over a filler body whose only URL gives no sign of an offer is `none` (C20, C51).

## 20. Clarifications (v1.10, from rows 2501-3300)
- C63. An internal or employer message (HR survey, IT notice) whose links are on the organisation's real domain and that asks for no money, password or personal details is `none`.
- C64. A plain mail-server bounce with no attachment, no link and no request is `none`, even when its subject names a delivery notice (C11 applies only when an attachment or link is carried).
- C65. Marker 4 also counts "retail price X, our price Y" and "you save X" comparisons on software or brand goods.
- C66. Stock mail and marker 5: if the email says anywhere that it is paid or sponsored promotion, it is not marker 5 (C61). If it presents a rating as coming from an independent analyst or research report and discloses no payment, it is marker 5.
- C67. Casino and gambling words name what is sold for C19: "casino", "slots", "poker", "blackjack", "jackpot" and "bonus" in a gambling context.
- C68. "No prescription needed" on its own is not a deception marker; it is covered by MED-01's advice. SPM-03 for medicine still needs marker 1, 2 or 5 or the context rule (C2).
- C69. The "current status / for your records / update our records" loan template that links to a form for the reader's details is read like meajor_test_44362: BRD-01, BRD-03, LNK-02, SPM-03 (marker 5), GEN-01, `partial`.

## 21. Clarifications (v1.11, from rows 3301-4200)
- C70. A brand notice that looks genuine, with all links on the brand's real domain and only a routine footer such as "log in to update your email address", is `none` (as C63). C13 applies when the body itself asks the reader to verify or log in.
- C71. An institutional scholarship, training or call-for-papers announcement with a deadline and a download link on the organisation's own site, and no fee, payment or personal-detail request, is `none` (extends C52).
- C72. Loan links: LNK-02 when the text mentions a form or application to fill in, or the URL is clearly a form page (for example formupdate.asp, apply.asp); "apply today ... enter here" with neither is LNK-01.
- C73. Loan emails that pose as a confirmation ("we accepted your application", "pre-approval confirmation") follow C69 when the link is a form page: BRD-01, BRD-03, LNK-02, SPM-03 (marker 5), GEN-01. Without a form page they are SPM-03 (marker 5) with LNK-01.
- C74. Marker 4 also applies when a readable price is visibly far below the normal price of named brand software or goods ("Photoshop CS3 Extended for $89"). The wording list in C24 is for masked prices.
- C75. A pharmacy advert written as a consumer warning ("beware of fake drugs, choose licensed pharmacies such as X") poses as independent advice: SPM-03 (marker 5).

## 22. Clarifications (v1.12, from rows 4201-5000)
- C76. C69 and C73 apply only when the body itself presents the confirmation or records notice and asks the reader to complete the form. If only the subject poses as a confirmation over a plain loan advert, use SPM-03 (marker 5) with the mechanism chunks (BRD-03, LNK-02 when there is a form) and no BRD-01 or GEN-01.
- C77. Text that asks the reader to complete a form or application ("please complete your application") sets LNK-02 under C72 even when the link is a URL shortener.
- C78. Job application forms take LNK-01, as in the worked example meajor_test_104409; add BRD-03 when personal or bank details are requested. LNK-02 stays for sign-in, account or payment details and for loan forms (C49, C72).
- C79. A drugstore advert that names no drug is `good` when it presents itself as a pharmacy or drug shop selling medicines (MED-02 framing), otherwise `partial`.
- C80. A brand name inside a spammer's own registered domain used for its own business (for example naver-loan.co.kr for a loan advert), with no copy of the brand's sign-in or site, is not brand imitation (no BRD-02).
- C81. "OEM" sets marker 4 only inside an offer. A subject that asks a technical question ("reinstall oem with different media???") with no offer is not a lure.
- C82. ATT-01: "see attach" or "see attachment" counts as a file mention even when only a link follows.
- C83. A size or erection slogan with no product named ("your woman needs an 8 inch man") is an effect word under C19 and C59: MED-01 (`partial`) with SPM-03 marker 2.
- C84. "Safe purchase" or "secure ordering" is a service condition (C42), not marker 1. "100% safe" or "completely safe" about the product or its effects is marker 1.
- C85. Authority claims in other languages count under the context rule ("verifizierter Onlineshop", "pharmacie agréée").
- C86. Stock bulletins: "forward-looking statements" disclaimers are not a payment disclosure; only an explicit statement of compensation or paid promotion makes a stock email openly promotional (C61, C66).

## 23. Clarifications (v1.13, from rows 5001-5900)
- C87. A work-from-home "employees wanted" email that describes tasks and asks the reader to apply is JOB-01 (BRD-03 if the form asks for personal details). Income promises with no described work ("unlimited income", "financial freedom") are marker 6 without JOB-01.
- C88. A pharmacy advert framed as a consumer warning ("other pharmacies sell fakes, choose ours") is marker 5 only when it poses as independent advice, news or research; when the seller openly speaks as itself ("we", "our pharmacy"), it is not marker 5.
- C89. Effect words under C19 and C59 must name a body or health effect ("last longer", "harder", "bigger", "lose weight"); vague fun or lifestyle slogans ("keep the fun going all night long") do not.
- C90. A subject such as "[product] ready to download" or "ready to ship" is marker 5 only when it addresses the reader's own order or account ("your order", "your download"); an impersonal availability line is not.
- C91. A stated duration of a product's effect ("lasts up to 48 hours") is not a time limit for URG-01.
- C92. A genuine-looking brand promotion whose links pass through a third-party tracking host carrying the brand name in its path is not brand imitation (C30, C45) unless it asks the reader to log in or give details; label it as an advert.
- C93. A link-only personal note whose link goes to an academic or personal page with nothing promoted is `none` (C37); C7 applies when the link leads to a commercial or promotional site.

