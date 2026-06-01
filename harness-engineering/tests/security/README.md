# security tests

Target coverage:

```text
Platform whitelist schema
Forbidden business fields
Platform database has no business tables
Credential no-leak checks
Health report desensitization
case_id isolation
Platform invisibility redline artifact scanning
Delivery acceptance report metadata-only enforcement
Delivery package boundary enforcement
```

Key scripts:

```text
scripts/scan-platform-invisibility-redlines.py
scripts/scan-delivery-acceptance-report.py
scripts/scan-delivery-artifacts.py
scripts/check-delivery-package.py
```
