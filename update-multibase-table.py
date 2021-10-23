"""
    Pulls the current multibase table from the [multibase spec](https://github.com/multiformats/multibase)
"""

import csv
import io
import pprint
import textwrap

# not a dependency for the `multiformats` library
import requests

from multiformats import multibase

# Fetches and validates the new multibase table from the multibase spec GitHub repo:
multibase_table_url = "https://github.com/multiformats/multibase/raw/master/multibase.csv"
print("Fetching multibase table from:")
print(multibase_table_url)
print()

new_bytes = requests.get(multibase_table_url).content
new_text = new_bytes.decode("utf-8")
print("Building new multibase table...")
reader = csv.DictReader(io.StringIO(new_text))
clean_rows = ({k.strip(): v.strip() for k, v in row.items()} for row in reader)
renamed_rows = ({(k if k != "encoding" else "name"): v for k, v in row.items()} for row in clean_rows)
encodings = (multibase.Encoding(**{k.strip(): v.strip() for k, v in _row.items()})
             for _row in renamed_rows)
new_table, _ = multibase.build_multibase_tables(encodings)

# Loads and validates the current multibase table:
print("Building current multibase table...")
with open("multiformats/multibase/multibase-table.csv", "r") as f:
    current_text = f.read()
reader = csv.DictReader(io.StringIO(current_text))
clean_rows = ({k.strip(): v.strip() for k, v in row.items()} for row in reader)
renamed_rows = ({(k if k != "encoding" else "name"): v for k, v in row.items()} for row in clean_rows)
encodings = (multibase.Encoding(**{k.strip(): v.strip() for k, v in _row.items()})
             for _row in renamed_rows)
current_table, _ = multibase.build_multibase_tables(encodings)

print()

# Displays added encodings, if any:
added = {
    code: m
    for code, m in new_table.items()
    if code not in current_table
}
if added:
    print(f"Added {len(added)} new encodings:")
    for m in sorted(added.values(), key=lambda m: m.code):
        print(textwrap.indent(pprint.pformat(m.to_json()), "  "))
else:
    print("Added no new encodings.")

# Displays removed encodings, if any:
removed = {
    code: m
    for code, m in current_table.items()
    if code not in new_table
}
if removed:
    print(f"Removed {len(added)} existing encodings:")
    for m in sorted(removed.values(), key=lambda m: m.code):
        print(textwrap.indent(pprint.pformat(m.to_json()), "  "))
else:
    print("Removed no existing encodings.")

# Displays changed encodings, if any:
changed = {
    code: (m, new_table[code])
    for code, m in current_table.items()
    if code in new_table and new_table[code] != m
}

if changed:
    print(f"Changed {len(added)} existing encodings:")
    for m_old, m_new in sorted(changed.values(), key=lambda pair: pair[0].code):
        print(f"  Changes in protocol {repr(m_old.code)}:")
        for attr in ("name", "status", "description"):
            old_val, new_val = (getattr(m_old, attr), getattr(m_new, attr))
            if old_val != new_val:
                print(f"    {attr}: {repr(old_val)} -> {repr(new_val)}")
else:
    print("Changed no existing encodings.")

print()

# If the table has changed, prompts for update:
if added or removed or changed:
    answer = input("Would you like to update the multibase table? (y/n) ")
    if answer.lower().startswith("y"):
        with open("multiformats/multibase/multibase-table.csv", "w") as f:
            f.write(new_text)
else:
    print("Nothing to update, exiting.")
