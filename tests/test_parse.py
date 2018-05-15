import pickletools
from pickle import dumps
from pickletools import (
    anyobject,
    markobject,
    pybool,
    pyint,
    pylist,
    pynone,
    pytuple,
    pyunicode,
)

import attr
from pikara.analysis import _parse, _ParseEntry, _ParseResult

for opcode in pickletools.opcodes:
    globals()[opcode.name] = opcode

_MISSING = object()

if getattr(pickletools, "_RawOpcodeInfo", _MISSING) is _MISSING:
    pickletools._RawOpcodeInfo = pickletools.OpcodeInfo
    pickletools.OpcodeInfo = attr.s(
        these={
            "name": attr.ib(),
            "code": attr.ib(),
            "arg": attr.ib(),
            "stack_before": attr.ib(),
            "stack_after": attr.ib(),
            "proto": attr.ib(),
        },
        init=False,
    )(
        pickletools.OpcodeInfo
    )

if getattr(pickletools, "_RawArgumentDescriptor", _MISSING) is _MISSING:
    pickletools._RawArgumentDescriptor = pickletools.ArgumentDescriptor
    pickletools.ArgumentDescriptor = attr.s(
        these={"name": attr.ib(), "n": attr.ib()}, init=False
    )(
        pickletools.ArgumentDescriptor
    )


def test_string():
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(
                op=BINUNICODE, arg="a", pos=2, stackslice=None
            ),  # this will be str on py2 and unicode on py3
            _ParseEntry(op=BINPUT, arg=0, pos=8, stackslice=None),
            _ParseEntry(op=STOP, arg=None, pos=10, stackslice=[pyunicode]),
        ],
        maxproto=2,
        stack=[],
        memo={0: pyunicode},
    )
    actual = _parse(dumps(u"a", protocol=3))
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


def test_list_of_three_ints():
    list_of_three_ints_slice = [pylist, markobject, [pyint, pyint, pyint]]
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(op=EMPTY_LIST, arg=None, pos=2, stackslice=None),
            _ParseEntry(op=BINPUT, arg=0, pos=3, stackslice=None),
            _ParseEntry(op=MARK, arg=None, pos=5, stackslice=None),
            _ParseEntry(op=BININT1, arg=1, pos=6, stackslice=None),
            _ParseEntry(op=BININT1, arg=2, pos=8, stackslice=None),
            _ParseEntry(op=BININT1, arg=3, pos=10, stackslice=None),
            _ParseEntry(
                op=APPENDS, arg=None, pos=12, stackslice=list_of_three_ints_slice
            ),
            _ParseEntry(
                op=STOP, arg=None, pos=13, stackslice=[list_of_three_ints_slice]
            ),
        ],
        maxproto=2,
        stack=[],
        memo={0: pylist},
    )
    actual = _parse(dumps([1, 2, 3], protocol=3))
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


def test_nested_list():
    inner = [1]
    middle = [2, inner]
    outer = [3, middle]

    innerslice = [pylist, pyint]  # no markobject because plain append, not appends
    middleslice = [pylist, markobject, [pyint, innerslice]]
    outerslice = [pylist, markobject, [pyint, middleslice]]

    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            # Outer list
            _ParseEntry(op=EMPTY_LIST, arg=None, pos=2, stackslice=None),
            _ParseEntry(op=BINPUT, arg=0, pos=3, stackslice=None),
            _ParseEntry(op=MARK, arg=None, pos=5, stackslice=None),
            _ParseEntry(op=BININT1, arg=3, pos=6, stackslice=None),
            # Middle list
            _ParseEntry(op=EMPTY_LIST, arg=None, pos=8, stackslice=None),
            _ParseEntry(op=BINPUT, arg=1, pos=9, stackslice=None),
            _ParseEntry(op=MARK, arg=None, pos=11, stackslice=None),
            _ParseEntry(op=BININT1, arg=2, pos=12, stackslice=None),
            # Inner list
            _ParseEntry(op=EMPTY_LIST, arg=None, pos=14, stackslice=None),
            _ParseEntry(op=BINPUT, arg=2, pos=15, stackslice=None),
            _ParseEntry(op=BININT1, arg=1, pos=17, stackslice=None),
            # Build inner, middle, outer lists
            _ParseEntry(op=APPEND, arg=None, pos=19, stackslice=innerslice),
            _ParseEntry(op=APPENDS, arg=None, pos=20, stackslice=middleslice),
            _ParseEntry(op=APPENDS, arg=None, pos=21, stackslice=outerslice),
            _ParseEntry(op=STOP, arg=None, pos=22, stackslice=[outerslice]),
        ],
        maxproto=2,
        stack=[],
        memo={0: pylist, 1: pylist, 2: pylist},
    )
    actual = _parse(dumps(outer, protocol=3))
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


class NullReduce(object):

    def __reduce__(self):
        return NullReduce, ()


def test_reduce():
    actual = _parse(dumps(NullReduce(), protocol=3))
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(
                op=GLOBAL, arg="tests.test_parse NullReduce", pos=2, stackslice=None
            ),
            _ParseEntry(op=BINPUT, arg=0, pos=31, stackslice=None),
            _ParseEntry(op=EMPTY_TUPLE, arg=None, pos=33, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=34,
                stackslice=[
                    actual.global_objects["tests.test_parse NullReduce"], pytuple
                ],
            ),
            _ParseEntry(op=BINPUT, arg=1, pos=35, stackslice=None),
            _ParseEntry(
                op=STOP,
                arg=None,
                pos=37,
                stackslice=[
                    [actual.global_objects["tests.test_parse NullReduce"], pytuple]
                ],
            ),
        ],
        maxproto=2,
        stack=[],
        memo={
            0: actual.global_objects["tests.test_parse NullReduce"],
            1: [actual.global_objects["tests.test_parse NullReduce"], pytuple],
        },
    )
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


class ReduceSentinel(object):

    def __init__(self, s):
        self.s = s

    def __reduce__(self):
        return ReduceSentinel, (self.s,)


def test_reduce_sentinel():
    actual = _parse(dumps(ReduceSentinel(Ellipsis), protocol=3))
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(
                op=GLOBAL, arg="tests.test_parse ReduceSentinel", pos=2, stackslice=None
            ),
            _ParseEntry(op=BINPUT, arg=0, pos=35, stackslice=None),
            _ParseEntry(op=GLOBAL, arg="builtins Ellipsis", pos=37, stackslice=None),
            _ParseEntry(op=BINPUT, arg=1, pos=56, stackslice=None),
            _ParseEntry(
                op=TUPLE1,
                arg=None,
                pos=58,
                stackslice=[actual.global_objects["builtins Ellipsis"]],
            ),
            _ParseEntry(op=BINPUT, arg=2, pos=59, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=61,
                stackslice=[
                    actual.global_objects["tests.test_parse ReduceSentinel"],
                    [actual.global_objects["builtins Ellipsis"]],
                ],
            ),
            _ParseEntry(op=BINPUT, arg=3, pos=62, stackslice=None),
            _ParseEntry(
                op=STOP,
                arg=None,
                pos=64,
                stackslice=[
                    [
                        actual.global_objects["tests.test_parse ReduceSentinel"],
                        [actual.global_objects["builtins Ellipsis"]],
                    ]
                ],
            ),
        ],
        maxproto=2,
        stack=[],
        memo={
            0: actual.global_objects["tests.test_parse ReduceSentinel"],
            1: actual.global_objects["builtins Ellipsis"],
            2: [actual.global_objects["builtins Ellipsis"]],
            3: [
                actual.global_objects["tests.test_parse ReduceSentinel"],
                [actual.global_objects["builtins Ellipsis"]],
            ],
        },
    )
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


def test_reduce_sentinel_list():
    actual = _parse(
        dumps(
            [ReduceSentinel(Ellipsis), ReduceSentinel(True), ReduceSentinel(None)],
            protocol=3,
        )
    )
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(op=EMPTY_LIST, arg=None, pos=2, stackslice=None),
            _ParseEntry(op=BINPUT, arg=0, pos=3, stackslice=None),
            _ParseEntry(op=MARK, arg=None, pos=5, stackslice=None),
            _ParseEntry(
                op=GLOBAL, arg="tests.test_parse ReduceSentinel", pos=6, stackslice=None
            ),
            _ParseEntry(op=BINPUT, arg=1, pos=39, stackslice=None),
            _ParseEntry(op=GLOBAL, arg="builtins Ellipsis", pos=41, stackslice=None),
            _ParseEntry(op=BINPUT, arg=2, pos=60, stackslice=None),
            _ParseEntry(
                op=TUPLE1,
                arg=None,
                pos=62,
                stackslice=[actual.global_objects["builtins Ellipsis"]],
            ),
            _ParseEntry(op=BINPUT, arg=3, pos=63, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=65,
                stackslice=[
                    actual.global_objects["tests.test_parse ReduceSentinel"],
                    [actual.global_objects["builtins Ellipsis"]],
                ],
            ),
            _ParseEntry(op=BINPUT, arg=4, pos=66, stackslice=None),
            _ParseEntry(op=BINGET, arg=1, pos=68, stackslice=None),
            _ParseEntry(op=NEWTRUE, arg=None, pos=70, stackslice=None),
            _ParseEntry(op=TUPLE1, arg=None, pos=71, stackslice=[pybool]),
            _ParseEntry(op=BINPUT, arg=5, pos=72, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=74,
                stackslice=[
                    actual.global_objects["tests.test_parse ReduceSentinel"], [pybool]
                ],
            ),
            _ParseEntry(op=BINPUT, arg=6, pos=75, stackslice=None),
            _ParseEntry(op=BINGET, arg=1, pos=77, stackslice=None),
            _ParseEntry(op=NONE, arg=None, pos=79, stackslice=None),
            _ParseEntry(op=TUPLE1, arg=None, pos=80, stackslice=[pynone]),
            _ParseEntry(op=BINPUT, arg=7, pos=81, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=83,
                stackslice=[
                    actual.global_objects["tests.test_parse ReduceSentinel"], [pynone]
                ],
            ),
            _ParseEntry(op=BINPUT, arg=8, pos=84, stackslice=None),
            _ParseEntry(
                op=APPENDS,
                arg=None,
                pos=86,
                stackslice=[
                    pylist,
                    markobject,
                    [
                        [
                            actual.global_objects["tests.test_parse ReduceSentinel"],
                            [actual.global_objects["builtins Ellipsis"]],
                        ],
                        [
                            actual.global_objects["tests.test_parse ReduceSentinel"],
                            [pybool],
                        ],
                        [
                            actual.global_objects["tests.test_parse ReduceSentinel"],
                            [pynone],
                        ],
                    ],
                ],
            ),
            _ParseEntry(
                op=STOP,
                arg=None,
                pos=87,
                stackslice=[
                    [
                        pylist,
                        markobject,
                        [
                            [
                                actual.global_objects[
                                    "tests.test_parse ReduceSentinel"
                                ],
                                [actual.global_objects["builtins Ellipsis"]],
                            ],
                            [
                                actual.global_objects[
                                    "tests.test_parse ReduceSentinel"
                                ],
                                [pybool],
                            ],
                            [
                                actual.global_objects[
                                    "tests.test_parse ReduceSentinel"
                                ],
                                [pynone],
                            ],
                        ],
                    ]
                ],
            ),
        ],
        maxproto=2,
        stack=[],
        memo={
            0: pylist,
            1: actual.global_objects["tests.test_parse ReduceSentinel"],
            2: actual.global_objects["builtins Ellipsis"],
            3: [actual.global_objects["builtins Ellipsis"]],
            4: [
                actual.global_objects["tests.test_parse ReduceSentinel"],
                [actual.global_objects["builtins Ellipsis"]],
            ],
            5: [pybool],
            6: [actual.global_objects["tests.test_parse ReduceSentinel"], [pybool]],
            7: [pynone],
            8: [actual.global_objects["tests.test_parse ReduceSentinel"], [pynone]],
        },
    )
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo


class NullReduceEx(object):

    def __reduce_ex__(self, protocol):
        return NullReduceEx, ()


def test_reduce_ex():
    actual = _parse(dumps(NullReduceEx(), protocol=3))
    expected = _ParseResult(
        parsed=[
            _ParseEntry(op=PROTO, arg=3, pos=0, stackslice=None),
            _ParseEntry(
                op=GLOBAL, arg="tests.test_parse NullReduceEx", pos=2, stackslice=None
            ),
            _ParseEntry(op=BINPUT, arg=0, pos=33, stackslice=None),
            _ParseEntry(op=EMPTY_TUPLE, arg=None, pos=35, stackslice=None),
            _ParseEntry(
                op=REDUCE,
                arg=None,
                pos=36,
                stackslice=[
                    actual.global_objects["tests.test_parse NullReduceEx"], pytuple
                ],
            ),
            _ParseEntry(op=BINPUT, arg=1, pos=37, stackslice=None),
            _ParseEntry(
                op=STOP,
                arg=None,
                pos=39,
                stackslice=[
                    [actual.global_objects["tests.test_parse NullReduceEx"], pytuple]
                ],
            ),
        ],
        maxproto=2,
        stack=[],
        memo={
            0: actual.global_objects["tests.test_parse NullReduceEx"],
            1: [actual.global_objects["tests.test_parse NullReduceEx"], pytuple],
        },
    )
    assert expected.parsed == actual.parsed
    assert expected.maxproto == actual.maxproto
    assert expected.stack == actual.stack
    assert expected.memo == actual.memo
