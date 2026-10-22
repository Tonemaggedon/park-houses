#!/usr/bin/env python3
"""Ask every contributor to choose a new password.

Railway disclosed on 21 October 2026 that customer environment variables may
have been read, database credentials among them. The password hashes in this
record are bcrypt and ten of them is not a prize, so this is the proportionate
step rather than the drastic one: nobody is locked out and no password has to
be carried to anybody. Each person is simply asked to pick a new one the next
time they sign in, which they do themselves on Your part in it.

The flag clears the moment they choose.
"""
import os, sys, psycopg2

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""UPDATE users SET must_change_password = TRUE
                WHERE must_change_password IS NOT TRUE
            RETURNING id, email, role""")
rows = cur.fetchall()
for i, e, r in rows:
    print(f'  #{i:<3} {e:<30} {r}')
print(f'\n{len(rows)} accounts will be asked to choose a new password at next sign-in')
cur.execute("SELECT COUNT(*)::int FROM users WHERE must_change_password")
print('flagged in total:', cur.fetchone()[0])
c.commit(); cur.close(); c.close()
