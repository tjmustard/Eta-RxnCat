"""Keyed engine options and the resolved stage (mission R6, ADR-0016 PROPOSED).

Every option that changes a result is keyed: it lives in ``StageConfig.options`` and, in the
engine's resolved stage, always carries its value (given or default) plus ``engine_impl``. So a
default left implicit and the same value given explicitly produce the same cache key. Runtime
arguments (devices, paths, threads) are constructor keywords and never enter the options.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from eta_rxncat.core import StageConfig
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines.errors import EngineInputError

ENGINE_IMPL_KEY = "engine_impl"
"""The resolved option recording the engine implementation version."""

OptionType = type[str] | type[int] | type[float] | type[bool]


def _coerce(spec_type: OptionType, value: ScalarValue) -> ScalarValue | None:
    """Return ``value`` as ``spec_type``, or ``None`` if it is not of that type.

    ``bool`` is accepted only for ``bool`` specs (never as ``int`` or ``float``), and an ``int``
    given for a ``float`` spec becomes a ``float``, so ``1`` and ``1.0`` key the same.
    """
    if spec_type is bool:
        return value if isinstance(value, bool) else None
    if isinstance(value, bool):
        return None
    if spec_type is float and isinstance(value, int | float):
        return float(value)
    if spec_type is int and isinstance(value, int):
        return value
    if spec_type is str and isinstance(value, str):
        return value
    return None


@dataclass(frozen=True)
class OptionSpec:
    """One keyed option: its type, default and (optionally) the allowed values.

    Attributes:
        type: ``str``, ``int``, ``float`` or ``bool``.
        default: The value used when the stage does not give one.
        allowed: The permitted values, or ``None`` for any value of ``type``.
    """

    type: OptionType
    default: ScalarValue
    allowed: frozenset[ScalarValue] | None = None

    def __post_init__(self) -> None:
        """Check the spec itself: a known type, and a default of that type and allowed."""
        if self.type not in (str, int, float, bool):
            raise TypeError(f"option type must be str, int, float or bool, not {self.type!r}")
        if _coerce(self.type, self.default) is None:
            raise TypeError(f"default {self.default!r} is not a {self.type.__name__}")
        if self.allowed is not None and self.default not in self.allowed:
            raise ValueError(f"default {self.default!r} is not in allowed {sorted(self.allowed)}")


def resolve_options(
    tag: str,
    table: Mapping[str, OptionSpec],
    given: Mapping[str, ScalarValue],
    engine_impl: int,
) -> dict[str, ScalarValue]:
    """Return every option of ``table`` (given or default) plus ``engine_impl``.

    Raises:
        EngineInputError: an unknown key, a caller-set ``engine_impl``, a value of the wrong
            type or a value outside ``allowed``; the message names the engine and the key.
    """
    if ENGINE_IMPL_KEY in table:
        raise ValueError(f"engine {tag!r} option table may not define {ENGINE_IMPL_KEY!r}")
    if isinstance(engine_impl, bool) or not isinstance(engine_impl, int) or engine_impl < 1:
        raise ValueError(f"engine_impl must be an int >= 1, not {engine_impl!r}")
    if ENGINE_IMPL_KEY in given:
        raise EngineInputError(
            f"engine {tag!r}: option {ENGINE_IMPL_KEY!r} is set by the engine, not the stage"
        )
    unknown = sorted(set(given) - set(table))
    if unknown:
        raise EngineInputError(
            f"engine {tag!r}: unknown option(s) {unknown}; known: {sorted(table)}"
        )
    resolved: dict[str, ScalarValue] = {}
    for key in sorted(table):
        spec = table[key]
        raw = given.get(key, spec.default)
        value = _coerce(spec.type, raw)
        if value is None:
            raise EngineInputError(
                f"engine {tag!r}: option {key!r} must be {spec.type.__name__}, "
                f"not {type(raw).__name__} {raw!r}"
            )
        if spec.allowed is not None and value not in spec.allowed:
            raise EngineInputError(
                f"engine {tag!r}: option {key!r} value {value!r} not in {sorted(spec.allowed)}"
            )
        resolved[key] = value
    resolved[ENGINE_IMPL_KEY] = engine_impl
    return resolved


def normalise_solvent(stage: StageConfig) -> StageConfig:
    """Return ``stage`` with ``solvation.solvent`` lowercased (a new object when it changes)."""
    solvent = stage.solvation.solvent
    if solvent is None or solvent == solvent.lower():
        return stage
    data = stage.model_dump()
    data["solvation"]["solvent"] = solvent.lower()
    return StageConfig.model_validate(data)


def resolved_stage(
    stage: StageConfig,
    table: Mapping[str, OptionSpec],
    engine_impl: int,
    normalise: Callable[[StageConfig], StageConfig] = normalise_solvent,
) -> StageConfig:
    """Return a new ``StageConfig``: ``normalise(stage)`` with fully resolved options.

    ``stage`` itself is never changed. Engines pass their own ``normalise`` (which should still
    lowercase the solvent) to canonicalise further fields.
    """
    options = resolve_options(stage.engine, table, stage.options, engine_impl)
    data = normalise(stage).model_dump()
    data["options"] = options
    return StageConfig.model_validate(data)
