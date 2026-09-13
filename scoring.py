from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np
from scipy import sparse


Edge = tuple[str, str, str]
TYPE_WEIGHTS = {
    "finetune": 1.0,
    "adapter": 0.8,
    "merge": 0.5,
    "quantized": 0.3,
}


@dataclass(frozen=True)
class ScoreConfig:
    name: str
    quality_share: float
    event_share: float
    child_quality: bool = True
    type_weight: bool = True
    parent_size: bool = True
    damping: float = 0.85
    beta: float = 0.15
    direct_blend: float = 0.0
    alpha: float = 0.3
    kappa: float = 0.5
    parameter_backfill: float = 66_955_779.0
    tolerance: float = 1e-8
    max_iterations: int = 200
    mix_mode: str = "separate"

    def __post_init__(self) -> None:
        for label, value in (
            ("quality_share", self.quality_share),
            ("event_share", self.event_share),
            ("damping", self.damping),
            ("beta", self.beta),
            ("direct_blend", self.direct_blend),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be within [0, 1]")
        if self.quality_share + self.event_share <= 0:
            raise ValueError("at least one input share must be positive")
        if self.mix_mode not in {"separate", "raw"}:
            raise ValueError("mix_mode must be 'separate' or 'raw'")


@dataclass(frozen=True)
class ScoreTrace:
    ordered_ids: tuple[str, ...]
    q_base: Mapping[str, float]
    event_value: Mapping[str, float]
    tau: Mapping[str, float]
    pagerank: Mapping[str, float]
    quality_input_mass: float
    event_input_mass: float
    raw_event_total: float
    scaled_event_total: float
    event_scale_factor: float
    iterations: int
    dangling_fraction: float


@dataclass(frozen=True)
class ScoreResult:
    scores: Mapping[str, float]
    score_normalized: Mapping[str, float]
    trace: ScoreTrace


def _normalized(values: np.ndarray) -> np.ndarray | None:
    total = float(values.sum())
    if total <= 0:
        return None
    return values / total


def _parent_lists(
    edges: Iterable[Edge],
    id_to_index: Mapping[str, int],
) -> dict[int, list[tuple[int, str]]]:
    result: dict[int, list[tuple[int, str]]] = {}
    for child, parent, relation in sorted(set(edges)):
        if child not in id_to_index or parent not in id_to_index:
            continue
        result.setdefault(id_to_index[child], []).append(
            (id_to_index[parent], str(relation).lower())
        )
    return result


def score_month(
    model_ids: Iterable[str],
    topology_edges: Iterable[Edge],
    current_event_edges: Iterable[Edge],
    q_base: Mapping[str, float],
    params: Mapping[str, float | None],
    previous_scores: Mapping[str, float] | None,
    config: ScoreConfig,
    event_scale_target: float | None = None,
) -> ScoreResult:
    ordered = tuple(sorted(set(str(item) for item in model_ids)))
    if not ordered:
        raise ValueError("score_month requires at least one model")
    index = {model_id: position for position, model_id in enumerate(ordered)}
    size = len(ordered)
    q_values = np.array(
        [max(0.0, float(q_base.get(model_id, 0.0))) for model_id in ordered],
        dtype=float,
    )
    if not np.isfinite(q_values).all():
        raise ValueError("q_base contains nonfinite values")
    q_max = max(1.0, float(q_values.max()))

    event_parents = _parent_lists(current_event_edges, index)
    event = np.zeros(size, dtype=float)
    for child_index, parents in event_parents.items():
        share = 1.0 / len(parents)
        quality_factor = (
            config.alpha + (1.0 - config.alpha) * q_values[child_index] / q_max
            if config.child_quality
            else 1.0
        )
        for parent_index, relation in parents:
            relation_factor = (
                TYPE_WEIGHTS.get(relation, 0.5) if config.type_weight else 1.0
            )
            parameter = params.get(ordered[parent_index])
            if parameter is None or not np.isfinite(float(parameter)) or float(parameter) <= 0:
                parameter = config.parameter_backfill
            size_factor = (
                np.log1p(float(parameter)) ** config.kappa
                if config.parent_size
                else 1.0
            )
            event[parent_index] += share * relation_factor * quality_factor * size_factor

    raw_event_total = float(event.sum())
    scale_factor = 1.0
    if event_scale_target is not None:
        target = float(event_scale_target)
        if target < 0 or not np.isfinite(target):
            raise ValueError("event scale target must be finite and nonnegative")
        if raw_event_total > 0:
            scale_factor = target / raw_event_total
            event *= scale_factor
        elif target > 0:
            raise ValueError("cannot scale a zero event vector to positive mass")
    scaled_event_total = float(event.sum())

    if config.mix_mode == "raw":
        quality_part = config.quality_share * q_values
        event_part = config.event_share * event
        total = float(quality_part.sum() + event_part.sum())
        if total <= 0:
            tau = np.full(size, 1.0 / size, dtype=float)
            quality_mass = 0.0
            event_mass = 0.0
        else:
            tau = (quality_part + event_part) / total
            quality_mass = float(quality_part.sum()) / total
            event_mass = float(event_part.sum()) / total
    else:
        q_norm = _normalized(q_values)
        event_norm = _normalized(event)
        weighted = np.zeros(size, dtype=float)
        active_weight = 0.0
        if q_norm is not None and config.quality_share > 0:
            weighted += config.quality_share * q_norm
            active_weight += config.quality_share
        if event_norm is not None and config.event_share > 0:
            weighted += config.event_share * event_norm
            active_weight += config.event_share
        if active_weight <= 0:
            tau = np.full(size, 1.0 / size, dtype=float)
            quality_mass = 0.0
            event_mass = 0.0
        else:
            tau = weighted / active_weight
            quality_mass = config.quality_share / active_weight if q_norm is not None else 0.0
            event_mass = config.event_share / active_weight if event_norm is not None else 0.0

    topology_parents = _parent_lists(topology_edges, index)
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for child_index, parents in topology_parents.items():
        share = 1.0 / len(parents)
        for parent_index, _relation in parents:
            rows.append(child_index)
            columns.append(parent_index)
            values.append(share)
    transition = sparse.csr_matrix(
        (values, (rows, columns)), shape=(size, size), dtype=float
    )
    dangling = np.asarray(transition.sum(axis=1)).ravel() == 0
    current = tau.copy()
    iterations = 0
    for iteration in range(1, config.max_iterations + 1):
        updated = config.damping * (transition.T @ current)
        updated += config.damping * float(current[dangling].sum()) * tau
        updated += (1.0 - config.damping) * tau
        total = float(updated.sum())
        if total <= 0:
            raise ValueError("PageRank produced no positive mass")
        updated /= total
        difference = float(np.abs(updated - current).sum())
        current = updated
        iterations = iteration
        if difference < config.tolerance:
            break

    raw = (1.0 - config.direct_blend) * current + config.direct_blend * tau
    previous_scores = previous_scores or {}
    if config.beta > 0 and previous_scores:
        inherited = np.array(
            [max(0.0, float(previous_scores.get(model_id, 0.0))) for model_id in ordered],
            dtype=float,
        )
        inherited_total = float(inherited.sum())
        if inherited_total > 0:
            inherited /= inherited_total
            final = (1.0 - config.beta) * raw + config.beta * inherited
        else:
            final = raw
    else:
        final = raw
    final_total = float(final.sum())
    if final_total <= 0 or not np.isfinite(final).all() or np.any(final < 0):
        raise ValueError("candidate score violates finite nonnegative mass")
    final /= final_total
    normalized = final * size

    def as_map(values_array: np.ndarray) -> dict[str, float]:
        return {model_id: float(values_array[position]) for position, model_id in enumerate(ordered)}

    trace = ScoreTrace(
        ordered_ids=ordered,
        q_base=as_map(q_values),
        event_value=as_map(event),
        tau=as_map(tau),
        pagerank=as_map(current),
        quality_input_mass=float(quality_mass),
        event_input_mass=float(event_mass),
        raw_event_total=raw_event_total,
        scaled_event_total=scaled_event_total,
        event_scale_factor=float(scale_factor),
        iterations=iterations,
        dangling_fraction=float(dangling.mean()),
    )
    return ScoreResult(
        scores=as_map(final),
        score_normalized=as_map(normalized),
        trace=trace,
    )
