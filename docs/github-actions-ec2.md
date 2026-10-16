# Automatic deployment to the NLK test server

This setup is for the existing private GCAKuma/NLK_web repository and the single
Tokyo EC2 server. It does not add AWS resources or open SSH to the internet.

Flow: push to `charith/aws-production` → GitHub builds the production image and
runs isolated PostgreSQL tests → a runner on EC2 fetches the same commit, builds
the image there, backs up Supabase to S3, migrates, restarts and checks HTTPS.
The image is built twice; no registry or image-upload storage is required.
The EC2 build uses the t3.small's CPU/memory, so do not run load tests during it.
This is a single-server release with possible brief downtime, not a rolling deployment.

## Before enabling

Complete one manual release first. At the last confirmed server state, the
repository was cloned but private environment configuration was not confirmed.
These must work before automatic deployments can succeed:

- `/opt/nlk/.env.prod`: strong secret, restricted database login, S3 bucket names,
  Tokyo region and test email backend.
- `/opt/nlk/.env.migrate`: owner database URL used for backup/migration only.
- Runtime role created, media transferred, successful initial release and HTTPS.
- `/opt/nlk/nginx/active.conf` and a running Nginx container with a valid certificate.
- The existing `nlk_github` deploy key must still allow server-side Git fetches.

Use an IP-address certificate for the domain-free test. The old
`enable-https.sh` is domain based; it must be adapted for Certbot's IP certificate
flags before using it for this test. Do not simply pass the IP to its `-d` flag.
Keep the database URLs and `.env` files on EC2, out of GitHub and workflow logs.

## 1. Publish the workflow

The relevant files are `.github/workflows/verify.yml` and
`deploy/github-deploy.sh`. Commit and push them to `charith/aws-production`.
The deploy job remains skipped while `EC2_DEPLOY_ENABLED` is absent or false.
Tests run on GitHub-hosted Ubuntu; pull requests never use the EC2 runner in
this workflow.

## 2. Register a runner on the existing EC2 instance

Keep this repository private and restrict repository access to trusted people.
The runner can access this server's Docker daemon and deployment secrets.
Branch checks in this workflow are not a sandbox against someone who can change
workflows. Do not run untrusted workflows on this server or attach public repos.

In GitHub open **NLK_web → Settings → Actions → Runners → New self-hosted runner**.
Select **Linux** and **x64**. GitHub displays current download, checksum and
registration commands with a short-lived token.

In your Ubuntu SSH terminal:

```bash
cd ~
mkdir -p actions-runner
cd actions-runner
```

Run the download, checksum verification, extraction and `./config.sh` commands
shown by GitHub from this directory. If GitHub's download block also contains
`mkdir actions-runner` and `cd actions-runner`, skip those two lines since you
already created and entered the directory. Do not share the registration token.

During configuration:

| Prompt | Answer |
| --- | --- |
| Runner group | Default (press Enter) |
| Runner name | `nlk-test-ec2` |
| Additional labels | `nlk-test` |
| Work folder | `_work` (press Enter) |

Do not place the runner work folder inside `/opt/nlk`. Install the service as
the existing ubuntu user, who already has Docker access:

```bash
sudo ./svc.sh install ubuntu
sudo ./svc.sh start
sudo ./svc.sh status
```

GitHub's runner page should show **Idle**. The runner connects outbound to GitHub;
your current SSH rule stays restricted to your computer. No GitHub SSH secret,
AWS access key, extra EC2 instance, or paid runner size is needed.

## 3. Enable only after the site works

GitHub → **Settings → Secrets and variables → Actions → Variables**.
Create repository variables (not secrets):

| Name | Value |
| --- | --- |
| `EC2_TEST_URL` | `https://35.79.172.45` (update if the server address changes) |
| `EC2_DEPLOY_ENABLED` | `true` |

Protect/restrict writes to `charith/aws-production` where your GitHub plan permits.
Only push code you trust. The configured workflow deploys only pushes to this
branch in the original private repository after its `verify` job passes.

## 4. Trigger and inspect

Commit a normal application change on `charith/aws-production` and push it.
On GitHub open **Actions → Test and deploy EC2 → the latest run**.
Both `verify` and `deploy` should succeed. Check the deployed website too.

The deploy script refuses missing setup, local checkout changes, wrong branch
or non-fast-forward updates. A superseded commit is skipped instead of deploying
newer, untested code. Concurrent deployments are serialized, with an additional
server lock. Failure stops the job; it does not automatically roll back database
changes. Inspect the failed step and preserve its backup before recovery.

Set `EC2_DEPLOY_ENABLED=false` to disable future deployment jobs. This does not
stop an already-running job or EC2 billing.

## Costs and upkeep

AWS credits continue to cover eligible EC2/storage usage; creating a workflow
does not pause the server between deployments. As of 14 October 2026, GitHub's
documentation lists self-hosted runner usage as free. GitHub-hosted tests in this
private repository consume the GitHub account's included Actions allowance;
AWS credits cannot pay GitHub bills. In GitHub Billing, keep paid Actions usage
blocked or configure a budget that stops paid usage. If included minutes are
exhausted, accept paused CI rather than enabling paid usage.

Check disk space with `df -h /` and `docker system df` periodically: rebuilt
images and build caches accumulate. Do not prune volumes containing live data.
Keep the runner updated. Remove it from GitHub when the AWS test server is retired.

References:
- [Runner installation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)
- [Runner service](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application)
- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
