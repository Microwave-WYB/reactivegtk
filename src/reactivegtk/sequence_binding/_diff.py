from dataclasses import dataclass
from typing import TypeVar, Generic, Callable
from collections.abc import Iterable, Sequence, Mapping, Iterator
import weakref

# Type variables
SourceT = TypeVar("SourceT")
TargetT = TypeVar("TargetT")
ContainerT = TypeVar("ContainerT")
KeyT = TypeVar("KeyT")


# Operation data structures
@dataclass(frozen=True)
class Remove(Generic[KeyT]):
    """Remove operation for a key."""

    key: KeyT


@dataclass(frozen=True)
class Insert(Generic[KeyT]):
    """Insert operation for a key at a position."""

    key: KeyT
    at: int


# Union type for operations
Operation = Remove[KeyT] | Insert[KeyT]


def extract_keys_with_positions(
    source: Sequence[SourceT], key_func: Callable[[SourceT], KeyT]
) -> Mapping[KeyT, int]:
    """Extract keys and their positions from a source sequence."""
    return {key_func(item): i for i, item in enumerate(source)}


def longest_increasing_subsequence_indices(arr: Sequence[int]) -> list[int]:
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
    old_source: Sequence[SourceT],
    new_source: Sequence[SourceT],
    key_func: Callable[[SourceT], KeyT],
) -> Iterator[Operation[KeyT]]:
    """Compute minimal operations using Longest Common Subsequence approach."""
    old_keys = extract_keys_with_positions(old_source, key_func)
    new_keys = extract_keys_with_positions(new_source, key_func)

    # Find items to remove (in old but not in new)
    for key in old_keys:
        if key not in new_keys:
            yield Remove(key=key)

    # Find the longest increasing subsequence of positions for items that exist in both
    common_items = [item for item in new_source if key_func(item) in old_keys]
    old_positions = [old_keys[key_func(item)] for item in common_items]

    # Find LIS to determine which items can stay in place
    lis_indices = longest_increasing_subsequence_indices(old_positions)
    items_to_keep = {key_func(common_items[i]) for i in lis_indices}

    # Remove items that need to be moved (not in LIS)
    for item in common_items:
        key = key_func(item)
        if key not in items_to_keep:
            yield Remove(key=key)

    # Insert new items and moved items at their correct positions
    for key, new_position in new_keys.items():
        if key not in old_keys:
            # New item
            yield Insert(key=key, at=new_position)
        elif key not in items_to_keep:
            # Moved item (was removed above)
            yield Insert(key=key, at=new_position)


def find_target_by_key(
    container_items: Sequence[TargetT],
    old_source: Sequence[SourceT],
    key_func: Callable[[SourceT], KeyT],
    target_key: KeyT,
) -> TargetT | None:
    """Find the target item corresponding to a given key."""
    for i, source_item in enumerate(old_source):
        if key_func(source_item) == target_key:
            if i < len(container_items):
                return container_items[i]
    return None


def find_source_by_key(
    source: Iterable[SourceT], key_func: Callable[[SourceT], KeyT], target_key: KeyT
) -> SourceT | None:
    """Find the source item with the given key."""
    for item in source:
        if key_func(item) == target_key:
            return item
    return None


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
    container_ref = weakref.ref(container)
    current_items = get_container_items(container)
    old_keys = extract_keys_with_positions(old_source, key_func)
    new_keys = extract_keys_with_positions(new_source, key_func)
    removed_items: dict[KeyT, TargetT] = {}

    # Phase 1: Remove items (both deleted and moved)
    for key, old_position in old_keys.items():
        current_container = container_ref()
        if current_container is None:
            break

        if key not in new_keys:
            # Item completely removed
            target_item = find_target_by_key(current_items, old_source, key_func, key)
            if target_item is not None:
                remove(current_container, target_item)
        elif new_keys[key] != old_position:
            # Check if this item needs to be moved
            should_move = any(
                isinstance(op, Remove) and op.key == key
                for op in compute_diff_operations(old_source, new_source, key_func)
            )
            if should_move:
                target_item = find_target_by_key(current_items, old_source, key_func, key)
                if target_item is not None:
                    removed_items[key] = target_item
                    remove(current_container, target_item)

    # Phase 2: Insert items (both new and moved)
    for key, new_position in new_keys.items():
        current_container = container_ref()
        if current_container is None:
            break

        if key not in old_keys:
            # Completely new item
            source_item = find_source_by_key(new_source, key_func, key)
            if source_item is not None:
                target_item = factory(source_item)
                insert(current_container, target_item, new_position)
        elif key in removed_items:
            # Item was moved - reinsert the stored item
            insert(current_container, removed_items[key], new_position)
