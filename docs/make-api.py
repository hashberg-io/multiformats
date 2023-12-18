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

SPECIAL_CLASS_MEMBERS_REL = ("__eq__", "__gt__", "__ge__", "__lt__", "__le__", "__ne__", )
SPECIAL_CLASS_MEMBERS_UNOP = ("__abs__", "__not__", "__inv__", "__invert__", "__neg__", "__pos__", )
SPECIAL_CLASS_MEMBERS_BINOP = ("__add__", "__and__", "__concat__", "__floordiv__", "__lshift__", "__mod__", "__mul__",
                               "__matmul__", "__or__", "__pow__", "__rshift__", "__sub__", "__truediv__", "__xor__", )
SPECIAL_CLASS_MEMBERS_BINOP_I = tuple(f"__i{name[2:]}" for name in SPECIAL_CLASS_MEMBERS_BINOP)
SPECIAL_CLASS_MEMBERS_BINOP_R = tuple(f"__r{name[2:]}" for name in SPECIAL_CLASS_MEMBERS_BINOP)
SPECIAL_CLASS_MEMBERS_CAST = ("__bool__", "__int__", "__float__", "__complex__", "__bytes__", "__str__")
SPECIAL_CLASS_MEMBERS_OTHER = ("__init__", "__new__", "__call__", "__repr__", "__index__", "__contains__",
                               "__delitem__", "__getitem__", "__setitem__", "__getattr__", "__setattr__", "__delattr__", "__set_name__", "__set__", "__get__")
SPECIAL_CLASS_MEMBERS = (SPECIAL_CLASS_MEMBERS_REL+SPECIAL_CLASS_MEMBERS_UNOP+SPECIAL_CLASS_MEMBERS_BINOP+SPECIAL_CLASS_MEMBERS_BINOP_I
                         +SPECIAL_CLASS_MEMBERS_BINOP_R+SPECIAL_CLASS_MEMBERS_CAST+SPECIAL_CLASS_MEMBERS_OTHER)

def make_apidocs() -> None:
    """
        A script to generate .rst files for API documentation.
    """
    err_msg = """Expected a 'make-api.json' file, with the following structure:
{
    "pkg_name": str,
    "apidocs_folder": str,
    "pkg_path": str,
    "toc_filename": str,
    "type_alias_dict_filename": Optional[str],
    "include_members": Dict[str, List[str]],
    "type_aliases": Dict[str, List[str]],
    "exclude_members": Dict[str, List[str]],
    "exclude_modules": List[str],
    "member_fullnames": Dict[str, Dict[str, str]],
    "special_class_members": Dict[str, List[str]],
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
            validate(toc_filename, str)
            type_alias_dict_filename = config.get("type_alias_dict_filename", None)
            validate(type_alias_dict_filename, Optional[str])
            include_members = config.get("include_members", {})
            validate(include_members, Dict[str, List[str]])
            type_aliases = config.get("type_aliases", {})
            validate(type_aliases, Dict[str, List[str]])
            exclude_members = config.get("exclude_members", {})
            validate(exclude_members, Dict[str, List[str]])
            include_modules = config.get("include_modules", [])
            validate(include_modules, List[str])
            exclude_modules = config.get("exclude_modules", [])
            validate(exclude_modules, List[str])
            member_fullnames = config.get("member_fullnames", {})
            validate(member_fullnames, Dict[str, Dict[str, str]])
            special_class_members = config.get("special_class_members", {})
            validate(special_class_members, Dict[str, List[str]])
    except FileNotFoundError:
        print(err_msg)
        sys.exit(1)
    except TypeError:
        print(err_msg)
        sys.exit(1)
    for mod_name, type_alias_members in type_aliases.items():
        if mod_name not in include_members:
            include_members[mod_name] = []
        include_members[mod_name].extend(type_alias_members)

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

    type_alias_fullnames: dict[str, str] = {}

    print("Pre-processing type aliases:")
    for mod_name, mod_type_aliases in type_aliases.items():
        if mod_name in exclude_modules:
            continue
        for member_name in mod_type_aliases:
            member_fullname = f"{mod_name}.{member_name}"
            if member_name in type_alias_fullnames:
                print(f"    WARNING! Skipping type alias {member_name} -> {member_fullname}")
                print(f"             Existing type alias {member_name} -> {type_alias_fullnames[member_name]}")
            else:
                type_alias_fullnames[member_name] = member_fullname
                print(f"    {member_name} -> {member_fullname}")
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
        for member_name in sorted(name for name in dir(mod)):
            to_include = mod_name in include_members and member_name in include_members[mod_name]
            to_exclude = mod_name in exclude_members and member_name in exclude_members[mod_name]
            if to_exclude:
                continue
            member = getattr(mod, member_name)
            if member_name.startswith("_") and not to_include:
                continue
            member = getattr(mod, member_name)
            member_module = inspect.getmodule(member)
            member_module_name = member_module.__name__ if member_module is not None else None
            imported_member = member_module is not None and member_module != mod
            if mod_name in include_members and member_name in include_members[mod_name]:
                imported_member = False
            if member_name in type_alias_fullnames:
                member_fullname = type_alias_fullnames[member_name]
            elif mod_name in member_fullnames and member_name in member_fullnames[mod_name]:
                member_fullname = member_fullnames[mod_name][member_name]
            elif imported_member:
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
                    member_lines.append("    :show-inheritance:")
                    member_lines.append("    :members:")
                    _special_class_submembers: list[str] = []
                    if member_fullname in special_class_members and special_class_members[member_fullname]:
                        _special_class_submembers.extend(special_class_members[member_fullname])
                    for submember_name in SPECIAL_CLASS_MEMBERS:
                        if not hasattr(member, submember_name):
                            continue
                        submember = getattr(member, submember_name)
                        if not hasattr(submember, "__doc__") or submember.__doc__ is None:
                            continue
                        if not ":meta public:" in submember.__doc__:
                            continue
                        if submember_name not in _special_class_submembers:
                            _special_class_submembers.append(submember_name)
                    if _special_class_submembers:
                        member_lines.append(f"    :special-members: {', '.join(_special_class_submembers)}")
                member_lines.append("")
                if member_name in type_alias_fullnames:
                    print(f"    {member_kind} {member_name} -> {type_alias_fullnames[member_name]} (type alias)")
                else:
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
        if mod_name in exclude_modules:
            continue
        line = f"    {apidocs_folder}/{mod_name}"
        toctable_lines.append(line)
        print(line)
    toctable_lines.append("")
    print()

    with open(toc_filename, "w") as f:
        f.write("\n".join(toctable_lines))

    if type_alias_dict_filename is not None:
        print(f"Writing type alias dictionary: {type_alias_dict_filename}")
        for name, fullname in type_alias_fullnames.items():
            print(f"    {name} -> {fullname}")
        print()
        with open(type_alias_dict_filename, "w") as f:
            json.dump(type_alias_fullnames, f, indent=4)

if __name__ == "__main__":
    make_apidocs()
