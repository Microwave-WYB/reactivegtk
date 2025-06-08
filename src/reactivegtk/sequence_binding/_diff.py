from dataclasses import dataclass
from typing import TypeVar, Generic, Callable
from collections.abc import Sequence, Mapping, Iterator
from itertools import chain


SourceT = TypeVar("SourceT")
TargetT = TypeVar("TargetT")
ContainerT = TypeVar("ContainerT")
KeyT = TypeVar("KeyT")


@dataclass(frozen=True)
class Remove(Generic[KeyT]):
    """Remove operation for a key."""

    key: KeyT


@dataclass(frozen=True)
class Insert(Generic[KeyT]):
    """Insert operation for a key at a position."""

    key: KeyT
    at: int


@dataclass(frozen=True)
class Move(Generic[KeyT]):
    """Move operation for a key to a new position."""

    key: KeyT
    at: int


Operation = Remove[KeyT] | Insert[KeyT] | Move[KeyT]


def longest_increasing_subsequence_indices(arr: Sequence[int]) -> Sequence[int]:
    """Find indices of the longest increasing subsequence."""
    if not arr:
        return []

    n = len(arr)
    dp = [1] * n
    parent = [-1] * n

    for i in range(1, n):
        for j in range(i):
            if arr[j] < arr[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                parent[i] = j

    max_length = max(dp)
    end_pos = dp.index(max_length)

    lis_indices = []
    current = end_pos
    while current != -1:
        lis_indices.append(current)
        current = parent[current]

    return list(reversed(lis_indices))


def compute_diff_operations(
    old_key_to_index: Mapping[KeyT, int],
    new_key_to_index: Mapping[KeyT, int],
    new_sequence: Sequence[SourceT],
    key_func: Callable[[SourceT], KeyT],
) -> Iterator[Operation[KeyT]]:
    """Compute minimal operations using Longest Common Subsequence approach."""
    # Find the longest increasing subsequence of positions for items that exist in both
    common_items = [item for item in new_sequence if key_func(item) in old_key_to_index]
    old_positions = [old_key_to_index[key_func(item)] for item in common_items]

    # Find LIS to determine which items can stay in place
    lis_indices = longest_increasing_subsequence_indices(old_positions)
    items_to_keep = {key_func(common_items[i]) for i in lis_indices}

    # Separate keys into different categories
    deleted_keys = {key for key in old_key_to_index if key not in new_key_to_index}
    moved_keys = {
        key for key in old_key_to_index if key in new_key_to_index and key not in items_to_keep
    }
    new_keys_only = {key for key in new_key_to_index if key not in old_key_to_index}

    # 1. Remove deleted items first
    yield from (Remove(key=key) for key in deleted_keys)

    # 2. Then handle moves and inserts by final position (reverse order)
    moves = (Move(key=key, at=new_key_to_index[key]) for key in moved_keys)
    inserts = (Insert(key=key, at=new_key_to_index[key]) for key in new_keys_only)

    # Sort by position (descending) to avoid position shifts
    yield from sorted(chain(moves, inserts), key=lambda op: op.at, reverse=True)


def diff_update(
    container: ContainerT,
    old_source: Sequence[SourceT],
    new_source: Sequence[SourceT],
    key_func: Callable[[SourceT], KeyT],
    factory: Callable[[SourceT], TargetT],
    remove: Callable[[ContainerT, TargetT], None],
    insert: Callable[[ContainerT, TargetT, int], None],
    get_container_items: Callable[[ContainerT], Sequence[TargetT]],
) -> None:
    """Apply minimal diff updates to transform container from old_source to new_source state."""
    current_items = get_container_items(container)

    # Create mappings once
    old_key_to_index = {key_func(item): i for i, item in enumerate(old_source)}
    new_key_to_index = {key_func(item): i for i, item in enumerate(new_source)}
    new_key_to_item = {key_func(item): item for item in new_source}

    def apply_operation(operation: Operation[KeyT]) -> None:
        """Apply a single operation."""

        match operation:
            case Remove(key=key):
                old_position = old_key_to_index[key]
                if old_position < len(current_items):
                    target_item = current_items[old_position]
                    remove(container, target_item)

            case Insert(key=key, at=at):
                source_item = new_key_to_item[key]
                target_item = factory(source_item)
                insert(container, target_item, at)

            case Move(key=key, at=at):
                old_position = old_key_to_index[key]
                if old_position < len(current_items):
                    target_item = current_items[old_position]
                    remove(container, target_item)
                    insert(container, target_item, at)

    for op in compute_diff_operations(old_key_to_index, new_key_to_index, new_source, key_func):
        apply_operation(op)
