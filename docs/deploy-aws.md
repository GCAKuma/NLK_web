# Deploying to AWS (evaluation phase)

This walks through hosting the existing `docker-compose.prod.yml` stack on a
single AWS EC2 instance — the simplest path that matches what's already
built, appropriate for a ~6 month evaluation before deciding on long-term
hosting. Nothing here requires rewriting the app: it's the same Docker Compose
stack, just running on an AWS VM instead of a laptop.

Steps with a ⚠ require the AWS/registrar console directly — an AI assistant
can't click through your account for you (or shouldn't: it's your billing,
your credentials).

## 1. Launch the server ⚠

In the EC2 console:
- **AMI**: Ubuntu Server 22.04 LTS
- **Instance type**: `t3.small` (2 GB RAM) recommended — Postgres + Redis +
  Gunicorn + Celery + Nginx together are tight on `t3.micro`'s 1 GB. If you
  want to stay inside the AWS Free Tier (750 hrs/month of `t2.micro` or
  `t3.micro` for a new account's first 12 months), `t3.micro` will *run* it,
  just with less headroom under load.
- **Storage**: 20–30 GB gp3 EBS volume (default 8 GB is too small once
  product images and Postgres data accumulate).
- **Security group**: allow inbound `22` (SSH — restrict to your IP if
  possible), `80`, `443`. Nothing else needs to be open; Postgres/Redis stay
  inside the Docker network.
- **Key pair**: create one and save the `.pem` — it's your only way in.

## 2. Allocate an Elastic IP ⚠

A plain EC2 public IP changes if the instance stops/restarts, which would
silently break DNS. Allocate an **Elastic IP** (EC2 → Network & Security →
Elastic IPs) and associate it with the instance — it's free while attached
to a running instance. This is the IP your DNS record will point to.

## 3. Install Docker on the instance

SSH in (`ssh -i your-key.pem ubuntu@<elastic-ip>`), then:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
sudo apt install -y docker-compose-plugin
```

## 4. Get the code and configure it

```bash
git clone <your-repo-url> nlk && cd nlk
cp .env.prod.example .env.prod
nano .env.prod   # fill in SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, etc.
```

For the evaluation phase, set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to
whatever hostname you'll test with (a subdomain or the Elastic IP itself —
see step 6).

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod exec web \
    python manage.py createsuperuser
```

The site is now reachable at `http://<elastic-ip>/`.

## 5. Point your domain at it ⚠

You already own the domain — this is the one step where it comes in, and
it's just a DNS record, not a purchase. Wherever you bought/manage the
domain's DNS (your registrar, or Route 53 if you've delegated it there):

- Add an **A record** pointing a hostname to the Elastic IP.

**Recommendation for the evaluation window:** point a subdomain (e.g.
`test.yourdomain.tld` or `beta.yourdomain.tld`) rather than the bare domain.
Reasoning: it keeps the real domain "unused" and clean of test data/traffic
while you're evaluating on AWS, and switching to the bare domain later is
just adding one more A record — nothing about the app changes. If you'd
rather test on the real domain directly, that's fine too; DNS changes are
cheap and reversible either way, so it's a preference, not a technical
requirement.

DNS propagation is usually minutes, occasionally a few hours.

## 6. Enable HTTPS

Once the hostname resolves to the Elastic IP, follow **README → "Enable
HTTPS"** — it's the same `certbot` flow regardless of host (AWS, DigitalOcean,
anywhere), already wired into `docker-compose.prod.yml`.

## 7. Set a billing alarm ⚠

Since this is a timeboxed 6-month trial: AWS Budgets (Billing console →
Budgets → Create budget) can email you if spend crosses a threshold — cheap
insurance against a surprise bill if you forget to check in on it. Takes two
minutes to set up.

## Cost ballpark

Rough, region-dependent — check the [AWS Pricing Calculator](https://calculator.aws)
for a real number:
- `t3.small` on-demand: ~US$15/month (~US$0 if still inside the Free Tier's
  first year on `t3.micro`)
- 20 GB gp3 EBS: ~US$1.60/month
- Elastic IP: free while attached to a running instance
- Data transfer out: negligible at evaluation-scale traffic

## Later: moving off this instance

Everything above is disposable — the app, database schema, and Docker setup
don't change based on where they run. If after the evaluation you move to
different AWS resources (RDS for the database, ECS instead of one VM, S3 for
media) or to another host entirely, it's an infrastructure change, not an
app change: `docker-compose.prod.yml`, `.env.prod`, and this repo stay the
same shape.
