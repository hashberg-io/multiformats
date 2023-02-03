"""
    Reports the current implementation status for multiformats.
"""
# pylint: disable = wrong-import-position, wrong-import-order, unused-import

if __name__ != "__main__":
    raise RuntimeError("usage: report.py [-h] [-d]")

# == Script imports ==

import argparse
import gc
import sys
from typing import Any, Callable, Collection, Dict, List, Optional, Tuple, Union

# `rich` is not a dependency for the `multiformats` library
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# `setuptools_scm` is a development dependency for the `multiformats` library
from setuptools_scm import get_version # type: ignore

# `psutil` is not a dependency for the `multiformats` library
import psutil # type: ignore

# `pympler` is not a dependency for the `multiformats` library
from pympler import tracker # type: ignore

def bytesize_str(nbytes: int) -> str:
    """
        Pretty string representation of bytesizes.
    """
    sign = ""
    if nbytes < 0:
        nbytes *= -1
        sign = "-"
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]
    suffix_idx = 0
    while nbytes >= 1024 and suffix_idx <= 2:
        nbytes //= 1024
        suffix_idx += 1
    return f"{sign}{nbytes}{suffixes[suffix_idx]}"

def print_diff(diff: list[tuple[str, int, int]], console: Console) -> None:
    """
        Prints a tracker diff object to console
    """
    table = Table()
    table.add_column("Type", style="bold green")
    table.add_column("Count")
    table.add_column("Size")
    for t, c, s in sorted(diff, key=lambda entry: -entry[2]):
        table.add_row(t, str(c), bytesize_str(s))
    console.print(table)

# == Extract commandline args ==

description = "Implementation report for multiformats."
parser = argparse.ArgumentParser(description=description)
parser.add_argument("-m", help='loads a minimal set of multicodecs and multibases', action="store_true")
parser.add_argument("-d", help='print codes as decimal rather than hex', action="store_true")
parser.add_argument("-r", help='saves report to file', action="store_true")
args = parser.parse_args()
minimal_load = args.m
hex_codes = not args.d
save_report = args.r
code2str: Callable[[int], str] = hex if hex_codes else str # type: ignore

# == Intro panel with version ==

version = get_version(root='.', version_scheme="post-release")

console = Console(record=True, width=110)
console.print(Panel(f"Multiformats implementation report [bold blue]v{version}[white]"))

# == Memory profiling ==

pympler_count = {}
pympler_mem_usage = {}
psutil_mem_usage = {}

gc.collect()
baseline = psutil.Process().memory_full_info().uss / (1024 * 1024)
pympler_prev = baseline
psutil_prev = baseline


tr = tracker.SummaryTracker()
tr.diff()
import typing_extensions
gc.collect()
tracker_diff = tr.diff()
pympler_count["typing-extensions"] = sum(entry[1] for entry in tracker_diff)
pypler_diff = sum(entry[2] for entry in tracker_diff)
pympler_mem_usage["typing-extensions"] = pypler_diff / (1024 * 1024)
pympler_prev += pypler_diff
psutil_diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-psutil_prev
psutil_mem_usage["typing-extensions"] = psutil_diff
psutil_prev += psutil_diff

tr = tracker.SummaryTracker()
tr.diff()
import typing_validation
gc.collect()
tracker_diff = tr.diff()
pympler_count["typing-validation"] = sum(entry[1] for entry in tracker_diff)
pypler_diff = sum(entry[2] for entry in tracker_diff)
pympler_mem_usage["typing-validation"] = pypler_diff / (1024 * 1024)
pympler_prev += pypler_diff
psutil_diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-psutil_prev
psutil_mem_usage["typing-validation"] = psutil_diff
psutil_prev += psutil_diff

tr = tracker.SummaryTracker()
tr.diff()
import bases
gc.collect()
tracker_diff = tr.diff()
pympler_count["bases"] = sum(entry[1] for entry in tracker_diff)
pypler_diff = sum(entry[2] for entry in tracker_diff)
pympler_mem_usage["bases"] = pypler_diff / (1024 * 1024)
pympler_prev += pypler_diff
psutil_diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-psutil_prev
psutil_mem_usage["bases"] = psutil_diff
psutil_prev += psutil_diff

tr = tracker.SummaryTracker()
tr.diff()
if minimal_load:
    import multiformats_config
    multiformats_config.enable(codecs=[], bases=[])
import multiformats
from multiformats import *
gc.collect()
tracker_diff = tr.diff()
pympler_count["multiformats"] = sum(entry[1] for entry in tracker_diff)
pypler_diff = sum(entry[2] for entry in tracker_diff)
pympler_mem_usage["multiformats"] = pypler_diff / (1024 * 1024)
pympler_prev += pypler_diff
psutil_diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-psutil_prev
psutil_mem_usage["multiformats"] = psutil_diff
psutil_prev += psutil_diff

pympler_mem_usage_total = sum(pympler_mem_usage.values())
pympler_mem_usage_pct = {k: v/pympler_mem_usage_total for k, v in pympler_mem_usage.items()}
psutil_mem_usage_total = sum(psutil_mem_usage.values())
psutil_mem_usage_pct = {k: v/psutil_mem_usage_total for k, v in psutil_mem_usage.items()}

# == Memory usage table ==

console.rule("Memory Usage (pympler)")

table = Table()
table.add_column("Component", style="white")
table.add_column("Obj. count", style="white", justify="right")
table.add_column("Memory", style="bold blue", justify="right")
table.add_column("Memory %", style="bold blue", justify="right")
for k, v in pympler_mem_usage.items():
    pct = f"{pympler_mem_usage_pct[k]:.0%}" if k in pympler_mem_usage_pct else ""
    if v >= 1000/1024:
        table.add_row(k, str(pympler_count[k]), f"{v:.1f}MiB", pct)
    else:
        table.add_row(k, str(pympler_count[k]), f"{1024*v:.0f}KiB", pct)
console.print(f"> memory baseline: [bold blue]{baseline:.1f}MiB[white]")
console.print(f"> multiformats memory total:     [bold blue]{pympler_mem_usage_total:.1f}MiB[white]")
console.print(table)


console.rule("Memory Usage (psutil)")

table = Table()
table.add_column("Component", style="white")
table.add_column("Memory", style="bold blue", justify="right")
table.add_column("Memory %", style="bold blue", justify="right")
for k, v in psutil_mem_usage.items():
    pct = f"{psutil_mem_usage_pct[k]:.0%}" if k in psutil_mem_usage_pct else ""
    if v >= 1000/1024:
        table.add_row(k, f"{v:.1f}MiB", pct)
    else:
        table.add_row(k, f"{1024*v:.0f}KiB", pct)
console.print(f"> memory baseline: [bold blue]{baseline:.1f}MiB[white]")
console.print(f"> multiformats memory total:     [bold blue]{psutil_mem_usage_total:.1f}MiB[white]")
console.print(table)


# == Group multihash multicodecs together ==
# TODO: consider introduce grouped multicodecs doing this directly, to reduce mem footprint (currently footprint is negligible)

_multihash_indices: Dict[str, int] = {}
_grouped_multicodecs: List[Tuple[str, str, Optional[List[int]], List[int], List[bool], typing_extensions.Literal["draft", "permanent"]]] = []
for codec in multicodec.table(tag="multihash"):
    is_implemented = multihash.is_implemented(codec.name)
    tokens = codec.name.split("-")
    if len(tokens) == 1:
        label = codec.name
    else:
        label = "-".join(tokens[:-1])
    max_digest_size: Optional[int] = None
    try:
        max_digest_size = multihash.raw.get(codec.name)[1]
    except KeyError:
        pass
    if max_digest_size is None:
        try:
            max_digest_size = int(tokens[-1])//8
        except ValueError:
            pass
    if max_digest_size is None:
        _grouped_multicodecs.append((codec.name, codec.tag, None, [codec.code], [is_implemented], codec.status))
        continue
    bitsize = max_digest_size*8
    if label not in _multihash_indices:
        _multihash_indices[label] = len(_grouped_multicodecs)
        _grouped_multicodecs.append((codec.name, codec.tag, [bitsize], [codec.code], [is_implemented], codec.status))
    else:
        bitsize_list = _grouped_multicodecs[_multihash_indices[label]][2]
        if bitsize_list is None:
            _grouped_multicodecs.append((codec.name, codec.tag, None, [codec.code], [is_implemented], codec.status))
            continue
        code_list = _grouped_multicodecs[_multihash_indices[label]][3]
        impl_list = _grouped_multicodecs[_multihash_indices[label]][4]
        bitsize_list.append(bitsize)
        code_list.append(codec.code)
        impl_list.append(is_implemented)


# == Multihash table ==

def set_str(l: Collection[int], *, use_hex: bool = False, minlen: int = 4, maxlen: int = 8) -> str:
    """ Compact representation of a sorted set of numbers. """
    assert minlen >= 3
    assert maxlen >= minlen
    tostr: Callable[[int], str] = hex if use_hex else str # type: ignore
    l = sorted(set(l))
    start = l[0]
    end = l[-1]
    step = l[1]-l[0]
    if len(l) <= minlen:
        return f"{{{', '.join(tostr(i) for i in l)}}}"
    if l == list(range(start, end+1, step)):
        fst = tostr(start)
        snd = tostr(start+step)
        lst = tostr(end)
        return f"{{{fst}, {snd}, ..., {lst}}}"
    if len(l) <= maxlen:
        return f"{{{', '.join(tostr(i) for i in l)}}}"
    return f"{{{tostr(l[0])},...(irregular)}}"


console.rule("Multihash functions")

table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Bitsize", style="bright_black")
table.add_column("Implem.")
table.add_column("Status")
num_implemented = 0
num_total = 0
for name, tag, bitsize_list, code_list, impl_list, status in _grouped_multicodecs:
    num_total += len(impl_list)
    impl_status = "[red]no"
    if all(impl_list):
        impl_status = "[green]yes"
        num_implemented += len(impl_list)
    elif any(impl_list):
        num_impl = sum(1 if b else 0 for b in impl_list)
        impl_status = f"[yellow]{num_impl}/{len(impl_list)}"
        num_implemented += num_impl
    codec_status = "[yellow]draft" if status == "draft" else "[green]perm."
    if bitsize_list is None:
        table.add_row(code2str(code_list[0]), name, "", impl_status, codec_status)
        continue
    if len(bitsize_list) <= 1:
        table.add_row(code2str(code_list[0]), f"{name}", str(bitsize_list[0]), impl_status, codec_status)
    else:
        label = "-".join(name.split("-")[:-1])
        table.add_row(set_str(code_list, use_hex=hex_codes),
                      f"{label}-[bright_black]Bitsize",
                      set_str(bitsize_list),
                      impl_status,
                      codec_status)
console.print(f"> Multihash functions implemented: [bold blue]{num_implemented}/{num_total}")
console.print(table)


# == Multiaddr table ==

console.rule("Multiaddr protocols")
table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Implem.")
table.add_column("Status")
num_implemented = 0
num_total = 0
for codec in multicodec.table(tag="multiaddr"):
    is_implemented = multiaddr.raw.exists(codec.name)
    num_implemented += 1 if is_implemented else 0
    num_total += 1
    impl_status = "[green]yes" if is_implemented else "[red]no"
    codec_status = "[yellow]draft" if codec.status == "draft" else "[green]perm."
    table.add_row(code2str(codec.code), codec.name, impl_status, codec_status)
console.print(f"> Multiaddr protocols implemented: [bold blue]{num_implemented}/{num_total}")
console.print(table)

# == Multibase table ==

console.rule("Multibases")
table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Implem.")
table.add_column("Status")

num_implemented = 0
num_total = 0
for base in multibase.table():
    is_implemented = multibase.raw.exists(base.name)
    num_implemented += 1 if is_implemented else 0
    num_total += 1
    impl_status = "[green]yes" if is_implemented else "[red]no"
    codec_status = "[yellow]draft" if base.status == "draft" else "[green]perm."
    table.add_row(base.code_printable, base.name, impl_status, codec_status)
console.print(f"> Multibases implemented: [bold blue]{num_implemented}/{num_total}")
console.print(table)

# == Other multicodecs table ==

console.rule("Other Multicodecs")
table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Tag", style="magenta")
table.add_column("Status")
for codec in multicodec.table():
    if codec.tag not in ("multihash", "multiaddr"):
        codec_status = "[yellow]draft" if codec.status == "draft" else "[green]perm."
        table.add_row(code2str(codec.code), codec.name, codec.tag, codec_status)
console.print(table)


# == Exporting report ==

if save_report:
    console.save_text("report.txt")
