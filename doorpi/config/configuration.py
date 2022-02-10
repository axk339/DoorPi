from __future__ import annotations

import collections.abc
import contextlib
import pathlib
import itertools
import logging
import enum
import os
import re
import dpath.util
from importlib import resources
from typing import (
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    TextIO,
    Tuple,
    Union,
)

import toml

from . import defs as _defs
from . import types

logger = logging.getLogger(__name__)

flagkeys = frozenset({"_default", "_type"})


class Configuration:
    """The main configuration object"""

    def __init__(self) -> None:
        self.__values: Dict[str, Any] = {}
        self.__defs: Dict[str, Any] = {}

    def load_builtin_definitions(self) -> None:
        """Load the built-in key definitions from the ``defs`` directory"""
        for fname in resources.contents(_defs):
            if fname.endswith(".toml") and resources.is_resource(_defs, fname):
                logger.debug("Loading defs from %s", fname)
                with resources.open_text(_defs, fname) as file:
                    self.attach_defs(toml.load(file))

    def load(self, path: Union[str, os.PathLike, TextIO]) -> None:
        """Replace configuration by loading from the given TOML file"""
        self.__values = {}
        subconf = list(toml.load(path).items())
        while subconf:
            key, val = subconf.pop()
            if isinstance(val, dict):
                subconf.extend(
                    (f"{key}.{subkey}", subval)
                    for subkey, subval in val.items()
                )
            else:
                self[key] = val

    def save(self, path: Union[str, os.PathLike, TextIO]) -> None:
        """Save the configuration into the given TOML file"""
        # Erroneous "Only @runtime_checkable protocols can be used with
        # instance and class checks"
        if isinstance(path, (str, os.PathLike)):  # type: ignore[misc]
            ctx: ContextManager[TextIO] = open(path, "w")
        else:
            ctx = contextlib.nullcontext(path)
        with ctx as file:
            toml.dump(self.__values, file, encoder=CustomTomlEncoder())

    def attach_defs(self, defs: Mapping[str, Any]) -> None:
        """Attach a dictionary of key definitions to this configuration"""

        def update_defs(
            keypath: Tuple[str, ...],
            target: Dict[str, Any],
            updates: Mapping[str, Any],
        ) -> None:
            if not isinstance(updates, dict):  # pragma: no cover
                raise TypeError(
                    "Expected key definition table, got {}".format(
                        type(updates).__name__
                    )
                )

            update_is_namespace = not set(updates) & flagkeys
            target_is_namespace = not set(target) & flagkeys
            if target and update_is_namespace ^ target_is_namespace:
                raise ValueError(  # pragma: no cover
                    "Cannot convert from {} to {}".format(
                        ("key", "namespace")[target_is_namespace],
                        ("key", "namespace")[update_is_namespace],
                    )
                )

            if not update_is_namespace:
                target.clear()
                target.update(
                    {k: v for k, v in updates.items() if k.startswith("_")}
                )
                self.__make_type(keypath, target)
                if "_default" in target:
                    target["_default"] = target["_type"].insertcast(
                        target["_default"]
                    )
            else:
                for key, val in updates.items():
                    if key.startswith("_"):
                        target[key[1:]] = val
                    else:
                        update_defs(
                            keypath + (key,), target.setdefault(key, {}), val
                        )

        update_defs((), self.__defs, defs.get("config", {}))

    def keydef(self, key: Union[str, Sequence[str]]) -> Tuple[Dict, List]:
        """Get the definition of key ``path``"""
        path = _splitkey(key)
        source, wildsegments = self._keydef(path)
        if not set(source) & flagkeys:
            raise KeyError(f"Key path too short: {key}")
        return source, wildsegments

    @property
    def keypaths(self):
        """ returns the combined keypaths (definitions and values) available """

        __combined = list(set(_keypaths(self.__defs) + _keypaths(self.__values)))
        __combined.sort()
        # separate wildcard entries (to sort em correctly)
        __wildcards = list(filter(lambda item: "*" in item, __combined))
        __combined = list(filter(lambda item: item not in __wildcards, __combined))

        for wc in __wildcards:
            __wc = wc.split(".")
            for pos, item in enumerate(__combined):
                __item = item.split(".")
                if __wc[0] != __item[0]:
                    continue
                if keymatch(wc, item):
                    __combined.insert(pos, wc)
                    break

        # readd unused
        for wc in __wildcards:
            if wc not in __combined:
                __combined.append(wc)

        return __combined

    def get_definition(self, keypath):
        if not dpath.util.search(self.__defs, keypath, separator="."):
            segment = {"_type": "", "_description": "", "_default": ""}
        else:
            keypath = _splitkey(keypath)
            segment = self.__defs
            for key in keypath:
                segment = segment[key]
        return segment

    def __getitem__(self, key: Union[str, Sequence[str]]) -> Any:
        keypath = _splitkey(key)
        keydef, _ = self.keydef(keypath)
        value = self.__values
        try:
            for segment in keypath:
                value = value[segment]
        except KeyError:
            try:
                value = keydef["_default"]
            except KeyError:
                raise KeyError(
                    f"No value set for required key {key}"
                ) from None
        return keydef["_type"].querycast(value)

    def __setitem__(self, key: Union[str, Sequence[str]], value: Any) -> None:
        keypath = _splitkey(key)
        keydef, _ = self.keydef(keypath)
        value = keydef["_type"].insertcast(value)
        namespace = self.__values
        for i in range(len(keypath) - 1):
            namespace = namespace.setdefault(keypath[i], {})
        namespace[keypath[-1]] = value

    def __delitem__(self, key: Union[str, Sequence[str]]) -> None:
        keypath = _splitkey(key)
        keydef, _ = self.keydef(keypath)
        if "_default" in keydef:
            namespace = self.__values
            try:
                for i in range(len(keypath) - 1):
                    namespace = namespace[keypath[i]]
                del namespace[keypath[-1]]
            except KeyError:
                pass
        else:
            raise KeyError(f"Cannot delete required key {key}")

    def view(self, key: Union[str, Sequence[str]]) -> ConfigView:
        """Return a view on the specified config section"""
        return ConfigView(self, tuple(_splitkey(key)))

    def iter(self, key: Union[str, Sequence[str]]) -> Iterator[str]:
        """Iterate over the value subkeys in ``key``"""
        keypath = _splitkey(key)
        keydef, _ = self._keydef(keypath)
        section = self.__values
        for segment in keypath:
            section = section.get(segment, {})
        if flagkeys & keydef.keys():
            raise KeyError(f"Cannot iterate over value key: {key}")
        return iter(section)

    def _keydef(self, path: Sequence[str]) -> Tuple[Dict, List]:
        source = self.__defs
        wildsegments = []
        for segment in path:
            if set(source) & flagkeys:
                raise KeyError(f"Key path too long: {path}")
            if not isinstance(source, dict):  # pragma: no cover
                raise KeyError(f"Bad key definition for {path}")

            try:
                source = source[segment]
            except KeyError:
                try:
                    source = source["*"]
                except KeyError:
                    raise KeyError(f"Undefined key: {path}") from None
                wildsegments.append(segment)
        return source, wildsegments

    @staticmethod
    def __make_type(
        keypath: Sequence[str],
        keydef: MutableMapping[str, Any],
    ) -> None:
        if "_type" in keydef:
            type_ = types.gettype(keydef["_type"])
        elif "_default" in keydef:
            type_ = types.infertype(keydef["_default"])
        else:  # pragma: no cover
            raise ValueError("Invalid keydef: Need `_type` or `_default`")
        keydef["_type"] = type_(keypath, keydef)


class ConfigView(collections.abc.Mapping):
    """A view into a subsection of the Configuration"""

    def __init__(self, source: Configuration, path: Tuple[str, ...]) -> None:
        assert isinstance(path, tuple)
        self.__source = source
        self.__path = path

    def __len__(self) -> int:
        return sum(1 for k in self)

    def __iter__(self) -> Iterator[str]:
        return self.__source.iter(self.__path)

    def __setitem__(self, key: Union[str, Sequence[str]], value: Any) -> None:
        self.__source[
            tuple(itertools.chain(self.__path, _splitkey(key)))
        ] = value

    def __getitem__(self, key: Union[str, Sequence[str]]) -> Any:
        return self.__source[
            tuple(itertools.chain(self.__path, _splitkey(key)))
        ]

    def view(self, subkey: Union[str, Sequence[str]]) -> ConfigView:
        """Return a subview onto the ``key`` within this section"""
        return type(self)(
            self.__source,
            tuple(itertools.chain(self.__path, _splitkey(subkey))),
        )


def _splitkey(key: Union[str, Sequence[str]]) -> List[str]:
    """ Takes in a keypath and returns a splitted list"""
    if isinstance(key, str):
        key = key.split(".")
    elif not isinstance(key, list):
        key = list(key)
    return key


def _keypaths(d):
    """ Takes in a config dict and returns the keypaths"""
    def iterdict(d, path):
        paths = []
        for k, v in d.items():
            if isinstance(v, dict):
                paths += iterdict(v, path + [k])
            else:
                #TODO get the test version!
                # to serve both self.__values and self.__defs
                if k not in ("_default", "_type", "_description", "_enumcls", "_min", "_max", "_membertype",):
                    path.append(k)
                _path = '.'.join(path)
                if _path not in paths:
                    paths.append(_path)
        return paths

    return iterdict(d, [])


def keymatch(pat, against):
    """ Matches a wildcard keypath against a defined one
    i.e. keyboard.*.input.* against keyboard.<some_name>.input.<some_pin> """

    regex = re.sub(re.compile(r'\*', re.I), r'\\w*', pat)
    return re.match(regex, against) is not None

class CustomTomlEncoder(toml.TomlEncoder):
    def __init__(self):
        super().__init__()
        self.dump_funcs.update({pathlib.PosixPath: lambda v: f'"{str(v)}"'})

    # monkeypatch
    def dump_value(self, v):
        dump_fn = self.dump_funcs.get(type(v))
        if dump_fn is None:
            if isinstance(v, enum.Enum):
                dump_fn = lambda v: f'"{v.name}"'
            elif hasattr(v, '__iter__'):
                dump_fn = self.dump_funcs[list]
        return dump_fn(v) if dump_fn is not None else self.dump_funcs[str](v)