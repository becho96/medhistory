## Summary

- 

## Linked issue

Closes #

## Product decision / scope

- [ ] No product decision needed
- [ ] Product decision confirmed by Boris in linked issue
- [ ] Scope/non-goals are documented in linked issue

## Risk gates

Check any touched area:

- [ ] Auth/session flow
- [ ] Database migration
- [ ] PII / medical document data
- [ ] Medical interpretation or user-facing medical wording
- [ ] Legal documents / consent flow
- [ ] `.env.production`, nginx, GitHub Actions, deploy scripts
- [ ] Production deploy required
- [ ] None of the above

If any risky area is checked, include Boris approval link/comment before merge/deploy.

## Test plan

- [ ] Frontend build/typecheck (`npm run build` or `npx tsc --noEmit`) if frontend changed
- [ ] Backend targeted tests if backend changed
- [ ] UI verified locally on dev build if UI changed
- [ ] Document analysis benchmark considered if document analysis changed
- [ ] Not applicable / explain why:

## Deployment

- [ ] No deploy needed
- [ ] Deploy after Boris approval
- [ ] Deployed via GitHub Actions

Deployment run/link:
