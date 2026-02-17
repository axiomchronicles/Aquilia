"""
MLOps Data Structures — High-performance primitives for ML pipelines.

All structures are designed for the hot path: inference routing,
metrics collection, registry caching, and drift windowing.

Structures::

    RingBuffer       — fixed-capacity circular buffer for sliding-window stats
    LRUCache         — O(1) eviction cache for registry lookups & model artifacts
    AtomicCounter    — thread-safe monotonic counter (lock-free via threading)
    ExponentialDecay — EWMA (exponentially weighted moving average)
    SlidingWindow    — time-bucketed sliding window for rate/latency tracking
    TopKHeap         — space-efficient top-K tracker for hot models
    BloomFilter      — probabilistic set for dedup / fast negative lookups
    ConsistentHash   — jump-consistent hashing for sticky model routing
    ModelLineageDAG  — DAG of model derivation relationships
    ExperimentLedger — A/B experiment assignment + metric ledger
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Generic,
    Hashable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
)

T = TypeVar("T")
KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")


# ═══════════════════════════════════════════════════════════════════════════
# Ring Buffer
# ═══════════════════════════════════════════════════════════════════════════


class RingBuffer(Generic[T]):
    """
    Fixed-capacity circular buffer backed by a pre-allocated list.

    O(1) append, O(1) index access.  When the buffer is full the oldest
    element is silently overwritten — ideal for sliding-window metrics
    (latency histograms, throughput counters) where only the last *N*
    observations matter.

    Thread safety: a single writer + multiple readers is safe without
    locks because ``_head`` is a monotonically increasing integer and
    we never mutate already-written slots.

    >>> rb = RingBuffer(4)
    >>> for v in range(6):
    ...     rb.append(v)
    >>> list(rb)
    [2, 3, 4, 5]
    """

    __slots__ = ("_buf", "_cap", "_head", "_full")

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be ≥ 1")
        self._cap = capacity
        self._buf: list[Any] = [None] * capacity
        self._head = 0          # next write index
        self._full = False

    # ── Mutations ────────────────────────────────────────────────────

    def append(self, value: T) -> None:
        self._buf[self._head] = value
        self._head = (self._head + 1) % self._cap
        if self._head == 0 and not self._full:
            self._full = True

    def extend(self, values: Sequence[T]) -> None:
        for v in values:
            self.append(v)

    def clear(self) -> None:
        self._buf = [None] * self._cap
        self._head = 0
        self._full = False

    # ── Queries ──────────────────────────────────────────────────────

    def __len__(self) -> int:
        return self._cap if self._full else self._head

    def __bool__(self) -> bool:
        return self._full or self._head > 0

    def __iter__(self) -> Iterator[T]:
        n = len(self)
        start = self._head if self._full else 0
        for i in range(n):
            yield self._buf[(start + i) % self._cap]

    def __getitem__(self, idx: int) -> T:
        n = len(self)
        if idx < 0:
            idx += n
        if idx < 0 or idx >= n:
            raise IndexError(idx)
        start = self._head if self._full else 0
        return self._buf[(start + idx) % self._cap]

    @property
    def capacity(self) -> int:
        return self._cap

    def last(self) -> T:
        """Return the most recently appended element."""
        if not self:
            raise IndexError("empty buffer")
        return self._buf[(self._head - 1) % self._cap]

    def to_list(self) -> list[T]:
        return list(self)

    def percentile(self, p: float) -> float:
        """Compute the *p*-th percentile (0–100) over numeric elements."""
        values = sorted(self)
        if not values:
            return 0.0
        idx = int(len(values) * p / 100.0)
        return float(values[min(idx, len(values) - 1)])


# ═══════════════════════════════════════════════════════════════════════════
# LRU Cache
# ═══════════════════════════════════════════════════════════════════════════


class LRUCache(Generic[KT, VT]):
    """
    O(1) get / put / evict cache backed by :class:`OrderedDict`.

    Suitable for caching registry manifest lookups, resolved model
    artifacts, and compiled inference graphs.

    Thread-safe via a coarse lock (acceptable for registry reads
    which are I/O-bound).

    >>> c = LRUCache(2)
    >>> c.put("a", 1); c.put("b", 2); c.put("c", 3)
    >>> c.get("a")  # evicted
    >>> c.get("b")
    2
    """

    __slots__ = ("_cap", "_data", "_lock", "_hits", "_misses")

    def __init__(self, capacity: int = 128) -> None:
        if capacity < 1:
            raise ValueError("capacity must be ≥ 1")
        self._cap = capacity
        self._data: OrderedDict[KT, VT] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: KT, default: Optional[VT] = None) -> Optional[VT]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._hits += 1
                return self._data[key]
            self._misses += 1
            return default

    def put(self, key: KT, value: VT) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = value
            else:
                if len(self._data) >= self._cap:
                    self._data.popitem(last=False)
                self._data[key] = value

    def invalidate(self, key: KT) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._hits = self._misses = 0

    def __contains__(self, key: KT) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "capacity": self._cap,
            "size": len(self._data),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Atomic Counter
# ═══════════════════════════════════════════════════════════════════════════


class AtomicCounter:
    """
    Thread-safe monotonic counter (integers only).

    Uses a lightweight lock rather than ``threading.Value`` to avoid
    ctypes overhead and remain pure-Python.

    >>> c = AtomicCounter()
    >>> c.inc(); c.inc(5); c.value
    6
    """

    __slots__ = ("_value", "_lock")

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    def inc(self, n: int = 1) -> int:
        with self._lock:
            self._value += n
            return self._value

    def dec(self, n: int = 1) -> int:
        with self._lock:
            self._value -= n
            return self._value

    @property
    def value(self) -> int:
        return self._value

    def reset(self, to: int = 0) -> None:
        with self._lock:
            self._value = to

    def __repr__(self) -> str:
        return f"AtomicCounter({self._value})"


# ═══════════════════════════════════════════════════════════════════════════
# Exponential Weighted Moving Average
# ═══════════════════════════════════════════════════════════════════════════


class ExponentialDecay:
    """
    EWMA (Exponentially Weighted Moving Average).

    Ideal for smoothing noisy latency / throughput metrics.

    The smoothing factor ``alpha`` ∈ (0, 1].  Higher alpha puts more
    weight on recent observations.

    >>> e = ExponentialDecay(alpha=0.3)
    >>> for v in [10, 12, 11, 13, 12]:
    ...     e.update(v)
    >>> round(e.value, 2)
    11.69
    """

    __slots__ = ("_alpha", "_value", "_initialized")

    def __init__(self, alpha: float = 0.1) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1]")
        self._alpha = alpha
        self._value = 0.0
        self._initialized = False

    def update(self, sample: float) -> float:
        if not self._initialized:
            self._value = sample
            self._initialized = True
        else:
            self._value = self._alpha * sample + (1 - self._alpha) * self._value
        return self._value

    @property
    def value(self) -> float:
        return self._value

    def reset(self) -> None:
        self._value = 0.0
        self._initialized = False


# ═══════════════════════════════════════════════════════════════════════════
# Sliding Window (time-bucketed)
# ═══════════════════════════════════════════════════════════════════════════


class SlidingWindow:
    """
    Time-bucketed sliding window for rate/latency tracking.

    Divides time into fixed-width buckets and keeps only the most
    recent ``window_seconds`` of data.  Used by the autoscaler and
    drift detector.

    Complexities:
        add()   → O(1) amortised
        rate()  → O(buckets)
        sum()   → O(buckets)

    >>> w = SlidingWindow(window_seconds=60, bucket_width=10)
    >>> w.add(1.0)
    >>> w.count()
    1
    """

    __slots__ = ("_window", "_width", "_buckets", "_n_buckets")

    def __init__(self, window_seconds: float = 60.0, bucket_width: float = 1.0):
        if bucket_width <= 0 or window_seconds <= 0:
            raise ValueError("window and bucket must be > 0")
        self._window = window_seconds
        self._width = bucket_width
        self._n_buckets = int(math.ceil(window_seconds / bucket_width))
        # Each bucket: (timestamp_floor, count, total_value)
        self._buckets: Deque[Tuple[float, int, float]] = deque(
            maxlen=self._n_buckets
        )

    def _bucket_key(self, ts: float) -> float:
        return ts - (ts % self._width)

    def _expire(self, now: float) -> None:
        cutoff = now - self._window
        while self._buckets and self._buckets[0][0] < cutoff:
            self._buckets.popleft()

    def add(self, value: float = 1.0, *, ts: Optional[float] = None) -> None:
        now = ts or time.monotonic()
        self._expire(now)
        key = self._bucket_key(now)
        if self._buckets and self._buckets[-1][0] == key:
            _, c, s = self._buckets[-1]
            self._buckets[-1] = (key, c + 1, s + value)
        else:
            self._buckets.append((key, 1, value))

    def count(self, *, ts: Optional[float] = None) -> int:
        now = ts or time.monotonic()
        self._expire(now)
        return sum(c for _, c, _ in self._buckets)

    def total(self, *, ts: Optional[float] = None) -> float:
        now = ts or time.monotonic()
        self._expire(now)
        return sum(s for _, _, s in self._buckets)

    def rate(self, *, ts: Optional[float] = None) -> float:
        """Events per second over the window."""
        now = ts or time.monotonic()
        self._expire(now)
        n = sum(c for _, c, _ in self._buckets)
        return n / self._window if self._window > 0 else 0.0

    def mean(self, *, ts: Optional[float] = None) -> float:
        now = ts or time.monotonic()
        self._expire(now)
        n = sum(c for _, c, _ in self._buckets)
        s = sum(s for _, _, s in self._buckets)
        return s / n if n > 0 else 0.0

    def clear(self) -> None:
        self._buckets.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Top-K Heap (space-efficient)
# ═══════════════════════════════════════════════════════════════════════════


class TopKHeap(Generic[KT]):
    """
    Maintains the top-K elements by score using a dict + sort-on-read
    strategy (optimal for K ≤ ~1000).

    Use case: track the most-requested models, highest-latency
    endpoints, or most-drifted features.

    >>> t = TopKHeap(3)
    >>> for model, score in [("a",5),("b",3),("c",8),("d",1),("e",9)]:
    ...     t.push(model, score)
    >>> [x for x, _ in t.top()]
    ['e', 'c', 'a']
    """

    __slots__ = ("_k", "_scores")

    def __init__(self, k: int = 10) -> None:
        self._k = k
        self._scores: Dict[KT, float] = {}

    def push(self, key: KT, score: float) -> None:
        if key in self._scores:
            self._scores[key] = max(self._scores[key], score)
        else:
            self._scores[key] = score
        # Prune when 2× capacity (amortised O(1) per push)
        if len(self._scores) > self._k * 2:
            self._prune()

    def _prune(self) -> None:
        top = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)[: self._k]
        self._scores = dict(top)

    def top(self) -> List[Tuple[KT, float]]:
        items = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return items[: self._k]

    def __len__(self) -> int:
        return min(len(self._scores), self._k)

    def __contains__(self, key: KT) -> bool:
        return key in self._scores


# ═══════════════════════════════════════════════════════════════════════════
# Bloom Filter (probabilistic membership)
# ═══════════════════════════════════════════════════════════════════════════


class BloomFilter:
    """
    Space-efficient probabilistic set for fast negative lookups.

    Use case: quickly reject duplicate inference request IDs or
    already-processed digest hashes without touching the DB.

    Parameters:
        expected_items:  anticipated number of elements
        fp_rate:         desired false-positive probability

    The filter computes optimal ``m`` (bits) and ``k`` (hash functions)
    via the standard formulas.
    """

    __slots__ = ("_bits", "_m", "_k_hashes")

    def __init__(self, expected_items: int = 10_000, fp_rate: float = 0.01) -> None:
        ln2 = math.log(2)
        self._m = max(
            64,
            int(-expected_items * math.log(fp_rate) / (ln2 * ln2)),
        )
        self._k_hashes = max(1, int((self._m / expected_items) * ln2))
        self._bits = bytearray(self._m // 8 + 1)

    def _hash_indices(self, item: str) -> List[int]:
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)
        return [(h1 + i * h2) % self._m for i in range(self._k_hashes)]

    def add(self, item: str) -> None:
        for idx in self._hash_indices(item):
            self._bits[idx // 8] |= 1 << (idx % 8)

    def __contains__(self, item: str) -> bool:
        return all(
            self._bits[idx // 8] & (1 << (idx % 8))
            for idx in self._hash_indices(item)
        )

    @property
    def size_bytes(self) -> int:
        return len(self._bits)

    def clear(self) -> None:
        self._bits = bytearray(len(self._bits))


# ═══════════════════════════════════════════════════════════════════════════
# Consistent Hashing (jump hash)
# ═══════════════════════════════════════════════════════════════════════════


class ConsistentHash:
    """
    Jump-consistent hash for sticky model-to-node routing.

    Given a key and *n* buckets, returns a bucket index in [0, n).
    Adding a new bucket only redistributes ~1/n of existing keys.

    Algorithm: `A Fast, Minimal Memory, Consistent Hash Algorithm`
    (Lamping & Veach, 2014).

    >>> ch = ConsistentHash(3)
    >>> ch.bucket("model-v1")     # always same bucket for same key
    1
    >>> ch.add_bucket()           # add node, minimal redistribution
    >>> ch.bucket("model-v1")
    1
    """

    __slots__ = ("_n",)

    def __init__(self, num_buckets: int = 1) -> None:
        if num_buckets < 1:
            raise ValueError("num_buckets must be ≥ 1")
        self._n = num_buckets

    def bucket(self, key: str) -> int:
        h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        return self._jump(h, self._n)

    def add_bucket(self) -> int:
        self._n += 1
        return self._n

    def remove_bucket(self) -> int:
        if self._n <= 1:
            raise ValueError("cannot remove last bucket")
        self._n -= 1
        return self._n

    @property
    def num_buckets(self) -> int:
        return self._n

    @staticmethod
    def _jump(key: int, num_buckets: int) -> int:
        """Jump-consistent hash algorithm."""
        b, j = -1, 0
        while j < num_buckets:
            b = j
            key = ((key * 2862933555777941757) + 1) & 0xFFFFFFFFFFFFFFFF
            j = int((b + 1) * (1 << 31) / ((key >> 33) + 1))
        return b


# ═══════════════════════════════════════════════════════════════════════════
# Model Lineage DAG
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class LineageNode:
    """A single node in the model lineage graph."""
    model_id: str
    version: str
    framework: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parents: List[str] = field(default_factory=list)    # model_ids
    children: List[str] = field(default_factory=list)    # model_ids


class ModelLineageDAG:
    """
    Directed acyclic graph tracking model derivation relationships.

    Nodes are model versions; edges represent "derived-from" links
    (e.g. fine-tuning, distillation, quantization).

    Use cases:
        - ``ancestors("model-v3")`` → full training lineage
        - ``descendants("base-model")`` → all derived models
        - ``path("base", "prod-v2")`` → derivation chain
        - ``to_dict()`` → export for visualization

    >>> dag = ModelLineageDAG()
    >>> dag.add_model("base-v1", "v1")
    >>> dag.add_model("fine-v1", "v1", parents=["base-v1"])
    >>> dag.ancestors("fine-v1")
    ['base-v1']
    """

    __slots__ = ("_nodes",)

    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}

    def add_model(
        self,
        model_id: str,
        version: str,
        *,
        framework: str = "",
        parents: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        if model_id in self._nodes:
            raise ValueError(f"Model '{model_id}' already exists in lineage")

        parent_ids = parents or []
        # Validate parents exist
        for pid in parent_ids:
            if pid not in self._nodes:
                raise ValueError(f"Parent model '{pid}' not found in lineage")
            self._nodes[pid].children.append(model_id)

        node = LineageNode(
            model_id=model_id,
            version=version,
            framework=framework,
            metadata=metadata or {},
            parents=parent_ids,
        )
        self._nodes[model_id] = node
        return node

    def ancestors(self, model_id: str) -> List[str]:
        """All transitive ancestors (BFS)."""
        if model_id not in self._nodes:
            return []
        visited: Set[str] = set()
        queue: Deque[str] = deque(self._nodes[model_id].parents)
        result: List[str] = []
        while queue:
            mid = queue.popleft()
            if mid not in visited:
                visited.add(mid)
                result.append(mid)
                queue.extend(self._nodes[mid].parents)
        return result

    def descendants(self, model_id: str) -> List[str]:
        """All transitive descendants (BFS)."""
        if model_id not in self._nodes:
            return []
        visited: Set[str] = set()
        queue: Deque[str] = deque(self._nodes[model_id].children)
        result: List[str] = []
        while queue:
            mid = queue.popleft()
            if mid not in visited:
                visited.add(mid)
                result.append(mid)
                queue.extend(self._nodes[mid].children)
        return result

    def path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """
        Find shortest derivation path from ``from_id`` → ``to_id``.

        Returns None if no path exists.
        """
        if from_id not in self._nodes or to_id not in self._nodes:
            return None
        if from_id == to_id:
            return [from_id]

        visited: Set[str] = {from_id}
        queue: Deque[List[str]] = deque([[from_id]])

        while queue:
            current_path = queue.popleft()
            current = current_path[-1]
            for child in self._nodes[current].children:
                if child == to_id:
                    return current_path + [child]
                if child not in visited:
                    visited.add(child)
                    queue.append(current_path + [child])
        return None

    def roots(self) -> List[str]:
        """Models with no parents (base models)."""
        return [mid for mid, n in self._nodes.items() if not n.parents]

    def leaves(self) -> List[str]:
        """Models with no children (leaf / production models)."""
        return [mid for mid, n in self._nodes.items() if not n.children]

    def get(self, model_id: str) -> Optional[LineageNode]:
        return self._nodes.get(model_id)

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._nodes

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the full DAG for storage / visualisation."""
        return {
            mid: {
                "version": n.version,
                "framework": n.framework,
                "created_at": n.created_at,
                "metadata": n.metadata,
                "parents": n.parents,
                "children": n.children,
            }
            for mid, n in self._nodes.items()
        }


# ═══════════════════════════════════════════════════════════════════════════
# A/B Experiment Ledger
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ExperimentArm:
    """One arm of an A/B experiment."""
    name: str
    model_version: str
    weight: float = 0.5           # traffic fraction
    metrics: Dict[str, float] = field(default_factory=dict)
    request_count: int = 0


@dataclass
class Experiment:
    """A/B experiment definition."""
    experiment_id: str
    description: str = ""
    arms: List[ExperimentArm] = field(default_factory=list)
    status: str = "active"        # active | paused | completed
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExperimentLedger:
    """
    Records A/B experiment assignments and collects per-arm metrics.

    Assignment uses weighted random selection, seeded by request ID
    for reproducibility (same request_id → same arm).

    >>> ledger = ExperimentLedger()
    >>> exp = ledger.create("latency-test", arms=[
    ...     {"name": "control", "model_version": "v1", "weight": 0.5},
    ...     {"name": "treatment", "model_version": "v2", "weight": 0.5},
    ... ])
    >>> arm = ledger.assign("latency-test", "req-001")
    >>> ledger.record("latency-test", arm, "latency_ms", 12.5)
    """

    __slots__ = ("_experiments",)

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}

    def create(
        self,
        experiment_id: str,
        *,
        description: str = "",
        arms: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Experiment:
        if experiment_id in self._experiments:
            raise ValueError(f"Experiment '{experiment_id}' already exists")

        arm_objs = []
        for arm_data in (arms or []):
            arm_objs.append(ExperimentArm(
                name=arm_data["name"],
                model_version=arm_data.get("model_version", ""),
                weight=arm_data.get("weight", 0.5),
            ))

        exp = Experiment(
            experiment_id=experiment_id,
            description=description,
            arms=arm_objs,
            metadata=metadata or {},
        )
        self._experiments[experiment_id] = exp
        return exp

    def assign(self, experiment_id: str, request_id: str) -> str:
        """
        Deterministically assign a request to an experiment arm.

        Uses the hash of (experiment_id + request_id) for reproducibility.
        Returns the arm name.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != "active" or not exp.arms:
            return ""

        # Deterministic hash → float in [0, 1)
        h = hashlib.sha256(f"{experiment_id}:{request_id}".encode()).hexdigest()
        val = int(h[:8], 16) / 0xFFFFFFFF

        # Weighted selection
        cumulative = 0.0
        for arm in exp.arms:
            cumulative += arm.weight
            if val < cumulative:
                arm.request_count += 1
                return arm.name

        # Fallback to last arm
        exp.arms[-1].request_count += 1
        return exp.arms[-1].name

    def record(
        self,
        experiment_id: str,
        arm_name: str,
        metric: str,
        value: float,
    ) -> None:
        """Record a metric observation for an experiment arm (running average)."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        for arm in exp.arms:
            if arm.name == arm_name:
                prev = arm.metrics.get(metric, 0.0)
                n = arm.request_count or 1
                # Cumulative moving average
                arm.metrics[metric] = prev + (value - prev) / n
                break

    def get(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def list_active(self) -> List[Experiment]:
        return [e for e in self._experiments.values() if e.status == "active"]

    def conclude(self, experiment_id: str, winner: str = "") -> None:
        """Mark experiment as completed, optionally recording the winning arm."""
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.status = "completed"
            exp.metadata["winner"] = winner

    def pause(self, experiment_id: str) -> None:
        exp = self._experiments.get(experiment_id)
        if exp:
            exp.status = "paused"

    def resume(self, experiment_id: str) -> None:
        exp = self._experiments.get(experiment_id)
        if exp and exp.status == "paused":
            exp.status = "active"

    def summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment summary with per-arm metrics."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        return {
            "experiment_id": exp.experiment_id,
            "status": exp.status,
            "arms": [
                {
                    "name": a.name,
                    "model_version": a.model_version,
                    "weight": a.weight,
                    "request_count": a.request_count,
                    "metrics": a.metrics,
                }
                for a in exp.arms
            ],
            "metadata": exp.metadata,
        }

    def __len__(self) -> int:
        return len(self._experiments)

    def to_dict(self) -> Dict[str, Any]:
        return {eid: self.summary(eid) for eid in self._experiments}


# ═══════════════════════════════════════════════════════════════════════════
# Circuit Breaker (async, lock-free state machine)
# ═══════════════════════════════════════════════════════════════════════════


class CircuitBreaker:
    """
    Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN → CLOSED).

    Protects inference endpoints against cascading failures.  Thread-safe
    via a lock; the hot path (``allow_request``) is a single comparison
    in the CLOSED state.

    States:
        CLOSED    – requests flow normally, failures are counted
        OPEN      – all requests are rejected immediately (fail-fast)
        HALF_OPEN – a limited number of probe requests are allowed through

    >>> cb = CircuitBreaker(failure_threshold=3, timeout_seconds=5)
    >>> cb.allow_request()
    True
    >>> cb.record_failure(); cb.record_failure(); cb.record_failure()
    >>> cb.allow_request()
    False
    """

    __slots__ = (
        "_failure_threshold", "_success_threshold", "_timeout",
        "_half_open_max", "_state", "_failure_count", "_success_count",
        "_last_failure_time", "_half_open_calls", "_lock",
        "_total_failures", "_total_successes", "_total_rejections",
    )

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: float = 30.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout_seconds
        self._half_open_max = half_open_max_calls
        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()
        # Lifetime metrics
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejections = 0

    @property
    def state(self) -> str:
        with self._lock:
            self._maybe_transition()
            return self._state

    def _maybe_transition(self) -> None:
        """Transition OPEN → HALF_OPEN if timeout has elapsed."""
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self._timeout:
                self._state = "half_open"
                self._half_open_calls = 0
                self._success_count = 0

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        with self._lock:
            self._maybe_transition()
            if self._state == "closed":
                return True
            if self._state == "open":
                self._total_rejections += 1
                return False
            # half_open
            if self._half_open_calls < self._half_open_max:
                self._half_open_calls += 1
                return True
            self._total_rejections += 1
            return False

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._total_successes += 1
            if self._state == "half_open":
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = "closed"
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == "closed":
                # Reset consecutive failure count on success
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._total_failures += 1
            self._last_failure_time = time.monotonic()
            if self._state == "half_open":
                self._state = "open"
                self._half_open_calls = 0
            elif self._state == "closed":
                self._failure_count += 1
                if self._failure_count >= self._failure_threshold:
                    self._state = "open"

    def reset(self) -> None:
        """Force reset to closed state."""
        with self._lock:
            self._state = "closed"
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._maybe_transition()
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "total_rejections": self._total_rejections,
                "failure_threshold": self._failure_threshold,
                "timeout_seconds": self._timeout,
            }


# ═══════════════════════════════════════════════════════════════════════════
# Token Bucket Rate Limiter
# ═══════════════════════════════════════════════════════════════════════════


class TokenBucketRateLimiter:
    """
    Token-bucket rate limiter for inference request throttling.

    Refills at ``rate`` tokens per second up to ``capacity``.
    Each ``acquire()`` consumes one token.

    Time complexity: O(1) per acquire (lazy refill).

    >>> rl = TokenBucketRateLimiter(rate=10.0, capacity=100)
    >>> rl.acquire()
    True
    """

    __slots__ = ("_rate", "_capacity", "_tokens", "_last_refill", "_lock",
                 "_total_allowed", "_total_rejected")

    def __init__(self, rate: float = 100.0, capacity: int = 1000) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._total_allowed = 0
        self._total_rejected = 0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._total_allowed += 1
                return True
            self._total_rejected += 1
            return False

    def acquire_wait_time(self, tokens: int = 1) -> float:
        """Return seconds to wait before tokens become available, 0 if available now."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            deficit = tokens - self._tokens
            return deficit / self._rate if self._rate > 0 else float("inf")

    @property
    def available(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._refill()
            return {
                "rate": self._rate,
                "capacity": self._capacity,
                "available_tokens": self._tokens,
                "total_allowed": self._total_allowed,
                "total_rejected": self._total_rejected,
            }

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(self._capacity)
            self._last_refill = time.monotonic()


# ═══════════════════════════════════════════════════════════════════════════
# Adaptive Batch Queue (for continuous batching in LLM serving)
# ═══════════════════════════════════════════════════════════════════════════


class AdaptiveBatchQueue(Generic[T]):
    """
    Priority-aware batch queue with adaptive sizing for LLM serving.

    Supports continuous batching: items can be drained by token budget
    rather than fixed batch size, enabling efficient GPU utilisation for
    variable-length sequences.

    Features:
        - Priority ordering (higher priority first, then FIFO)
        - Token-budget-aware draining
        - Max wait time enforcement
        - Backpressure via capacity limit

    >>> q = AdaptiveBatchQueue(max_capacity=100)
    >>> q.put("req1", priority=0, token_estimate=128)
    >>> q.put("req2", priority=1, token_estimate=256)
    >>> batch = q.drain(max_tokens=512)
    >>> len(batch)
    2
    """

    __slots__ = ("_queue", "_capacity", "_lock", "_total_enqueued",
                 "_total_dequeued", "_total_dropped")

    def __init__(self, max_capacity: int = 1024) -> None:
        self._capacity = max_capacity
        # Each entry: (negative_priority, insert_order, token_estimate, item)
        self._queue: List[Tuple[int, int, int, T]] = []
        self._lock = threading.Lock()
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_dropped = 0

    def put(self, item: T, priority: int = 0, token_estimate: int = 1) -> bool:
        """
        Enqueue an item. Returns False if queue is at capacity (backpressure).
        Higher priority values are dequeued first.
        """
        import heapq
        with self._lock:
            if len(self._queue) >= self._capacity:
                self._total_dropped += 1
                return False
            heapq.heappush(
                self._queue,
                (-priority, self._total_enqueued, token_estimate, item),
            )
            self._total_enqueued += 1
            return True

    def drain(
        self,
        max_items: int = 0,
        max_tokens: int = 0,
    ) -> List[T]:
        """
        Drain items from the queue respecting token budget and/or max items.

        If both max_items and max_tokens are 0, drains everything.
        """
        import heapq
        with self._lock:
            if not self._queue:
                return []

            result: List[T] = []
            token_total = 0

            while self._queue:
                if max_items > 0 and len(result) >= max_items:
                    break
                # Peek at next item's token estimate
                neg_pri, order, tok_est, item = self._queue[0]
                if max_tokens > 0 and token_total + tok_est > max_tokens and result:
                    break  # would exceed budget and we have at least one item
                heapq.heappop(self._queue)
                result.append(item)
                token_total += tok_est
                self._total_dequeued += 1

            return result

    def peek_token_total(self) -> int:
        """Total estimated tokens currently in the queue."""
        with self._lock:
            return sum(entry[2] for entry in self._queue)

    def __len__(self) -> int:
        return len(self._queue)

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._queue),
                "capacity": self._capacity,
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
                "total_dropped": self._total_dropped,
                "pending_tokens": sum(e[2] for e in self._queue),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Memory Tracker (for GPU/CPU memory management)
# ═══════════════════════════════════════════════════════════════════════════


class MemoryTracker:
    """
    Tracks memory allocations for model serving with watermark alerts.

    Provides soft/hard limits: when usage exceeds the soft limit,
    the system should start evicting unused models; at the hard limit,
    new loads are rejected.

    >>> mt = MemoryTracker(soft_limit_mb=8000, hard_limit_mb=10000)
    >>> mt.allocate("model-v1", 2048)
    True
    >>> mt.current_usage_mb
    2048
    """

    __slots__ = ("_allocations", "_soft_limit", "_hard_limit", "_lock")

    def __init__(self, soft_limit_mb: int = 8192, hard_limit_mb: int = 12288) -> None:
        self._soft_limit = soft_limit_mb
        self._hard_limit = hard_limit_mb
        self._allocations: Dict[str, int] = {}  # name → MB
        self._lock = threading.Lock()

    def allocate(self, name: str, size_mb: int) -> bool:
        """Allocate memory for a model. Returns False if hard limit would be exceeded."""
        with self._lock:
            current = sum(self._allocations.values())
            if current + size_mb > self._hard_limit:
                return False
            self._allocations[name] = size_mb
            return True

    def release(self, name: str) -> int:
        """Release memory for a model. Returns freed MB."""
        with self._lock:
            return self._allocations.pop(name, 0)

    @property
    def current_usage_mb(self) -> int:
        with self._lock:
            return sum(self._allocations.values())

    @property
    def is_above_soft_limit(self) -> bool:
        return self.current_usage_mb > self._soft_limit

    @property
    def is_above_hard_limit(self) -> bool:
        return self.current_usage_mb > self._hard_limit

    @property
    def available_mb(self) -> int:
        return max(0, self._hard_limit - self.current_usage_mb)

    def largest_model(self) -> Optional[Tuple[str, int]]:
        """Return the name and size of the largest allocated model."""
        with self._lock:
            if not self._allocations:
                return None
            name = max(self._allocations, key=self._allocations.get)  # type: ignore[arg-type]
            return name, self._allocations[name]

    def eviction_candidates(self) -> List[Tuple[str, int]]:
        """Return models sorted by size ascending (smallest first) for eviction."""
        with self._lock:
            return sorted(self._allocations.items(), key=lambda x: x[1])

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_usage_mb": sum(self._allocations.values()),
                "soft_limit_mb": self._soft_limit,
                "hard_limit_mb": self._hard_limit,
                "model_count": len(self._allocations),
                "allocations": dict(self._allocations),
                "above_soft_limit": sum(self._allocations.values()) > self._soft_limit,
            }
