# Monitored sources per platform (A–Z)

This document lists the endpoints and feeds each plugin uses. All token validation and change collection runs locally; token-doctor never sends tokens to its own servers.

## Acxiom

- **Token validation:** (No standard public /me in MVP; see Acxiom developer portal.)
- **Change feeds:** (None in MVP.)

## Adobe

- **Token validation:** `GET https://ims-na1.adobelogin.com/ims/userinfo`.
- **Change feeds:** Adobe developer blog feed.

## Amazon (Amazon Ads API)

- **Token validation:** `GET https://advertising-api.amazon.com/v2/profiles` (optional profile option `client_id`).
- **Change feeds:** Amazon Advertising API docs feed, AWS developer blog.

## Apple Search Ads

- **Token validation:** `GET https://api.searchads.apple.com/api/v5/acls` (Bearer JWT).
- **Change feeds:** (None in MVP.)

## Atlassian (Jira/Confluence)

- **Token validation:** `GET {base_url}/rest/api/3/myself` — set profile option `base_url` (e.g. `https://your-site.atlassian.net`).
- **Change feeds:** Developer blog, Confluence allposts feed.

## Auth0

- **Token validation:** `GET https://{tenant}.auth0.com/userinfo` — set profile option `tenant`.
- **Change feeds:** Auth0 blog RSS.

## Bing Ads

- **Token validation:** (Skipped in MVP; see Microsoft Advertising API.)
- **Change feeds:** Microsoft Advertising blog feed.

## Bitbucket

- **Token validation:** `GET https://api.bitbucket.org/2.0/user`.
- **Change feeds:** Bitbucket blog feed.

## Box

- **Token validation:** `GET https://api.box.com/2.0/users/me`.
- **Change feeds:** (No public RSS documented.)

## Braze

- **Token validation:** `GET {rest_url}/dashboard/data_export` (Bearer) — set profile option `rest_url` (e.g. `https://rest.iad-01.braze.com`).
- **Change feeds:** (None in MVP.)

## Brevo (Sendinblue)

- **Token validation:** `GET https://api.brevo.com/v3/account` (header `api-key`).
- **Change feeds:** (None in MVP.)

## Cloudflare

- **Token validation:** `GET https://api.cloudflare.com/client/v4/user`.
- **Change feeds:** Cloudflare blog RSS.

## DigitalOcean

- **Token validation:** `GET https://api.digitalocean.com/v2/account`.
- **Change feeds:** Community blog and product blog feeds.

## Discord

- **Token validation:** `GET https://discord.com/api/v10/users/@me`.
- **Change feeds:** Discord blog and developer docs feeds.

## Dropbox

- **Token validation:** `POST https://api.dropboxapi.com/2/users/get_current_account`.
- **Change feeds:** Dropbox blog feed.

## GitHub

- **Token validation:** `GET https://api.github.com/user`.
- **Change feeds:** GitHub blog changelog, developer changelog RSS.

## GitLab

- **Token validation:** `GET https://gitlab.com/api/v4/user`.
- **Change feeds:** About GitLab and blog feed.

## Campaign Manager 360 (CM360)

- **Token validation:** `GET https://dfareporting.googleapis.com/dfareporting/v4/userprofiles`.
- **Change feeds:** Google Ads release notes feed.

## Criteo

- **Token validation:** (Skipped in MVP; see Criteo Marketing API.)
- **Change feeds:** (None in MVP.)

## Display & Video 360 (DV360)

- **Token validation:** `GET https://doubleclickbidmanager.googleapis.com/v2/queries`.
- **Change feeds:** Google Ads release notes feed.

## Google Ads API

- **Token validation:** (No simple /me in MVP.)
- **Change feeds:** Release notes feed, Ads developer blog.

## Heroku

- **Token validation:** `GET https://api.heroku.com/account`.
- **Change feeds:** Heroku blog feed.

## HubSpot

- **Token validation:** `GET https://api.hubapi.com/account-info/v3/details` (Bearer).
- **Change feeds:** (None in MVP.)

## Instagram (Meta)

- **Token validation:** `GET https://graph.instagram.com/v18.0/me`.
- **Change feeds:** Meta developer blog feed.

## Iterable

- **Token validation:** `GET https://api.iterable.com/api/campaigns` (header `Api-Key`).
- **Change feeds:** (None in MVP.)

## Klaviyo

- **Token validation:** `GET https://a.klaviyo.com/api/lists` (header `Klaviyo-API-Key` and `revision`).
- **Change feeds:** (None in MVP.)

## Linear

- **Token validation:** `POST https://api.linear.app/graphql` (viewer query).
- **Change feeds:** Linear blog feed.

## LinkedIn

- **Token validation:** `GET https://api.linkedin.com/v2/me`.
- **Change feeds:** LinkedIn developer feed.

## Mailchimp

- **Token validation:** `GET https://{dc}.api.mailchimp.com/3.0/ping` — Basic (anystring:apikey) or Bearer; set profile option `dc` or derive from API key.
- **Change feeds:** (None in MVP.)

## Meta Marketing API

- **Token validation:** `GET https://graph.facebook.com/v21.0/me`.
- **Change feeds:** Facebook developers blog feed.

## Meta Messenger

- **Token validation:** `GET https://graph.facebook.com/v21.0/me`.
- **Change feeds:** Meta developer blog feed.

## Microsoft (Graph / Azure AD)

- **Token validation:** `GET https://graph.microsoft.com/v1.0/me`.
- **Change feeds:** Microsoft 365 dev blog, Graph blog feed.

## Netlify

- **Token validation:** `GET https://api.netlify.com/api/v1/user`.
- **Change feeds:** Netlify blog feed.

## Notion

- **Token validation:** `GET https://api.notion.com/v1/users/me` (with Notion-Version header).
- **Change feeds:** (No public API changelog RSS.)

## Pinterest

- **Token validation:** `GET https://api.pinterest.com/v5/user_account`.
- **Change feeds:** Pinterest developer blog feed.

## Quora

- **Token validation:** (Skipped in MVP; see Quora Ads API.)
- **Change feeds:** (None in MVP.)

## Reddit

- **Token validation:** `GET https://oauth.reddit.com/api/v1/me`.
- **Change feeds:** r/redditdev subreddit RSS.

## Search Ads 360 (SA360)

- **Token validation:** `GET https://searchads.googleapis.com/v2/customers:listAccessibleCustomers`.
- **Change feeds:** Google Ads release notes feed.

## Salesforce

- **Token validation:** `GET {instance_url}/services/oauth2/userinfo` (Bearer) — set profile option `instance_url`.
- **Change feeds:** (None in MVP.)

## Segment

- **Token validation:** `GET https://api.segmentapis.com/workspaces` (Bearer).
- **Change feeds:** (None in MVP.)

## SendGrid

- **Token validation:** `GET https://api.sendgrid.com/v3/user/account`.
- **Change feeds:** SendGrid blog feed.

## SharePoint (Microsoft Graph)

- **Token validation:** `GET https://graph.microsoft.com/v1.0/sites/root`.
- **Change feeds:** Microsoft 365 dev blog feed.

## Slack

- **Token validation:** `POST https://slack.com/api/auth.test`.
- **Change feeds:** Slack changelog (when available).

## Snapchat (Marketing API)

- **Token validation:** `GET https://businessapi.snapchat.com/v1/me`.
- **Change feeds:** (None in MVP.)

## Stripe

- **Token validation:** `GET https://api.stripe.com/v1/account`.
- **Change feeds:** Docs changelog URL (no RSS in MVP).

## Taboola

- **Token validation:** (Skipped in MVP; see Taboola API.)
- **Change feeds:** (None in MVP.)

## The Trade Desk

- **Token validation:** (Skipped in MVP; see TTD API.)
- **Change feeds:** (None in MVP.)

## TikTok (Business API)

- **Token validation:** `GET https://business-api.tiktok.com/open_api/v1.3/user/info/`.
- **Change feeds:** (None in MVP.)

## Twilio

- **Token validation:** `GET https://api.twilio.com/2010-04-01/Accounts.json` (Basic auth: Account SID + Auth Token). Token can be `SID:Token` or set profile option `account_sid` and token as Auth Token.
- **Change feeds:** Twilio blog feed.

## Twitter / X

- **Token validation:** `GET https://api.twitter.com/2/users/me`.
- **Change feeds:** Twitter/X developer blog feed.

## Vercel

- **Token validation:** `GET https://api.vercel.com/v2/user`.
- **Change feeds:** Vercel blog and changelog feeds.

## Verizon

- **Token validation:** (Not implemented in MVP; see Verizon developer portal.)
- **Change feeds:** (None in MVP.)

## WhatsApp (Meta Cloud API)

- **Token validation:** `GET https://graph.facebook.com/v21.0/me` (same Graph token).
- **Change feeds:** Meta developer blog feed.

## Yahoo (Yahoo Ads)

- **Token validation:** `GET https://api.admanager.yahoo.com/v3/rest/reports/metadata`.
- **Change feeds:** (None in MVP.)

## Zoom

- **Token validation:** `GET https://api.zoom.us/v2/users/me`.
- **Change feeds:** Zoom developer blog feed.

---

**Confidence levels:** Official API/docs or release-notes feeds → high; official vendor blog → medium; scraped HTML (opt-in) → low.
