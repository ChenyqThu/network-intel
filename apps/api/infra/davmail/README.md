# davmail email transport (nintel)

davmail bridges a local **SMTP (1025)** / **IMAP (1143)** server to the Omada
Exchange/O365 mailbox over OAuth, so `nintel.pipeline send` can deliver report
emails (SMTP) or stage drafts (IMAP APPEND). Runs as a Docker container
(`eclipse-temurin:17-jre` + davmail 6.8.0), bound to `127.0.0.1` only.

## Auth model

- IMAP/SMTP **password = the davmail cipher key** (a string you choose), NOT the
  O365 password. Set it as `NINTEL_DAVMAIL_CIPHER_KEY` in `apps/api/.env`.
- The cipher key encrypts `token.dat` (the cached OAuth refresh token). After a
  one-time interactive sign-in, `token.dat` auto-refreshes — no re-auth per send.
- `token.dat` is a **secret** and is gitignored. Do not commit or delete it.

## First-time setup

```sh
./fetch-davmail.sh                                  # download davmail.jar + lib/
./bootstrap-auth.sh lucien.chen@omadanetworks.com '<cipher-key>'   # one-time OAuth
```

`bootstrap-auth.sh` prints an OAuth URL; sign in (account + MFA + **Continue**).

> ⚠️ **This tenant requires the OOB redirect** (`davmail.oauth.redirectUri=urn:ietf:wg:oauth:2.0:oob`
> in `davmail.properties`). davmail's default `…/oauth2/nativeclient` is not
> registered for the well-known Office client here → `AADSTS50011`.
>
> With OOB, the authorization code is **not shown on the page**. After Continue the
> browser lands on a blank/error page; open **DevTools → Network**, find the failed
> request whose URL starts with `urn:ietf:wg:oauth:2.0:oob?code=…`, and copy that
> whole URL back into the script. Codes expire quickly (`AADSTS70008`), so be quick.

## Normal operation (pm2)

`run-davmail.sh` is supervised by pm2 as the `nintel-davmail` app:

```sh
pm2 start ecosystem.config.cjs        # starts nintel-davmail alongside api/web
pm2 restart nintel-davmail            # after editing davmail.properties
docker logs nintel-davmail            # troubleshoot
```

Quick health check:

```sh
nc -vz 127.0.0.1 1025 && nc -vz 127.0.0.1 1143
```

## ⚠️ Expiry / migration

davmail uses **EWS**, which Microsoft shuts down around **2026-10-01**. This is a
bridge, not the endgame — migrate to Microsoft Graph `sendMail` before then. Only
`engine/mailer.py`'s send/draft functions change; `build_report_message` is reused.
The PoC well-known client_id is fine for internal self-use but should be replaced
with a proper Azure app registration before any production/external use.
