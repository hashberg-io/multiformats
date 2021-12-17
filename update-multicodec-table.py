"""
   Pulls the current multicodec table from the [multicodec spec](https://github.com/multiformats/multicodec)
"""

import csv
import io
import json
import pprint
import textwrap

# not a dependency for the `multiformats` library
import requests

from multiformats import multicodec

# Fetches and validates the new multicodec table from the multicodec spec GitHub repo:
multicodec_table_url = "https://github.com/multiformats/multicodec/raw/master/table.csv"
print("Fetching multicodec table from:")
print(multicodec_table_url)
print()

new_bytes = requests.get(multicodec_table_url).content
new_text = new_bytes.decode("utf-8")
print("Building new multicodec table...")
reader = csv.DictReader(io.StringIO(new_text))
multicodecs = (multicodec.Multicodec(**{k.strip(): v.strip() for k, v in _row.items()})
               for _row in reader)
new_table, _ = multicodec.build_multicodec_tables(multicodecs)

# Loads and validates the current multicodec table:
print("Building current multicodec table...")
with open("multiformats/multicodec/multicodec-table.csv", "r") as f:
    current_text = f.read()
reader = csv.DictReader(io.StringIO(current_text))
multicodecs = (multicodec.Multicodec(**{k.strip(): v.strip() for k, v in _row.items()})
               for _row in reader)
current_table, _ = multicodec.build_multicodec_tables(multicodecs)

print()

# Displays added multicodecs, if any:
added = {
    code: m
    for code, m in new_table.items()
    if code not in current_table
}
if added:
    print(f"Added {len(added)} new multicodecs:")
    for m in sorted(added.values(), key=lambda m: m.code):
        print(textwrap.indent(pprint.pformat(m.to_json()), "  "))
else:
    print("Added no new multicodecs.")

# Displays removed multicodecs, if any:
removed = {
    code: m
    for code, m in current_table.items()
    if code not in new_table
}
if removed:
    print(f"Removed {len(added)} existing multicodecs:")
    for m in sorted(removed.values(), key=lambda m: m.code):
        print(textwrap.indent(pprint.pformat(m.to_json()), "  "))
else:
    print("Removed no existing multicodecs.")

# Displays changed multicodecs, if any:
changed = {
    code: (m, new_table[code])
    for code, m in current_table.items()
    if code in new_table and new_table[code] != m
}
if changed:
    print(f"Changed {len(added)} existing multicodecs:")
    for m_old, m_new in sorted(changed.values(), key=lambda pair: pair[0].code):
        print(f"  Changes in protocol {m_old.hexcode}:")
        for attr in ("name", "tag", "status", "description"):
            old_val, new_val = (getattr(m_old, attr), getattr(m_new, attr))
            if old_val != new_val:
                print(f"    {attr}: {repr(old_val)} -> {repr(new_val)}")
else:
    print("Changed no existing multicodecs.")

print()

# If the table has changed, prompts for update:
if added or removed or changed:
    answer = input("Would you like to update the multicodec table? (y/n) ")
    if answer.lower().startswith("y"):
        with open("multiformats/multicodec/multicodec-table.csv", "w") as f:
            f.write(new_text)
        with open("multiformats/multicodec/multicodec-table.json", "w") as f:
            table = [new_table[code].to_json() for code in sorted(new_table.keys())]
            json.dump(table, f, indent=4)
else:
    print("Nothing to update, exiting.")
