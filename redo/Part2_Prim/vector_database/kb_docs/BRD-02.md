# BRD-02: Message claiming to be your bank, employer or a service provider

| Field | Value |
|---|---|
| Group | BRD |
| Layer | 1 Story |
| Word count | 76 |
| Primary source | S03 |
| All sources | S03 |
| Gold use (100 rows) | 3 rows, first chunk in 3 |

## Text

> When a message claims to come from a bank, an employer or an online service, go to that organisation directly instead of following the message. Open its website from your own bookmark or by typing the address, or phone the number printed on your card, bill or official paperwork. Sign in there and check for any alert or request. If nothing appears in your account, the email was probably fake, so report it and delete it.

## Embedded string (`embed_text`)

```
Message claiming to be your bank, employer or a service provider. When a message claims to come from a bank, an employer or an online service, go to that organisation directly instead of following the message. Open its website from your own bookmark or by typing the address, or phone the number printed on your card, bill or official paperwork. Sign in there and check for any alert or request. If nothing appears in your account, the email was probably fake, so report it and delete it.
```

## When to assign (labeling rules v1.5)

- **Assign when:** Sender presents as a bank, employer, utility, government body, security system or known service and asks the reader to check or act. Also when a URL imitates a known brand: the brand name appears in the path or subdomain of a host that is not the brand's own domain, or the host is a bare IP address (for example `http://148.244.88.114/accesd.desjardins.com/...`)
- **Do not assign when:** Generic company ads; links to the brand's real domain (for example `images.desjardins.com`)

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
