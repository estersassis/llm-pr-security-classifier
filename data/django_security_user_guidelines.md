# Django Security Policy — User Guidelines

> These guidelines are derived exclusively from security patterns identified across Django's pull request history. Every recommendation is grounded in a concrete vulnerability introduction, fix, or prevention measure documented in the project's development discussions. Generic advice not traceable to Django-specific evidence has been intentionally excluded.

---

## 1. Configuration and Secrets Management

**REC-01 — Validate `SECRET_KEY` format and rotate it actively.**
`SECRET_KEY` must be a valid, non-empty Unicode string. Django enforces this at startup and will raise a configuration error on an invalid value — do not suppress this check. Use `SECRET_KEY_FALLBACKS` for rotation so cryptographic transitions do not immediately invalidate user sessions.

**REC-02 — Never commit secrets or local settings files to version control.**
Django's PR history records an incident where a local settings file containing a plaintext database password was accidentally committed. Keep all credentials out of version control and out of screenshot attachments in pull request descriptions.

**REC-03 — Never set `DEBUG = True` in production.**
Django's debug pages surface `request.user`, full settings values, session tokens, and URL parameters to anyone who triggers a 500 or 404 response. Additionally, `DEBUG = True` stores every SQL query in memory; running large migrations under it can cause `MemoryError`. Disable it before any migration that touches large datasets.

**REC-04 — Bind `runserver` only to `127.0.0.1`.**
Changing the default bind address to the host's public IP or `0.0.0.0` exposes the development server to the local network or the internet. This misconfiguration appears repeatedly in Django PR discussions. Never adjust the default in shared or CI environments.

**REC-05 — Set `ALLOWED_HOSTS` as a list, never as a bare string.**
Passing a plain string (e.g., `"example.com"`) causes Django to iterate over individual characters, matching any single-character host header and completely bypassing host validation. Always use a list: `ALLOWED_HOSTS = ["example.com"]`.

**REC-06 — Do not set `DJANGO_ALLOW_ASYNC_UNSAFE=true` in production.**
Django introduced a system check for this variable specifically to prevent unsafe use of synchronous ORM code inside async contexts. Suppressing the check can cause data corruption and race conditions in async views.

---

## 2. Dependency Management

**REC-07 — Keep Pillow up to date and pin it to a patched release.**
Django's PR history documents CVE-2019-16865 in Pillow as a supply chain vulnerability that required an emergency update. Monitor Pillow's security advisories and treat any unpatched Pillow version as a known vulnerability in your deployment.

**REC-08 — Enforce minimum versions for all database drivers.**
Use `psycopg2 >= 2.8` for PostgreSQL; versions below this introduce runtime instability. Django's discussions also explicitly drop support for `sqlparse < 0.2.2`. Pin lower-bound versions for all drivers in your requirements files and treat version conflicts as security-relevant failures.

**REC-09 — Use `BCryptSHA256PasswordHasher`, not `BCryptPasswordHasher`.**
Plain BCrypt silently truncates passwords longer than 72 bytes, weakening hashing for long passphrases. `BCryptSHA256PasswordHasher` pre-hashes input with SHA-256 before bcrypt processing, eliminating the truncation. Install the dependency explicitly via `pip install django[bcrypt]`.

**REC-10 — Audit and update admin-bundled JavaScript (jQuery, XRegExp, OpenLayers).**
Outdated versions of these libraries bundled in Django's admin interface have been identified by security assessors as active vulnerabilities. Do not pin admin JS to older versions, and do not introduce additional third-party scripts into the admin without auditing them. Breaking jQuery's namespace when customising admin pages creates DOM behaviour exploitable by XSS.

---

## 3. Authentication and Session Security

**REC-11 — Do not suppress session key rotation on login or password change.**
Django rotates the session key on `login()` and on password change via session verification. Removing this rotation reintroduces session fixation. Additionally, a failed remote authentication attempt must invalidate the existing session — Django fixed a flaw where a failed backend left the prior session intact, allowing unauthorised access.

**REC-12 — Never silence exceptions raised inside authentication backends.**
Django fixed a regression where `TypeError` inside the authentication loop was silently caught, masking misconfigured backends and producing incorrect authentication state. Let all backend exceptions propagate so they surface as visible configuration errors.

**REC-13 — Preserve the `is_active` check in all custom authentication backends.**
Django discussions explicitly flagged the removal of this check as an authentication bypass for disabled accounts. Any custom backend that omits `is_active` validation allows deactivated users to authenticate successfully.

**REC-14 — Bind password reset tokens to user-specific state.**
Django fixed a design flaw where reset tokens were insufficiently bound to user data, making them reusable after an email change. Tokens must incorporate at minimum the user's email address and last login timestamp. Tokens for accounts with `UNUSABLE_PASSWORD` must be explicitly rejected in `PasswordResetForm` logic.

**REC-15 — Do not strip whitespace from password fields.**
Django deliberately omits whitespace stripping from password inputs because silent truncation weakens authentication for passwords that include leading or trailing spaces. Custom forms or serialisers that strip password fields introduce this vulnerability.

---

## 4. SQL and ORM Safety

**REC-16 — Never pass user-supplied strings to `RawSQL()`, `extra(where=...)`, or any raw `where_clause`.**
Django PR discussions explicitly flag this as a SQL injection vector. Use parameterised ORM expressions (`Value()`, `F()`, annotated `Q()` objects) instead. Similarly, do not use `shell=True` in any `subprocess` call that incorporates ORM or management command output.

**REC-17 — Do not construct SQL fragments via string formatting.**
Multiple Django PRs were rejected or closed because their implementations used `%`-style or `.format()`-style string composition for SQL query parts. The author of one such PR acknowledged it "opens the possibility of an SQL injection attack." Always use Django's query compiler and parameterised expression APIs.

**REC-18 — Quote all database identifiers; do not rely on database leniency.**
Table names that conflict with SQL reserved keywords cause syntax errors or silent query manipulation if not quoted. If you extend Django's database introspection or schema editor, ensure all identifiers are quoted unconditionally.

---

## 5. Template and XSS Safety

**REC-19 — Do not apply `|safe` to user-supplied, translated, or externally influenced values.**
Django's PR history documents `|safe` being applied to password help text, float variables in JavaScript templates, and humanize filter output — all of which introduce XSS if the input is externally influenced. Use `format_html()` for any HTML that includes dynamic values; bypassing it by assuming a value is "always trusted" removes the only structural XSS guarantee.

**REC-20 — Do not use `escapejs` in URL attribute contexts.**
The `escapejs` filter prevents JavaScript string injection but does not make a value safe inside a `javascript:` URL. Using `escapejs` in a URL attribute is insufficient escaping and has been identified as an XSS vulnerability in Django's own templates.

---

## 6. Access Control

**REC-21 — Use the correct permission method for each admin operation.**
Use `has_delete_permission()`, `has_change_permission()`, and `has_view_permission()` for their respective operations. Substituting a generic `user.has_perm()` call bypasses Django's object-level and admin-specific permission model. A non-superuser with `change` permission on the `User` model must not be able to escalate their own privileges to superuser status — Django addressed this specific vector; verify custom user admin views apply the same constraint.

**REC-22 — Do not weaken `ModelAdmin.lookup_allowed()` or the autocomplete view.**
`lookup_allowed()` restricts which URL filter parameters are valid. Overriding it to permit unrestricted field traversal enables enumeration of related objects. The autocomplete view must enforce `has_view_permission` or `has_change_permission`; Django fixed a case where it could be queried without sufficient permission checks.

**REC-23 — Validate redirect targets with `url_has_allowed_host_and_scheme()`.**
The `next` parameter in login and logout flows must be validated against the allowed host and scheme. Django's PR discussions record multiple bypass attempts via cross-domain redirect manipulation. Never validate a redirect target using a simple prefix match or domain substring check.

**REC-24 — Configure proxy headers with explicit depth; do not trust `HTTP_X_FORWARDED_FOR` unconditionally.**
Trusting forwarded headers without depth-aware validation allows clients to spoof their IP address. Django PR discussions explicitly identify this as a security misconfiguration. Also maintain `ALLOWED_HOSTS` validation at all times — disabling it was flagged as removing the primary defence against Host Header Injection.

**REC-25 — Do not weaken CSRF protection via GET parameters, session-only assumptions, or unmasked tokens.**
Three distinct CSRF weaknesses appear in Django's PR history: transmitting tokens via GET (embeds them in URLs and server logs), assuming `CSRF_USE_SESSIONS` makes `CSRF_COOKIE_SECURE` redundant (it does not), and using raw unmasked tokens (vulnerable to BREACH). Django's accepted BREACH mitigation is per-request token masking via XOR; do not substitute response-length hiding.

---

## 7. Cryptographic Practices

**REC-26 — Do not use MD5 for any security-sensitive operation.**
Django deprecated MD5-based password hashing and replaced MD5-based cache key generation because MD5 is cryptographically broken and prohibited on FIPS-compliant systems. Always pass a `salt` argument to `Signer` and `TimestampSigner` — without it, different signing contexts sharing the same `SECRET_KEY` can produce colliding signatures, enabling cross-context token reuse.

**REC-27 — Use `constant_time_compare()` for all security-sensitive string comparisons.**
Standard string equality (`==`) leaks timing information exploitable to forge tokens. Django's `constant_time_compare()` (backed by `hmac.compare_digest`) must be used for all comparisons involving tokens, hashes, and signatures.

---

## 8. Sensitive Data in Logs and Tracebacks

**REC-28 — Decorate credential-handling code with `@sensitive_variables()` and `@sensitive_post_parameters()`; set `__traceback_hide__` in async frames.**
Django's PR history documents raw passwords, session tokens, and API keys appearing in 500 tracebacks. Standard `@sensitive_variables` decoration does not propagate into nested async execution frames — those require `__traceback_hide__ = True` set explicitly at each sensitive frame. Do not include credential values in `__repr__` methods of model or form instances.

**REC-29 — Never expose stack traces in production responses, including via AJAX or 404 pages.**
Django rejected proposals to expose technical 500 details via an AJAX-accessible settings flag, and fixed a 404 debug page that leaked exception messages from URL resolver failures. Do not implement equivalent disclosure in custom error handlers.

---

## 9. Exception Handling and Resilience

**REC-30 — Do not suppress exceptions in security-relevant paths; do not commit transactions unconditionally inside cache operations.**
Bare `except:` blocks and swallowed cache backend exceptions mask infrastructure failures, storage exhaustion, and active attacks — Django code reviews flag both patterns explicitly. Separately, do not invoke cache operations that unconditionally commit a database transaction: a pattern in Django's PR history showed cache writes committing prematurely inside an open transaction, causing partial-write data integrity failures.

---

*These guidelines are derived exclusively from security classifications and summaries extracted from Django's pull request history. They reflect patterns of vulnerabilities introduced and fixes applied within the project.*
