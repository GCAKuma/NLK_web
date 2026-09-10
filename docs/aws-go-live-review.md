# AWS launch assessment and workflow

Implementation update (2026-09-10): deployment preparation now addresses checkout
locking, retry-safe checkout tokens, private documents, durable notifications,
private S3 storage, limited database access, backups and HTTPS. The original
findings below describe the pre-change assessment. Follow
[AWS start here](aws-start-here.md) for the current commands and remaining
account setup. AWS provisioning and live acceptance checks are still pending.

Reviewed 2026-09-09 using the local repository and current AWS, Django and
Supabase guidance. No AWS resources were created. This is a source/configuration
review, not a security certification or a measured capacity assessment.

## Decision and architecture

AWS is suitable. Keep Supabase PostgreSQL and the existing Django authentication,
catalogue, checkout and admin. The production image already includes Gunicorn,
compiled CSS and native PDF dependencies. Celery and Redis are also required.

For a small initial store with accepted maintenance/recovery downtime, use one
Ubuntu EC2 instance with encrypted EBS running Nginx, Django, Celery and Redis
through Docker Compose. Start evaluation with 2 vCPU and 4 GiB RAM; tune based
on load tests and PDF memory usage. Put the app near the Supabase database.
Use S3 for media, SES for mail, existing DNS or Route 53, an Elastic IP,
Let's Encrypt HTTPS, and CloudWatch/Budgets for monitoring and costs.

A single server is not highly available. If instance/AZ outages must not stop
sales, use a load balancer and at least two web instances/tasks across two AZs,
shared media and a resilient broker/worker setup. Supabase availability remains
a separate dependency. AWS recommends multiple AZs for production fault tolerance.
[AWS reliability guidance](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_multiaz_region_system.html)

## Findings to address before launch

| Finding | Source evidence | Required outcome |
| --- | --- | --- |
| Checkout can oversell | `apps/orders/views.py`: stock subtraction clamps to zero without locking/revalidation | Lock/re-read cart and variants in a transaction; reject unavailable quantities; recalculate totals; prevent duplicate checkout |
| Documents lack private delivery rules | Nginx serves all `/media/`; S3 config disables signed URLs | Separate catalogue assets from private invoices/slips; authorize private downloads; use expiring URLs |
| Notifications can be lost or repeated | Direct publish in `on_commit`; Redis has no persistent volume; both emails share one completion flag | Durable outbox/reconciliation, per-recipient tracking, bounded retries, broker persistence and failed-job alerts |
| Deployment assumes local PostgreSQL | Compose starts `db`; backup script dumps it | Supabase-specific configuration and hosted-database backup process |
| HTTPS is incomplete | Nginx TLS block is commented while Django defaults to HTTPS redirects | Certificate bootstrap, correct HTTPS routing, and tested renewal with Nginx reload |
| Secrets/permissions need production hardening | Fallback Django secret, static S3 keys, owner-level database connection | Fail on missing secrets, use EC2 IAM roles, separate runtime and migration DB roles |
| Repeated product-card queries | Product properties filter related managers despite prefetching | Measure query counts and use prefetched data/annotations |
| Operational readiness | No application health endpoints or persistent Redis configuration | Health checks, bounded logs, monitoring, restart and recovery tests |

Also review upload limits, login/form abuse protection, staff access and dependency
updates. The previous 33 UI/application tests and exact database-transfer checks
do not establish concurrent checkout safety or AWS performance. These fixes are
identified work, not changes implemented by this review.

## Step-by-step launch workflow

1. **Agree the launch requirements.** Choose domain, budget, expected peak
   traffic, acceptable downtime and maximum data loss. Confirm Supabase region
   and plan. Free projects can pause for inactivity; choose a production-appropriate
   plan and backups. Daily backups alone can lose a day's new orders; use PITR
   or another recovery strategy if that is unacceptable.
   [Supabase production guidance](https://supabase.com/docs/guides/deployment/going-into-prod)

2. **Prepare and identify the release.** Resolve the findings above. Verify the
   GitHub commit includes the reviewed changes: this workspace has uncommitted
   files, so the remote version is not confirmed. Keep secrets, private backups
   and uploads out of Git. Pin tested dependencies and use repeatable builds.
   Run tests on disposable PostgreSQL in Linux containers, including invoice PDFs,
   concurrency, duplicate checkout, authorization and notification failures.

3. **Secure AWS access.** Enable root MFA and use a separate administrative
   identity. Set budget alerts. Create a narrowly scoped EC2 role for storage,
   monitoring and secrets. Use Secrets Manager/SSM SecureString with explicit
   runtime injection, or a protected server-only environment file initially.
   [AWS IAM practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

4. **Prepare Supabase.** Retain the transferred data; do not seed or re-import it.
   Back it up before migrations. Create separate runtime and migration roles.
   Imported tables have RLS enabled, so the runtime role needs deliberate policies
   and grants; never expose it to browser clients. Verify TLS, timeouts and
   connection budgets across web workers, Celery and deploys. Use session pooling
   for IPv4 persistent clients, or direct connectivity where supported. Restrict
   network access to intended hosts where supported and validate before closing it.

5. **Configure durable files and email.** Create private encrypted S3 storage with
   Block Public Access and versioning. Implement the public/private storage split
   first; CloudFront with Origin Access Control can deliver catalogue images while
   private documents require application authorization. Copy local media preserving
   referenced paths and verify the inventory. The transfer audit found 95 files
   and 48 referenced paths; recount at deployment. Verify the sending domain and
   DKIM in SES, request production access, and set Django SMTP credentials.
   Supabase Auth SMTP settings do not configure Django password-reset emails.
   Configure WhatsApp separately if automatic alerts are required.
   [S3 security](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html),
   [SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

6. **Create EC2.** Use supported Ubuntu LTS, encrypted gp3 EBS and the instance
   role. Require IMDSv2 and configure container access to role credentials.
   Associate an Elastic IP. Open 80/443; restrict SSH to your IP or use Systems
   Manager. Do not expose Redis, PostgreSQL or Gunicorn. Install Docker/Compose
   from the official Ubuntu instructions, configure OS updates and log rotation.
   [Docker installation](https://docs.docker.com/engine/install/ubuntu/)

7. **Deploy staging first.** Use a staging hostname, separate database/storage,
   and test mail recipients. Clone GitHub with read-only access and check out the
   reviewed commit. Configure a strong production secret, exact hosts/origins,
   database, storage and mail settings. Use `config.settings.prod`, not the SQLite
   `ui_settings`. Revised Compose must remove local PostgreSQL, persist Redis and
   add health checks. Run migrations once using migration credentials; remove
   automatic migrations from ordinary runtime startup. Collect static files.
   Run `manage.py check --deploy --settings=config.settings.prod` and
   `manage.py migrate --plan --settings=config.settings.prod` inside the configured
   container. Treat any remaining warnings according to the deployed topology.
   [Django checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)

8. **Set up DNS/HTTPS.** Point staging DNS to EC2. Serve the ACME challenge and
   a maintenance response over HTTP until the certificate is issued. Enable the
   domain-specific HTTPS Nginx host, then redirect ordinary HTTP traffic while
   preserving ACME access. Verify proxy headers, secure cookies and CSRF. Enable
   HSTS gradually; do not include all subdomains/preload before they are ready.
   Test certificate renewal and automatic Nginx reload.

9. **Test function, efficiency and recovery.** Exercise registration/reset,
   search/filter/Finder/Compare, cart, COD, bank deposit, uploads, admin verification,
   PDFs, both emails and wholesale enquiries on mobile/desktop. Test simultaneous
   last-item purchases, repeated checkout, broker/SMTP failures and server restart.
   Verify anonymous and cross-customer document access is denied. Load-test staging
   for 30 minutes at anticipated peak plus a short 2x burst. Record p95 response
   times, errors, CPU/RAM, queries, connections and queue age. Provisional targets:
   catalogue p95 below 1 second, checkout below 2 seconds, server errors below 1%.
   These are proposed goals, not measured results. Tune before choosing final size.
   Restore database/media into a separate environment and measure recovery time.

10. **Go live.** Record the approved release, backup and rollback steps. Check
    business contact details, bank instructions, catalogue stock/prices and policies.
    Remove/disable only approved demo records. Pause writes for any final data copy,
    take a fresh backup, set production secrets and apply reviewed migrations once.
    The Supabase data is already transferred. Activate production DNS/certificate,
    start web/workers and smoke-test with designated accounts/recipients. Open
    traffic and watch errors, queue age and resources closely for the first day.
    Roll back code only when compatible with the schema; restoring an old database
    would erase newer orders and needs explicit reconciliation.

11. **Operate.** Schedule hosted DB/media backups and monitor failures. The old
    local-DB backup script is insufficient. Repeat restore drills. Alert on uptime,
    application errors, disk/RAM, certificate expiry, broker/worker health and
    Supabase limits. Clear expired sessions and patch software. Automate subsequent
    releases using versioned images and GitHub Actions/OIDC once the process works.
    Scale to multiple AZs according to availability requirements and measurements.
    [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups)

## Costs and limits

Estimate EC2, EBS, public IPv4, bandwidth, storage, email, monitoring and Supabase
separately. Add load balancer/CDN/NAT costs only if those services are used. Public
EC2 IPv4 is not automatically free, and AWS free-tier eligibility depends on the
account/plan. Use the [AWS Pricing Calculator](https://calculator.aws/) before
purchasing. Multi-AZ is a resilience investment, not a guaranteed speed improvement.

For notification durability design, see the
[AWS transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).
