# 9. A security pass before submitting to Apple

**In short:** a security audit of the server before App Store submission found a set of issues, all fixed in one batch (D588). This page lists the categories, not the attack details.

## What was fixed
- **Order of actions:** a giver can confirm a collection or a missed pickup only once the app's "did they collect it?" question is due, three hours after the pickup window ends (moved into 9 AM to 9 PM local), not at any time after booking.
- **Ownership:** stored photo addresses must be the user's own objects, and deletes touch only the owner's folder.
- **The agent's reads:** the support agent fetches photos without following redirects.
- **Admin:** the admin push-device route requires an admin.
- **Location:** cancelled and missed claims show only the approximate point.
- **Rate limits:** on payments, messages, listing creation, completion uploads and signed-out browsing. The IP limiter keys on the one header the hosting edge sets and a client can't forge.
- **Exposure:** API docs are off in production.

A second batch for the admin dashboard (escaping and security headers) followed.

## What this shows
Security was treated as part of shipping, not an afterthought, and was done before strangers could reach the app.
