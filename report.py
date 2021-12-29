"""
    Reports the current implementation status for multiformats.
"""
# pylint: disable = wrong-import-position, wrong-import-order, unused-import

if __name__ != "__main__":
    raise RuntimeError("usage: report.py [-h] [-d]")


# == Memory profiling ==

# `psutil` is not a dependency for the `multiformats` library
import psutil # type: ignore

mem_usage = {}

baseline = psutil.Process().memory_full_info().uss / (1024 * 1024)
prev = baseline

import typing_validation

diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-prev
mem_usage["typing-validation"] = diff
prev += diff

import bases

diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-prev
mem_usage["bases"] = diff
prev += diff

import skein # type: ignore

diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-prev
mem_usage["pyskein"] = diff
prev += diff

import multiformats
from multiformats import *

diff = psutil.Process().memory_full_info().uss / (1024 * 1024)-prev
mem_usage["multiformats"] = diff

mem_usage_total = sum(mem_usage.values())
mem_usage_pct = {k: v/mem_usage_total for k, v in mem_usage.items()}


# == Script imports ==

import argparse
from typing import Any, Callable, Collection, Dict, List, Optional, Tuple, Union

# `rich` is not a dependency for the `multiformats` library
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# `setuptools_scm` is a development dependency for the `multiformats` library
from setuptools_scm import get_version # type: ignore

# == Extract commandline args ==

description = "Implementation report for multiformats."
parser = argparse.ArgumentParser(description=description)
parser.add_argument("-d", help='print codes as decimal rather than hex', action="store_true")
args = parser.parse_args()
hex_codes = not args.d
code2str: Callable[[int], str] = hex if hex_codes else str # type: ignore

# == Intro panel with version ==

version = get_version(root='.', version_scheme="post-release")

console = Console(record=True, width=104)
console.print(Panel(f"Multiformats implementation report [bold blue]v{version}[white]"))


# == Memory usage table ==

console.rule("Memory Usage")

table = Table()
table.add_column("Component", style="white")
table.add_column("Memory", style="bold blue", justify="right")
table.add_column("Memory %", style="bold blue", justify="right")
for k, v in mem_usage.items():
    pct = f"{mem_usage_pct[k]:.0%}" if k in mem_usage_pct else ""
    if v >= 1000/1024:
        table.add_row(k, f"{v:.1f}MiB", pct)
    else:
        table.add_row(k, f"{1024*v:.0f}KiB", pct)
console.print(f"> python+psutil memory baseline: [bold blue]{baseline:.1f}MiB[white]")
console.print(f"> multiformats memory total:     [bold blue]{mem_usage_total:.1f}MiB[white]")
console.print(table)


# == Group multihash multicodecs together ==
# TODO: introduce grouped multicodecs doing this directly, to reduce mem footprint

_multihash_indices: Dict[str, int] = {}
_grouped_multicodecs: List[Tuple[str, str, Optional[List[int]], List[int], List[bool]]] = []
for codec in multicodec.table(tag="multihash"):
    is_implemented = multihash.is_implemented(codec.name)
    tokens = codec.name.split("-")
    label = "-".join(tokens[:-1])
    max_digest_size: Optional[int] = None
    try:
        max_digest_size = multihash.raw.get(codec.name)[1]
    except KeyError:
        pass
    if max_digest_size is None:
        try:
            max_digest_size = int(tokens[-1])
        except ValueError:
            pass
    if max_digest_size is None:
        _grouped_multicodecs.append((codec.name, codec.tag, None, [codec.code], [is_implemented]))
        continue
    bitsize = max_digest_size*8
    if label not in _multihash_indices:
        _multihash_indices[label] = len(_grouped_multicodecs)
        _grouped_multicodecs.append((codec.name, codec.tag, [bitsize], [codec.code], [is_implemented]))
    else:
        bitsize_list = _grouped_multicodecs[_multihash_indices[label]][2]
        if bitsize_list is None:
            _grouped_multicodecs.append((codec.name, codec.tag, None, [codec.code], [is_implemented]))
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
num_implemented = 0
num_total = 0
for name, tag, bitsize_list, code_list, impl_list in _grouped_multicodecs:
    num_total += len(impl_list)
    impl_status = "[red]no"
    if all(impl_list):
        impl_status = "[green]yes"
        num_implemented += len(impl_list)
    elif any(impl_list):
        num_impl = sum(1 if b else 0 for b in impl_list)
        impl_status = f"[yellow]{num_impl}/{len(impl_list)}"
        num_implemented += num_impl
    if bitsize_list is None:
        table.add_row(code2str(code_list[0]), name, "", impl_status)
        continue
    if len(bitsize_list) <= 1:
        table.add_row(code2str(code_list[0]), f"{name}-{bitsize_list[0]}", str(bitsize_list[0]), impl_status)
    else:
        label = "-".join(name.split("-")[:-1])
        table.add_row(set_str(code_list, use_hex=hex_codes),
                      f"{label}-[bright_black]Bitsize",
                      set_str(bitsize_list),
                      impl_status)
console.print(f"> Multihash functions implemented: [bold blue]{num_implemented}/{num_total}")
console.print(table)


# == Multiaddr table ==

console.rule("Multiaddr protocols")
table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Implem.")
num_implemented = 0
num_total = 0
for codec in multicodec.table(tag="multiaddr"):
    is_implemented = multiaddr.raw.exists(codec.name)
    num_implemented += 1 if is_implemented else 0
    num_total += 1
    impl_status = "[green]yes" if is_implemented else "[red]no"
    table.add_row(code2str(codec.code), codec.name, impl_status)
console.print(f"> Multiaddr protocols implemented: [bold blue]{num_implemented}/{num_total}")
console.print(table)


# == Other multicodecs table ==

console.rule("Other Multicodecs")
table = Table()
table.add_column("Code", style="bold blue")
table.add_column("Name")
table.add_column("Tag", style="magenta")
for codec in multicodec.table():
    if codec.tag not in ("multihash", "multiaddr"):
        table.add_row(code2str(codec.code), codec.name, codec.tag)
console.print(table)


# == Exporting report ==

console.save_text("report.txt")
