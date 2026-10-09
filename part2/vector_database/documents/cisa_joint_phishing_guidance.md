# Phishing Guidance: Stopping the Attack Cycle at Phase One

This file is a condensed, source-grounded adaptation of selected passages from the official joint guidance PDF, not a verbatim copy of the complete document.

## Overview

Social engineering is the attempt to trick someone into revealing information (e.g., a password) or taking an action that can be used to compromise systems or networks. Phishing is a form of social engineering where malicious actors lure victims (typically via email) to visit a malicious site or deceive them into providing login credentials. Malicious actors primarily leverage phishing for obtaining login credentials and malware deployment.

The Cybersecurity and Infrastructure Security Agency (CISA), National Security Agency (NSA), Federal Bureau of Investigation (FBI), and Multi-State Information Sharing and Analysis Center (MS-ISAC) released this joint guide to outline phishing techniques malicious actors commonly use and to provide guidance for both network defenders and software manufacturers. The guide includes tailored recommendations for small- and medium-sized businesses and secure-by-design and secure-by-default guidance for software manufacturers.

## Selected mitigations for organizations

- Implement user training on social engineering and phishing attacks. Regularly educate users on identifying suspicious emails and links, not interacting with suspicious items, and reporting instances of opening suspicious emails, links, attachments, or other potential lures.
- Enable Domain-based Message Authentication, Reporting, and Conformance (DMARC) for received email, together with Sender Policy Framework (SPF) and DomainKeys Identified Mail (DKIM), and set DMARC to reject for sent email.
- Implement internal mail and messaging monitoring and scrutinize deviations from normal traffic.
- Harden credentials with FIDO or PKI-based multi-factor authentication. Prioritize phishing-resistant MFA for administrators and privileged users. If mobile push MFA cannot be replaced, use number matching to mitigate MFA fatigue.
- Incorporate denylists at the email gateway and firewall to block known malicious domains, URLs, IP addresses, high-risk extensions, and mislabeled extensions.
- Restrict administrative rights, apply least privilege, use application allowlists, and block macros by default.
- For small and medium-sized organizations, prioritize annual phishing-awareness training, strong MFA, DNS filtering or firewall denylists, anti-virus protection, high-risk file restrictions, automatic software updates, and safe-browsing policies.

## Incident response

If phishing compromises credentials or executes malware, the guide says to re-provision affected accounts, audit account access, isolate affected workstations to prevent spread, and have the malware analyzed. It also directs organizations to report phishing incidents through the appropriate channels.
