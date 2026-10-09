#!/bin/sh
# Run the site locally against the Railway database.
# `railway run` injects DATABASE_URL pointing at postgres.railway.internal, which
# only resolves inside Railway; DATABASE_PUBLIC_URL is the one that works from here.
export DATABASE_URL="${DATABASE_PUBLIC_URL:-$DATABASE_URL}"
exec node server.js
