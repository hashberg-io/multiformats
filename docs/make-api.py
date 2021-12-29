"""
    A script to generate .rst files for API documentation.
"""

import glob
import importlib
import inspect
import json
import os
import pkgutil
from typing import Dict, List, Optional, Tuple
import sys

from typing_validation import validate

def _list_package_contents(pkg_name: str) -> List[str]:
    modules = [pkg_name]
    for submod in pkgutil.iter_modules([pkg_name.replace(".", "/")]):
        submod_fullname = pkg_name+"."+submod.name
        if submod.ispkg:
            for subsubmod_name in _list_package_contents(submod_fullname):
                modules.append(subsubmod_name)
        else:
            modules.append(submod_fullname)
    return modules

def make_apidocs() -> None:
    """
        A script to generate .rst files for API documentation.
    """
    err_msg = """Expected a 'make-api.json' file, with the following structure:
{
    "pkg_name": str,
    "apidocs_folder": str,
    "pkg_path": str,
    "toc_filename": Optional[str],
    "include_members": Dict[str, List[str]],
    "exclude_members": Dict[str, List[str]],
    "exclude_modules": List[str]
}

Set "toc_filename" to null to avoid generating a table of contents file.

"""
    try:
        with open("make-api.json", "r") as f:
            config = json.load(f)
            pkg_name = config.get("pkg_name", None)
            validate(pkg_name, str)
            pkg_path = config.get("pkg_path", None)
            validate(pkg_path, str)
            apidocs_folder = config.get("apidocs_folder", None)
            validate(apidocs_folder, str)
            toc_filename = config.get("toc_filename", None)
            validate(toc_filename, Optional[str])
            include_members = config.get("include_members", None)
            validate(include_members, Dict[str, List[str]])
            exclude_members = config.get("exclude_members", None)
            validate(exclude_members, Dict[str, List[str]])
            include_modules = config.get("include_modules", None)
            validate(include_modules, List[str])
            exclude_modules = config.get("exclude_modules", None)
            validate(exclude_modules, List[str])
    except FileNotFoundError:
        print(err_msg)
        sys.exit(1)
    except TypeError:
        print(err_msg)
        sys.exit(1)

    cwd = os.getcwd()
    os.chdir(pkg_path)
    sys.path = [os.getcwd()]+sys.path
    modules = _list_package_contents(pkg_name)
    modules_dict = {
        mod_name: importlib.import_module(mod_name)
        for mod_name in modules
    }
    for mod_name in include_modules:
        if mod_name not in modules_dict:
            modules_dict[mod_name] = importlib.import_module(mod_name)
    os.chdir(cwd)

    print(f"Removing all docfiles from {apidocs_folder}/")
    for apidoc_file in glob.glob(f"{apidocs_folder}/*.rst"):
        print(f"    {apidoc_file}")
        os.remove(apidoc_file)
    print()

    for mod_name, mod in modules_dict.items():
        if mod_name in exclude_modules:
            continue
        filename = f"{apidocs_folder}/{mod_name}.rst"
        print(f"Writing API docfile {filename}")
        lines: List[str] = [
            mod_name,
            "="*len(mod_name),
            "",
            f".. automodule:: {mod_name}",
            ""
        ]
        mod__all__ = getattr(mod, "__all__", [])
        reexported_members: List[Tuple[str, str]] = []
        for member_name in sorted(name for name in dir(mod) if not name.startswith("_")):
            if mod_name in exclude_members and member_name in exclude_members[mod_name]:
                continue
            member = getattr(mod, member_name)
            member_module = inspect.getmodule(member)
            member_module_name = member_module.__name__ if member_module is not None else None
            imported_member = member_module is not None and member_module != mod
            if mod_name in include_members and member_name in include_members[mod_name]:
                imported_member = False
            if imported_member:
                if inspect.ismodule(member):
                    member_fullname = member_module_name or ""
                else:
                    member_fullname = f"{member_module_name}.{member_name}"
            else:
                member_fullname = f"{mod_name}.{member_name}"
            member_kind = "data"
            if inspect.isclass(member):
                member_kind = "class"
            elif inspect.isfunction(member):
                member_kind = "function"
            elif inspect.ismodule(member):
                member_kind = "module"
            if not imported_member:
                member_lines: List[str] = []
                member_lines = [
                    member_name,
                    "-"*len(member_name),
                    "",
                    f".. auto{member_kind}:: {member_fullname}",
                ]
                if member_kind == "class":
                    member_lines.append("    :members:")
                member_lines.append("")
                print(f"    {member_kind} {member_name}")
                lines.extend(member_lines)
            elif member_name in mod__all__:
                reexported_members.append((member_fullname, member_kind))
        if reexported_members:
            reexported_members_header = f"{mod_name}.__all__"
            print(f"    {reexported_members_header}:")
            lines.extend([
                reexported_members_header,
                "-"*len(reexported_members_header),
                "",
                "The following members were explicitly reexported using ``__all__``:",
                "",
            ])
            refkinds = {
                "data": "obj",
                "function": "func",
                "class": "class",
                "module": "mod"
            }
            for member_fullname, member_kind in reexported_members:
                refkind = f":py:{refkinds[member_kind]}:"
                lines.append(f"    - {refkind}`{member_fullname}`")
                print(f"        {member_kind} {member_fullname}")
            lines.append("")
        with open(filename, "w") as f:
            f.write("\n".join(lines))
        print("")

    toctable_lines = [
        ".. toctree::",
        "    :maxdepth: 2",
        "    :caption: API Documentation",
        ""
    ]
    print(f"Writing TOC for API docfiles at {toc_filename}")
    for mod_name in modules_dict:
        line = f"    {apidocs_folder}/{mod_name}"
        toctable_lines.append(line)
        print(line)
    toctable_lines.append("")
    print()

    with open(toc_filename, "w") as f:
        f.write("\n".join(toctable_lines))

if __name__ == "__main__":
    make_apidocs()
