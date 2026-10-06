#!/bin/sh
# Runs on every Netlify deploy (see netlify.toml). The site itself is prebuilt static HTML.
# Demo and preview deploys must never be indexed; the production domain stays indexable.
# Netlify sets URL to the site's primary URL (a custom domain once brsmove.com is attached)
# and CONTEXT to production, deploy-preview or branch-deploy.
set -eu
noindex=0
case "${URL:-}" in *.netlify.app*) noindex=1 ;; esac
[ "${CONTEXT:-production}" != "production" ] && noindex=1
if [ "$noindex" = "1" ]; then
  printf '/*\n  X-Robots-Tag: noindex, nofollow\n' > _headers
  echo "netlify-build: non-production deploy, X-Robots-Tag noindex enabled"
else
  rm -f _headers
  echo "netlify-build: production deploy, indexing allowed"
fi
