#!/usr/bin/env python3
"""The 1939 Register finds her in Marylebone, and she has stopped hedging.

A. Hagues supplied the page: 10 Luxborough House, Baker Street, City of
Westminster, St Marylebone. Schedule 129, line 1:

    Fyleman, Rose A.   F   6.3.77   S   Writer

Two things worth having. It confirms her date of birth — 6 March 1877 — from
an official record rather than from an article. And the occupation column,
which she filled in herself, says one word.

That completes a sequence the record can now show in her own hand across
twenty-eight years, which is the real find here:

    1911 census, 29 Newcastle Drive   Vocalist, own account
    1913-14 and 1915-16 directory     Feilmann Miss Rose, vocalist
    1921 census, Albury, Surrey       Teacher of voice production and authoress
    1939 Register, Marylebone         Writer

Luxborough House is a block of flats off Marylebone Road, so again nothing is
filed against a property: it is not in The Park.
"""
import os, sys
import psycopg2

ROSE = 5130

OLD = """Her own account of herself, 1921
By the 1921 census she had left Nottingham. She was boarding at Newlands Corner, Albury in Surrey, in the household of Charles Spanner, a council roadman, and his wife Clara — and the form has her, in her own words, as **teacher of voice production and authoress**, working on her own account. Four years after Punch printed the fairies, the singer had become a writer and was still teaching the voice. Her brother Frederick, forty, was boarding in the same house, a salesman for the International Multigraph Company. Both of them were entered as Fyleman."""

NEW = """What she called herself
The record can follow her description of her own work across twenty-eight years, every line of it written on a form rather than by a biographer.

| | | |
|---|---|---|
| **1911** | 29 Newcastle Drive | Vocalist, own account |
| **1913-14, 1915-16** | Wright's Directory, same house | Feilmann Miss Rose, vocalist |
| **1921** | Albury, Surrey | Teacher of voice production and authoress, own account |
| **1939** | Marylebone, London | Writer |

By the 1921 census she had left Nottingham, and was boarding at Newlands Corner, Albury in Surrey, in the household of Charles Spanner, a council roadman, and his wife Clara. Four years after Punch printed the fairies the singer had become a writer and was still teaching the voice, and the form says so in that order. Her brother Frederick, forty, was boarding in the same house, a salesman for the International Multigraph Company. Both of them were entered as Fyleman.

The 1939 Register, taken on the night this record's own last census was taken, finds her at 10 Luxborough House, Baker Street, in Marylebone — single, born 6 March 1877, and down to one word: **Writer**. The register also settles her date of birth from an official source rather than an account of her."""


def main():
    url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    c = psycopg2.connect(url)
    cur = c.cursor()
    cur.execute("SELECT bio FROM people WHERE id=%s", (ROSE,))
    bio = cur.fetchone()[0]
    if 'Luxborough' in bio:
        print('already has the 1939 Register')
    else:
        assert OLD in bio, 'the 1921 paragraph has moved'
        cur.execute("UPDATE people SET bio=%s WHERE id=%s", (bio.replace(OLD, NEW), ROSE))
        print('Rose — the 1939 Register added, and the four self-descriptions set side by side')
    # The register is a primary source for the birth date the record already shows.
    cur.execute("""UPDATE people SET born_date='6 March 1877', born_year=1877 WHERE id=%s""", (ROSE,))
    c.commit(); cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
