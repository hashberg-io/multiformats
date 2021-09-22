# Security Policy

We take security of this package very seriously.

## Supported Versions

We will issue security updates for [PyPI releases](https://pypi.org/project/multiformats/) with the latest minor version number (regardless of micro version), by releasing a new minor version.

If you find a vulnerability which is not in any of the PyPI releases with the latest minor version, you should instead report it as a bug by [filing an issue](https://github.com/hashberg-io/multiformats/issues).

## Reporting a Vulnerability

To report a vulnerability, please send an email to security@hashberg.io with the following information:

- how we can contact you privately
- how you wish to be publicly identified for the purpose of credit when we disclose the vulnerability
- which package releases are affected
- the Python version (including OS, if relevant) and the versions of all dependencies that you used when confirming the vulnerability
- detailed description of the vulnerability, including how we can reproduce it

We will come back to you within 24 hours to acknowledge your report and we will provide a detailed response within 48 hours, including an initial assessment of how we intend to address the vulnerability you disclosed. If the fix requires a prolonged amount of time (> 1 week), we will send you weekly updates on our progress.

## Disclosure Process

1. Upon initial acknowledgment, we will assign a Unique ID `UID` to your security report, which we will reference in all our communications using the header `[security report #UID]`.
2. Fixes are prepared and held locally in a new branch, without pushing to the public repository.
3. When all fixes are ready to be pushed, an issue announcing the existence of a vulnerability is opened on GitHub: this includes package versions affected, security report UID and embargo date (typically 72 hours from the issue being opened), but no further information.
4. On the embargo date, the fix branch is pushed and merged into the main branch, closing the issue, and a new minor version is released on both PyPI and GitHub. The release notes on GitHub provide a detailed description of the vulnerability, including credit to the initial discloser(s), as well as a summary of how the vulnerability was patched.
