# Launch NLK on AWS with the existing Supabase database

Prepared 10 September 2026. The production code and infrastructure template are
prepared locally. No AWS resources have been created and the site is not live.
The new deployment migrations have not been applied to the hosted database.

The architecture is one Ubuntu EC2 server running Nginx, Django, Redis, Celery
and the notification dispatcher; Supabase remains the PostgreSQL database.
Private S3 buckets hold images/documents and database backups. SES sends mail.
Start in **Asia Pacific (Tokyo), ap-northeast-1**, beside your Supabase project.
This accepts downtime during server failure or maintenance; it is not a highly
available deployment. Load capacity must be measured on the actual server.

## 1. Account, costs and domain

1. Sign in to AWS yourself and enable MFA for account administration.
2. In Billing, check the expiry and service eligibility of your $100 credits.
   Create a monthly cost budget for an amount you can afford, with email alerts
   at 50%, 80% and 100%. Exclude credits from the cost calculation if you want
   alerts to show underlying service consumption. A budget is an alert, not a
   spending cap. [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
3. Review an AWS Pricing Calculator estimate for Tokyo: one t3.medium running
   continuously, 30 GB gp3 EBS, one public IPv4 address, S3 storage/requests,
   internet transfer, SES and monitoring. Credits do not make these resources
   permanently free. Supabase billing is separate. The template does not create
   a load balancer, NAT gateway, RDS instance or paid DNS hosted zone.
4. Choose a domain you control for the final launch. Registration is separate.
   The supplied HTTPS script expects a domain resolving to the server. You can
   create the server first; do not enable customer checkout over plain HTTP.

## 2. Create the AWS resources

1. Switch the AWS console region to **Tokyo**.
2. Open EC2 → Key pairs → Create key pair. Name it `nlk-tokyo`, choose RSA and
   `.pem`, and save the downloaded file privately. Do not upload it to GitHub.
3. Open VPC and identify a VPC and a **public subnet in that VPC**, with a route
   to an internet gateway. A default VPC/subnet is suitable. If your account has
   no default VPC, create one through VPC → Your VPCs → Actions → Create default VPC.
4. Open CloudFormation → Create stack → With new resources → Upload a template
   file. Upload `deploy/aws/cloudformation.yml` from this project.
5. Name the stack `nlk-production`. Select the VPC, public subnet and key pair.
   Set `AdminCidr` to **your current public IPv4 address followed by /32**. The
   localhost default deliberately does not allow remote SSH. Leave InstanceType
   at `t3.medium` for 4 GiB RAM; choosing `t3.small` reduces memory to 2 GiB and
   requires testing PDF generation/build memory. CPU credits use standard mode
   to avoid surplus-credit billing, so sustained CPU exhaustion can throttle.
6. Review the resources and acknowledge creation of IAM resources, then Submit.
   This creates billable resources. Wait for `CREATE_COMPLETE`.
7. Open the stack Outputs tab and record `PublicIp`, `InstanceId`,
   `MediaBucketName`, `BackupBucketName` and `Region`.

The template creates private, encrypted, versioned S3 buckets and an EC2 role
with access to those two buckets. Both buckets are retained if the stack is
deleted; retained data and storage charges require separate management.
[CloudFormation workflow](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html)

## 3. Connect and put this release on the server

The deployment branch is `codex/aws-production` in
`https://github.com/GCAKuma/NLK_web.git`. Before cloning, confirm that branch is
published and includes this guide, the CloudFormation template and
`deploy/release.sh`. If it has not been published, commit and push the reviewed
release from your local Git client. Never stage `.env`,
`.env.prod`, `.env.migrate`, media, private keys or database dumps.

From Windows PowerShell, replace the key path and server IP:

```powershell
ssh -i "C:\path\nlk-tokyo.pem" ubuntu@YOUR_PUBLIC_IP
```

On the Ubuntu server:

```bash
sudo cloud-init status --wait
docker --version
docker compose version
git clone --branch codex/aws-production https://github.com/GCAKuma/NLK_web.git /opt/nlk
cd /opt/nlk
```

If Docker permission is denied, log out and reconnect so the new docker group
membership takes effect. If the repository is private, use your normal GitHub
authentication or a read-only deploy key; never paste a token into a clone URL.

## 4. Configure the domain and secrets

At your domain's DNS provider, create an A record pointing your chosen hostname
to the stack's `PublicIp`. This guide uses one hostname; only add `www` if you
also configure its DNS, certificate and allowed hosts.

```bash
cd /opt/nlk
umask 077
cp .env.prod.example .env.prod
cp .env.migrate.example .env.migrate
chmod 600 .env.prod .env.migrate
nano .env.prod
nano .env.migrate
```

Set these values directly on the server, never in chat or Git:

| Setting | Value |
| --- | --- |
| SECRET_KEY | Fresh random value, at least 50 characters; generate with `python3 -c 'import secrets; print(secrets.token_urlsafe(64))'` |
| ALLOWED_HOSTS | Your exact hostname plus `localhost,127.0.0.1` |
| CSRF_TRUSTED_ORIGINS | `https://YOUR_HOSTNAME` |
| AWS_STORAGE_BUCKET_NAME | MediaBucketName from stack Outputs |
| AWS_BACKUP_BUCKET_NAME | BackupBucketName from stack Outputs |
| AWS_S3_REGION_NAME | `ap-northeast-1` |
| USE_S3 | `True` |
| DATABASE_URL in .env.migrate | Existing owner connection from Supabase Connect → Session pooler, port 5432, with `sslmode=require` |
| DATABASE_URL in .env.prod | Same pooler host/database, username `nlk_app.PROJECT_REF`, with the dedicated password created next and `sslmode=require` |
| RUNTIME_DATABASE_ROLE | `nlk_app` |
| PG_CLIENT_IMAGE | `postgres:17`, or a client major at least as new as your Supabase server |

Session pooling provides IPv4 connectivity for this persistent Django backend.
Use the host actually shown by your project's Connect dialog. URL-encode special
characters in database passwords; do not substitute a Supabase API key for a
database password. [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
and [pooler usernames](https://supabase.com/docs/guides/troubleshooting/supavisor-faq-YyP5tI).

Build the image and create the restricted runtime role. The password prompt does
not echo your input; choose a unique password of at least 24 characters:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod build web
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --no-deps migrate python manage.py secure_application_tables --runtime-role nlk_app --set-password
```

Finish setting the matching runtime password in `.env.prod`. This role handles
normal app queries; the separate owner credential is used for migrations and
backups. Existing Django accounts and customer data remain in Supabase.

## 5. Set up transactional email

In SES in Tokyo, verify your sending domain and add the DNS records SES supplies.
Create SES SMTP credentials and set `EMAIL_HOST`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` and `ADMIN_EMAIL` in `.env.prod`.
Use SMTP port 587 with TLS. SMTP credentials are different from AWS login
credentials and are region specific. Follow SES instructions for DKIM and your
mail domain's SPF/DMARC configuration.

Request SES production access for transactional order and quotation emails.
Until approved, test only with verified recipient addresses and keep the site
closed to customers. Enable SES suppression/bounce/complaint handling in your
account. [SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

`WHATSAPP_PROVIDER=console` leaves automatic WhatsApp notifications disabled.
Configure Meta credentials separately if you need automated WhatsApp delivery.

## 6. Transfer existing images and private documents

Database records already moved to Supabase; their referenced local files also
need to reach S3. From Windows, copy the existing media directory:

```powershell
scp -i "C:\path\nlk-tokyo.pem" -r "D:\Coding\NLK web\media" ubuntu@YOUR_PUBLIC_IP:/opt/nlk/import-media
```

On the server, ensure `/opt/nlk/import-media` contains the media folders directly
(for example `products`, `invoices`, or `payment_slips`), then preview and apply:

```bash
cd /opt/nlk
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --no-deps -v /opt/nlk/import-media:/import-media:ro web python manage.py upload_media --source /import-media
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --no-deps -v /opt/nlk/import-media:/import-media:ro web python manage.py upload_media --source /import-media --apply
```

The command preserves database file paths, verifies bytes, skips identical files
and refuses to overwrite different content. Keep the source copy until live
images, historical invoices and slips are verified. Buckets stay private;
invoices/slips require Django authorization before a short-lived download URL.

## 7. Release and enable HTTPS

```bash
cd /opt/nlk
sh deploy/release.sh
sh deploy/enable-https.sh YOUR_HOSTNAME YOUR_CERTIFICATE_CONTACT_EMAIL
```

The release builds the image, creates and verifies an S3 database backup, checks
production configuration, applies migrations, secures application tables,
collects static assets, starts services and checks readiness. Stop if a command
fails; do not skip the failed step. There is deliberately no demo-data seeding.

Two Django deployment warnings are expected initially: HSTS does not include
all subdomains and is not preloaded. Enable those only after every relevant
subdomain supports HTTPS and you understand the domain-wide effect.

## 8. Enable maintenance and actual alerts

```bash
sudo cp deploy/aws/nlk-*.service deploy/aws/nlk-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nlk-backup.timer nlk-certificates.timer nlk-health.timer
sudo systemctl start nlk-backup.service nlk-health.service
systemctl list-timers 'nlk-*'
sudo journalctl -u nlk-backup.service -u nlk-health.service --since today
```

Backups run hourly and expire from S3 under the configured lifecycle; local
copies older than 14 days are removed only after upload verification. Certificate
renewal runs twice daily. Health checks run every five minutes and fail when the
database/cache is unavailable or notification jobs are stuck/exhausted.

**The timers write to the journal; they do not email you.** In CloudWatch, open
the stack's EC2 status alarm and configure an SNS email notification action.
Confirm the subscription email. Add an external HTTPS readiness check and wire
backup/health service failures to your monitoring before accepting orders.
The EC2 alarm alone does not detect checkout, mail or backup failures.

## 9. Acceptance before opening the store

- Check the homepage, search, product detail, cart and checkout on desktop and
  mobile. Check real image loading, keyboard access and form errors.
- Use a designated test customer and product: register, sign in, reset password,
  place one order, verify stock changes exactly once, and verify its PDF and both
  intended emails. Repeated submission must not create another order.
- Upload a test payment slip and confirm another customer's account cannot read
  it or an invoice. Test historical private documents after S3 migration.
- Submit a quotation and verify the admin receives it.
- Check Admin → Notification jobs and service logs for unfinished work. Delivery
  retries are durable and separated by recipient. SMTP cannot guarantee exactly
  once delivery if a worker crashes immediately after the mail provider accepts
  a message; a rare duplicate remains possible.
- Download a backup and restore it into a **separate disposable PostgreSQL
  database**, compare important row counts and open restored records. Never test
  restore against live Supabase. Dumps cover the Django `public` schema, not
  Supabase-managed auth/storage schemas or database roles; S3 media is separate.
- Measure response time and memory under expected concurrent browsing and PDF
  generation. Set a load target based on anticipated traffic before claiming
  production capacity. Check CPU credit balance and Supabase connection usage.

Useful server commands:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail 100 web celery dispatcher
sh deploy/check-health.sh
```

For an update, record the currently deployed Git commit, pull the reviewed release
and run `sh deploy/release.sh`. If a release fails, retain the backup and logs.
Revert application code only when it is compatible with the current schema;
restoring an older database loses subsequent writes and needs a planned recovery.
Do not delete Docker volumes to troubleshoot a failed deployment.

## Validation completed locally

- Production Linux image and compiled frontend built successfully.
- 55 PostgreSQL tests passed, including checkout concurrency, private media,
  invoice rendering, notification retries and restricted database permissions.
- Model/migration consistency checked against isolated PostgreSQL.
- CloudFormation passed cfn-lint; production Compose configuration validated.
- HTTPS Nginx configuration validated with a disposable local certificate.

AWS provisioning, IAM access from EC2, hosted-role login, S3 transfer, SES delivery,
real DNS/certificate issuance, restore drill and live load tests remain account
setup/acceptance steps. No local test is evidence those cloud operations happened.
