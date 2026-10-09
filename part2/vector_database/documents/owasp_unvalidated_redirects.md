# Unvalidated Redirects and Forwards Cheat Sheet

This is an attributed, lightly condensed adaptation of the OWASP Cheat Sheet under CC BY-SA 4.0, not a verbatim copy of the complete page.

## Introduction

Unvalidated redirects and forwards are possible when a web application accepts untrusted input that could cause the web application to redirect the request to a URL contained within untrusted input. By modifying untrusted URL input to a malicious site, an attacker may successfully launch a phishing scam and steal user credentials.

Because the server name in the modified link is identical to the original site, phishing attempts may have a more trustworthy appearance. Unvalidated redirect and forward attacks can also be used to maliciously craft a URL that would pass the application's access control check and then forward the attacker to privileged functions that they would normally not be able to access.

## Preventing Unvalidated Redirects and Forwards

Safe use of redirects and forwards can be done in a number of ways:

- Simply avoid using redirects and forwards.
- If used, do not allow the URL as user input for the destination.
- Where possible, have the user provide a short name, ID, or token which is mapped server-side to a full target URL. Be careful that this does not introduce an enumeration vulnerability.
- If user input cannot be avoided, ensure that the supplied value is valid, appropriate for the application, and authorized for the user.
- For local return URLs, use a framework helper that rejects non-local destinations.
- If external destinations are required, allow-list explicitly approved destinations using parsed URL components.
- Force redirects through a page that tells users they are leaving the site, clearly displays the destination, and asks them to confirm.

Use a maintained URL parser compatible with the redirect API and browser URL interpretation. Compare the parsed scheme, canonical host, and effective port against an explicit allowlist; constrain the path when only specific endpoints are permitted. Reject user information and ambiguous input, and redirect using the validated URL rather than transforming it afterward. Do not use raw prefix or suffix matching. A server-side mapping from an approved destination ID remains preferable to accepting arbitrary URLs.
