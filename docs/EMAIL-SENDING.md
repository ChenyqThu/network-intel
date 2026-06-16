# Email delivery (daily/weekly reports)

nintel can deliver each published report by email — as a **draft** for review
(default) or a direct **send** — from the real Omada mailbox.

## Architecture

`engine/render.py::render_email(report)` already produces email-safe HTML. The
transport is **davmail** (`apps/api/infra/davmail/`), a local SMTP/IMAP ↔
Exchange/O365 bridge running in Docker as the `nintel-davmail` pm2 app (bound to
`127.0.0.1`). `engine/mailer.py` builds the MIME and either SMTP-sends or
IMAP-APPENDs a draft. `python -m nintel.pipeline send` is the entry point.

- **draft** (default): IMAP APPEND into Drafts → review in Outlook/OWA → send by hand.
- **send**: SMTP straight to `NINTEL_MAIL_TO`.

`send` emails the **already-published** report (so the email matches the live site);
it does not rebuild the pipeline.

## Setup (one-time)

```sh
cd apps/api/infra/davmail
./fetch-davmail.sh                                                # download davmail jar
./bootstrap-auth.sh lucien.chen@omadanetworks.com '<cipher-key>' # OAuth — see README.md
```

Then fill the email vars in `apps/api/.env` (see `.env.example`) and start the bridge:

```sh
pm2 start ecosystem.config.cjs    # brings up nintel-davmail alongside api/web
```

> The login password is the davmail **cipher key** (you choose it; it encrypts
> `token.dat`), NOT the O365 password. This tenant requires the **OOB** redirect, and
> the auth code is captured from the browser's Network panel, not the page. Full
> detail and the re-auth procedure: `apps/api/infra/davmail/README.md`.

## Usage

```sh
cd apps/api
.venv/bin/python -m nintel.pipeline send --type daily             # default mode (draft)
.venv/bin/python -m nintel.pipeline send --type daily  --draft    # force draft
.venv/bin/python -m nintel.pipeline send --type weekly --send     # force send
.venv/bin/python -m nintel.pipeline send --type daily  --report-id 2026-06-01-daily
```

The command fails loud (non-zero exit) if credentials are unset, no published report
exists, or davmail is unreachable / its token expired — so a scheduled run surfaces
the problem instead of silently not delivering.

## Status / limits

- Verified end-to-end on the mac (2026-06-16): IMAP + SMTP auth, draft staged into
  Drafts, real mailbox reachable.
- **Manual trigger only** for now. To auto-deliver on schedule, add a `send` (or
  `send --draft`) step after the build in `apps/api/scripts/run_pipeline.sh` (deferred
  until a real send is confirmed in production).
- 🔴 **EWS shuts down around 2026-10-01.** davmail uses EWS, so this is a ~3.5-month
  bridge — migrate `engine/mailer.py`'s send/draft to Microsoft Graph `sendMail` before
  then (`build_report_message` is reused; only the transport changes). The PoC
  well-known client_id should become a proper Azure app registration before any
  external/production use.

Origin: this feature was specced by a handoff from the MailAgent project; the davmail
specifics that proved out in practice are recorded here and in the infra README.
