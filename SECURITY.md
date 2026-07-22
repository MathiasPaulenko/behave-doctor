# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in behave-doctor, please report it
responsibly.

- Email: **mathias@paulenko.dev**
- Do not open a public GitHub issue for security vulnerabilities.

## Response time

We aim to acknowledge reported vulnerabilities within **48 hours** and to
provide a fix or mitigation according to severity.

## Scope

behave-doctor is a read-only static analysis tool. It does not execute code,
make network calls, or write to the filesystem beyond user-requested output
files. Vulnerabilities related to parsing untrusted `.feature` or `.py` files
are in scope.
