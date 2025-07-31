# Security Policy

## Supported Versions

We provide security updates for the following versions of pmcgrab:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in pmcgrab, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

- **Email**: rajdeep@rajdeepmondal.com
- **Subject**: [SECURITY] pmcgrab vulnerability report

### What to Include

Please include the following information in your report:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fixes or mitigations
- Your contact information (optional)

### Response Timeline

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours.
- **Initial Assessment**: We will provide an initial assessment within 7 days.
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days.

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly.
- We will keep you informed of our progress throughout the process.
- We will publicly disclose the vulnerability after a fix is available.
- We will credit you for the discovery (if desired) in our security advisory.

## Security Best Practices

When using pmcgrab:

1. **Keep Updated**: Always use the latest version of pmcgrab.
2. **Validate Input**: Validate PMC IDs and email addresses before processing.
3. **Network Security**: Be aware that pmcgrab makes network requests to NCBI servers.
4. **Rate Limiting**: Respect NCBI's rate limits and terms of service.
5. **Data Handling**: Be mindful of how you store and process downloaded scientific content.

## Security Features

pmcgrab includes several security features:

- Input validation for PMC IDs and email addresses
- Timeout protection for network requests
- Optional XML DTD validation
- Safe HTML parsing and cleaning

## Dependencies

We regularly monitor our dependencies for security vulnerabilities using:

- Automated dependency scanning
- Regular dependency updates
- Security advisories monitoring

## Contact

For general security questions or concerns, please contact:

- **Email**: rajdeep@rajdeepmondal.com
- **GitHub**: [@rajdeepmondaldotcom](https://github.com/rajdeepmondaldotcom)

Thank you for helping to keep pmcgrab secure!
