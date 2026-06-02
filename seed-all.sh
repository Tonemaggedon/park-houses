#!/bin/bash
# Run all seed files against Railway
URL="https://park-houses-production.up.railway.app"
EMAIL="admin"
PASS="parkhouses2024"

cd "$(dirname "$0")"

for f in data/seed-*.json; do
  ID=$(echo "$f" | grep -oE 'seed-([0-9]+)-' | grep -oE '[0-9]+' | head -1)
  echo "Seeding property $ID from $f..."
  node seed.js "$URL" "$EMAIL" "$PASS" "$ID" "$f"
  echo "---"
done
echo "All done!"
