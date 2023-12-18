r"""
    Autodoc extension dealing with local type references and function signatures.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import inspect
import re
from types import FunctionType, ModuleType
from typing import Any, Optional, Union
from typing_extensions import Literal
from sphinx.application import Sphinx

@dataclass(frozen=True)
class ParsedType:
    r""" Dataclass for a parsed type. """
    name: str
    args: Union[None, str, tuple[ParsedType, ...]] = None
    variadic: bool = False

    def crossref(self, globalns: Optional[Mapping[str, Any]] = None) -> str:
        r""" Generates Sphinx cross-reference link for the given type, using local names. """
        # pylint: disable = eval-used
        if globalns is None:
            globalns = {}
        name, args, variadic = self.name, self.args, self.variadic
        role = "obj"
        if name in globalns:
            obj = globalns[name]
            if isinstance(obj, ModuleType):
                role = "mod"
            elif isinstance(obj, property):
                role = "attr"
            elif isinstance(obj, type):
                role = "class"
            elif isinstance(obj, FunctionType):
                role = "func"
        name_crossref = f":{role}:`{name}`"
        if args is None:
            return name_crossref
        if isinstance(args, str):
            _args = eval(f"({args}, )")
            arg_crossrefs = ", ".join(f"``{repr(arg)}``" for arg in _args)
        else:
            arg_crossrefs = ", ".join((arg.crossref(globalns) for arg in args))
        if variadic:
            arg_crossrefs += ", ..."
        return fr"{name_crossref}\ [{arg_crossrefs}]"

def _find_closing_idx(s: str, c_open: str, c_close: str, idx_open: int = 0) -> int:
    r""" Finds the index where a bracketed/quoted range ends. """
    assert len(c_open) == 1, c_open
    assert len(c_close) == 1, c_close
    assert idx_open < len(s), (idx_open, len(s))
    assert s[idx_open] == c_open, (idx_open, s[idx_open])
    lvl = 1
    idx_close: Optional[int] = None
    for idx in range(idx_open+1, len(s)):
        if s[idx] == c_close:
            lvl -= 1
        elif s[idx] == c_open:
            lvl += 1
        if lvl == 0:
            idx_close = idx
            break
    if idx_close is None:
        error_msg = f"Unbalanced opening symbol found while searching for first outermost {c_open}...{c_close} in {repr(s)}."
        raise ValueError(error_msg)
    return idx_close

def _parse_type(annotation: str) -> tuple[Union[ParsedType, Literal["..."]], str]:
    r"""
        Parses an annotation into the first type appearing in it, together with the unparsed remainder of the annotation.
    """
    quote_close_idx = None
    if annotation.startswith("'"):
        quote_close_idx = _find_closing_idx(annotation, "'", "'", 0)
    elif annotation.startswith('"'):
        quote_close_idx = _find_closing_idx(annotation, '"', '"', 0)
    if quote_close_idx is not None:
        if quote_close_idx == 1:
            raise ValueError(f"Cannot parse empty forward reference at start of annotation: annotation = {annotation}")
        annotation = annotation[1:quote_close_idx]+annotation[quote_close_idx+1:]
    try:
        b_open: Optional[int] = annotation.index("[")
    except ValueError:
        b_open = None
    try:
        c_idx = annotation.index(",")
    except ValueError:
        c_idx = None
    if b_open is not None and (c_idx is None or b_open < c_idx):
        b_close = _find_closing_idx(annotation, "[", "]", b_open)
        name = annotation[:b_open]
        args_str = annotation[b_open+1:b_close]
        res = annotation[b_close+1:]
        assert name, (name, args_str, res)
        # FIXME: this doesn't work with Callable[[...], ...]
        if name.split(".")[-1] == "Literal":
            return ParsedType(name, args_str), res
        args: list[ParsedType] = []
        variadic = False
        while args_str:
            arg, _args_str = _parse_type(args_str)
            if isinstance(arg, ParsedType):
                args.append(arg)
            else:
                assert arg == "...", arg
                variadic = True
                if _args_str:
                    raise ValueError(f"Ellipsis argument encountered in parametric type, but not at the end of args lis: annotation = {annotation}, args_str = {args_str}")
            if not _args_str:
                break
            if not _args_str.startswith(", "):
                raise ValueError(f"Multiple type parameters must be separated by ', ': annotation = {annotation}, args_str = {args_str}, arg = {arg} _args_str = {_args_str}")
            args_str = _args_str[2:]
        return ParsedType(name, tuple(args), variadic), res
    if c_idx is not None:
        name = annotation[:c_idx]
        res = annotation[c_idx:]
        if name == "...":
            raise ValueError(f"Found ellipsis followed by comma: annotation = {annotation}")
        return ParsedType(name), res
    if "]" in annotation:
        raise ValueError(f"Encountered closing bracket ']' without any opening bracket: annotation = {annotation} ")
    name = annotation
    if name == "...":
        return "...", ""
    return ParsedType(name), ""

def parse_type(annotation: str) -> ParsedType:
    r""" Parses an annotation into a type. """
    # Handle top-level unions:
    # FIXME: this doesn't handle nested unions.
    if "|" in annotation:
        member_types = [
            parse_type(member_annotation.strip())
            for member_annotation in annotation.split("|")
        ]
        return ParsedType("typing.Union", tuple(member_types))
    parsed_type, residual_string = _parse_type(annotation)
    if residual_string:
        raise ValueError(f"Annotation was not entirely consumed by parsing: annotation = {annotation!r}, parsed_type = {parsed_type}, residual_string = {residual_string!r}")
    if not isinstance(parsed_type, ParsedType):
        raise ValueError(f"Cannot parse ellipsis on its own: annotation = {annotation}")
    return parsed_type

def sigdoc(fun: FunctionType, lines: list[str]) -> None:
    r"""
        Returns doclines documenting the parameter and return type of the given function
    """
    # pylint: disable = too-many-branches
    doc = "\n".join(lines)
    lines.append("")
    # FIXME: if an :rtype: line already exists, remove it here and re-append it after all param type lines.
    globalns = fun.__globals__
    sig = inspect.signature(fun)
    for p in sig.parameters.values():
        annotation = p.annotation
        if annotation == p.empty:
            continue
        if not isinstance(annotation, str):
            print(f"WARNING! Found non-string annotation: {repr(annotation)}. Did you forget to import annotation from __future__?.")
            annotation = str(annotation)
        t = parse_type(annotation)
        tx = t.crossref(globalns)
        default = p.default if p.default != p.empty else None
        is_args = p.kind == p.VAR_POSITIONAL
        is_kwargs = p.kind == p.VAR_KEYWORD
        if is_args:
            extra_info = "variadic positional"
        elif is_kwargs:
            extra_info = "variadic keyword"
        elif default is not None:
            default_str = default.__qualname__ if isinstance(default, FunctionType) else repr(default)
            extra_info = f"default = ``{default_str}``"
        else:
            extra_info = None
        if extra_info is None:
            line = f":type {p.name}: {tx}"
        else:
            line = f":type {p.name}: {tx}; {extra_info}"
        if f":param {p.name}:" not in doc:
            lines.append(f":param {p.name}:")
        if f":type {p.name}:" not in doc:
            lines.append(line)
    if sig.return_annotation == sig.empty:
        return
    t = parse_type(sig.return_annotation)
    tx = t.crossref(globalns)
    line = f":rtype: {tx}"
    if ":rtype:" not in doc:
        lines.append(line)

def sigdoc_handler(app: Sphinx, what: str, fullname: str, obj: Any, options: Any, lines: list[str]) -> None:
    r"""
        Handler for Sphinx Autodoc's event
        `autodoc-process-docstring<https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-docstring>`_
        which replaces cross-references specified in terms of module globals with their fully qualified version.
    """
    # pylint: disable = too-many-arguments
    if what not in ("function", "method", "property"):
        return
    if what == "property":
        fun: FunctionType = obj.fget
    else:
        fun = obj
    sigdoc(fun, lines)

def simple_crossref_pattern(name: str) -> re.Pattern[str]:
    r"""
        Pattern for simple imports:

        .. code-block :: python

            f":{role}:`{name}`"        # e.g. ":class:`MyClass`"
            f":{role}:`~{name}`"       # e.g. ":class:`~MyClass`"
            f":{role}:`{name}{tail}`"  # e.g. ":attr:`MyClass.my_property.my_subproperty`"
            f":{role}:`~{name}{tail}`" # e.g. ":attr:`~MyClass.my_property.my_subproperty`"

    """
    return re.compile(rf":([a-z]+):`(~)?{name}(\.[\.a-zA-Z0-9_]+)?`")

def simple_crossref_repl(name: str, fullname: str) -> Callable[[re.Match[str]], str]:
    r"""
        Replacement function for the pattern generated by :func:`simple_crossref_pattern`:

        .. code-block :: python

            f":{role}:`~{fullname}`"                    # e.g. ":class:`~mymod.mysubmod.MyClass`"
            f":{role}:`~{fullname}`"                    # e.g. ":class:`~mymod.mysubmod.MyClass`"
            f":{role}:`{name}{tail}<{fullname}{tail}>`" # e.g. ":attr:`MyClass.my_property.my_subproperty<mymod.mysubmod.MyClass.my_property.my_subproperty>`"
            f":{role}:`~{fullname}{tail}`"              # e.g. ":attr:`~mymod.mysubmod.MyClass.my_property.my_subproperty`"

    """
    def repl(match: re.Match[str]) -> str:
        role = match[1]
        short = match[2] is not None
        tail = match[3]
        if tail is None:
            return f":{role}:`~{fullname}`"
        if short:
            return f":{role}:`~{fullname}{tail}`"
        return f":{role}:`{name}{tail}<{fullname}{tail}>`"
    return repl

def labelled_crossref_pattern(name: str) -> re.Pattern[str]:
    r"""
        Pattern for labelled imports:

        .. code-block :: python

            f":{role}:`{label}<{name}>`"       # e.g. ":class:`my class<MyClass>`"
            f":{role}:`{label}<{name}{tail}>`" # e.g. ":attr:`my_property<MyClass.my_property>`"

    """
    return re.compile(rf":([a-z]+):`([\.a-zA-Z0-9_]+)<{name}(\.[\.a-zA-Z0-9_]+)?>`")

def labelled_crossref_repl(name: str, fullname: str) -> Callable[[re.Match[str]], str]:
    r"""
        Replacement function for the pattern generated by :func:`labelled_crossref_pattern`:

        .. code-block :: python

            f":{role}:`{label}<{fullname}>`"       # e.g. ":class:`my class<mymod.mysubmod.MyClass>`"
            f":{role}:`{label}<{fullname}{tail}>`" # e.g. ":attr:`my_property<mymod.mysubmod.MyClass.my_property>`"

    """
    def repl(match: re.Match[str]) -> str:
        role = match[1]
        label = match[2]
        tail = match[3]
        if tail is None:
            return f":{role}:`{label}<{fullname}>`"
        return f":{role}:`{label}<{fullname}{tail}>`"
    return repl

_crossref_subs: list[tuple[Callable[[str], re.Pattern[str]],
                           Callable[[str, str], Callable[[re.Match[str]], str]]]] = [
    (simple_crossref_pattern, simple_crossref_repl),
    (labelled_crossref_pattern, labelled_crossref_repl),
]
r"""
    Substitution patterns and replacement functions for various kinds of cross-reference scenarios.
"""

def _get_module_by_name(modname: str) -> ModuleType:
    r"""
        Gathers a module object by name.
    """
    # pylint: disable = exec-used, eval-used
    exec(f"import {modname.split('.')[0]}")
    mod: ModuleType = eval(modname)
    if not isinstance(mod, ModuleType):
        return None
    return mod

def _get_obj_mod(app: Sphinx, what: str, fullname: str, obj: Any) -> Optional[ModuleType]:
    r"""
        Gathers the containing module for the given ``obj``.
    """
    autodoc_type_aliases = app.config.__dict__.get("autodoc_type_aliases")
    name = fullname.split(".")[-1]
    obj_mod: Optional[ModuleType]
    if autodoc_type_aliases is not None:
        if name in autodoc_type_aliases and fullname == autodoc_type_aliases[name]:
            modname = ".".join(fullname.split(".")[:-1])
            obj_mod = _get_module_by_name(modname)
            return obj_mod
    if what == "module":
        obj_mod = obj
    elif what in ("function", "class", "method"):
        obj_mod = inspect.getmodule(obj)
    elif what == "property":
        obj_mod = inspect.getmodule(obj.fget)
    elif what == "data":
        modname = ".".join(fullname.split(".")[:-1])
        obj_mod = _get_module_by_name(modname)
    elif what == "attribute":
        modname = ".".join(fullname.split(".")[:-2])
        obj_mod = _get_module_by_name(modname)
    else:
        print(f"WARNING! Encountered unexpected value for what = {what} at fullname = {fullname}")
        obj_mod = None
    return obj_mod

def _build_fullname_dict(app: Sphinx, fullname: str, obj_mod: Optional[ModuleType], ) -> dict[str, str]:
    r"""
        Builds a dictionary of substitutions from module global names to their fully qualified names,
        based on :func:`inspect.getmodule` and `autodoc_type_aliases` (if specified in the Sphinx app config).
    """
    autodoc_type_aliases = app.config.__dict__.get("autodoc_type_aliases")
    fullname_dict: dict[str, str] = {}
    if obj_mod is not None:
        globalns = obj_mod.__dict__
        for g_name, g_obj in globalns.items():
            if isinstance(g_obj, (FunctionType, type)):
                g_mod = inspect.getmodule(g_obj)
            elif isinstance(g_obj, ModuleType):
                g_mod = g_obj
            else:
                g_mod = inspect.getmodule(g_obj)
            if g_mod is None or g_mod == obj_mod:
                continue
            if g_name not in g_mod.__dict__:
                continue
            g_modname = g_mod.__name__
            fullname_dict[g_name] = f"{g_modname}.{g_name}"
    if autodoc_type_aliases is not None:
        for a_name, a_fullname in autodoc_type_aliases.items():
            if a_name not in fullname_dict:
                fullname_dict[a_name] = a_fullname
    return fullname_dict

def local_crossref_handler(app: Sphinx, what: str, fullname: str, obj: Any, options: Any, lines: list[str]) -> None:
    r"""
        Handler for Sphinx Autodoc's event
        `autodoc-process-docstring<https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-docstring>`_
        which replaces cross-references specified in terms of module globals with their fully qualified version.
    """
    # pylint: disable = too-many-arguments, too-many-locals
    obj_mod = _get_obj_mod(app, what, fullname, obj)
    fullname_dict = _build_fullname_dict(app, fullname, obj_mod)
    for sub_name, sub_fullname in fullname_dict.items():
        for idx, line in enumerate(lines):
            for pattern_fun, repl_fun in _crossref_subs:
                pattern = pattern_fun(sub_name)
                repl = repl_fun(sub_name, sub_fullname)
                line = re.sub(pattern, repl, line)
            lines[idx] = line

def setup(app: Sphinx) -> None:
    r"""
        Registers handlers for Sphinx Autodoc's event
        `autodoc-process-docstring<https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-docstring>`_
    """
    app.connect("autodoc-process-docstring", sigdoc_handler)
    app.connect("autodoc-process-docstring", local_crossref_handler)
