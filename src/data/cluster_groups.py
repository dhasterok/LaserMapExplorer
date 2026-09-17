"""Cluster grouping ("linking").

Qt-free so it can be tested headlessly -- the GUI side lives in ``ClusterTab``
(``src/data/Masking.py``), which owns the table and the Link/Unlink toolbar
actions.

A clustering run often splits one mineral into several clusters that differ
only in something uninteresting (ablation depth, say). *Linking* merges those
clusters into one class for display and analysis. It never touches the labels
in ``SampleObj.processed[method]``, so the clustering itself is unchanged and
unlinking restores the original classes.

Groups are stored in the per-cluster entries that
``AppData.cluster_group_changed`` builds -- the int-keyed subset of
``AppData.cluster_dict[method]``, ``{id: {'name', 'color', 'link'}}``. The
``'link'`` list holds every cluster id in the group, *including the entry's
own*; an empty list means the cluster stands alone. The lowest id in a group
is its **leader**: the group takes the leader's name in legends and the
leader's color on the map.

This mirrors ``PolygonManager.link_polygons``/``unlink_polygons``
(``src/data/Polygon.py``), which groups polygons the same way.
"""
from __future__ import annotations

#: Label reserved by the clustering code for masked-out / noise pixels
#: (see ``src/app/DataAnalysis.py``). It is never a group member.
MASK_ID = 99


def _cluster_ids(entries):
    """Real cluster ids in ``entries``, sorted, excluding the mask group."""
    return sorted(k for k in entries if isinstance(k, int) and k != MASK_ID)


def _members(entries, cluster_id):
    """Normalized membership of ``cluster_id``'s group.

    Returns a sorted list of ids that are actually present in ``entries``,
    always including ``cluster_id`` itself. Stale ids -- a link list left over
    from a run with more clusters, or one naming the mask group -- are dropped
    rather than raising, because ``cluster_group_changed`` rebuilds the int
    keys on every run and nothing guarantees the lists were cleaned up.
    """
    valid = set(_cluster_ids(entries))
    if cluster_id not in valid:
        return []

    raw = entries[cluster_id].get('link') or []
    try:
        linked = {int(i) for i in raw}
    except (TypeError, ValueError):
        linked = set()

    return sorted((linked & valid) | {cluster_id})


def cluster_groups(entries):
    """Group the clusters in ``entries``.

    Parameters
    ----------
    entries : dict
        ``AppData.cluster_dict[method]``. Only int keys other than
        :data:`MASK_ID` are considered, so the method's settings (``'seed'``,
        ``'n_clusters'``, ``'selected_clusters'``, ...) are ignored.

    Returns
    -------
    list of (int, list of int)
        ``(leader_id, member_ids)`` per group, ordered by leader id. An
        unlinked cluster appears as a group of one, so callers can iterate
        regions without special-casing it -- the same shape
        ``PolygonManager.groups`` returns.
    """
    seen = set()
    groups = []
    for cluster_id in _cluster_ids(entries):
        if cluster_id in seen:
            continue
        members = _members(entries, cluster_id)
        seen.update(members)
        groups.append((min(members), members))
    return groups


def group_of(entries, cluster_id):
    """Leader id of ``cluster_id``'s group, or ``None`` when it is unlinked."""
    members = _members(entries, cluster_id)
    if len(members) < 2:
        return None
    return min(members)


def group_index(entries, cluster_id):
    """1-based position of ``cluster_id``'s group, or ``None`` if unlinked.

    What the table's *Link* column displays (``Group 1``, ``Group 2``, ...).
    Counts only real groups, so the numbering does not jump over the singletons
    between them.
    """
    leader = group_of(entries, cluster_id)
    if leader is None:
        return None

    n = 0
    for gid, members in cluster_groups(entries):
        if len(members) < 2:
            continue
        n += 1
        if gid == leader:
            return n
    return None


def expand_to_groups(entries, ids):
    """Grow a selection so no group is only partly selected.

    Checking one member of a group means selecting the whole class -- for the
    cluster mask, for linking, and for *Create Region*.

    Returns
    -------
    list of int
        Sorted ids, including every member of every group touched by ``ids``.
    """
    out = set()
    for cluster_id in ids:
        out.update(_members(entries, int(cluster_id)))
    return sorted(out)


def link_clusters(entries, ids):
    """Link the given clusters into one group.

    Merges **whole** groups: selecting one member of an existing group pulls
    that group in entirely, so linking can never leave a group split across two
    others. The lowest id becomes the leader and its color is propagated to
    every member, which is what makes a linked class read as one color on the
    map.

    Parameters
    ----------
    entries : dict
        ``AppData.cluster_dict[method]``; modified in place.
    ids : iterable of int
        Cluster ids to link.

    Returns
    -------
    int or None
        The new group's leader id, or ``None`` if there was nothing to do
        (fewer than two distinct clusters resolve, or they are already exactly
        one group).
    """
    members = set(expand_to_groups(entries, ids))
    if len(members) < 2:
        return None

    # Already exactly this group -- nothing to change.
    leader = min(members)
    if set(_members(entries, leader)) == members:
        return None

    ordered = sorted(members)
    color = entries[leader].get('color')
    for cluster_id in ordered:
        entries[cluster_id]['link'] = list(ordered)
        if color is not None:
            entries[cluster_id]['color'] = color

    return leader


def unlink_clusters(entries, ids):
    """Remove the given clusters from their groups.

    A group left with a single member is dissolved -- a group of one is just an
    unlinked cluster, and leaving it linked would keep it out of the *Link*
    column's numbering for no reason.

    Parameters
    ----------
    entries : dict
        ``AppData.cluster_dict[method]``; modified in place.
    ids : iterable of int
        Cluster ids to unlink.

    Returns
    -------
    bool
        True if anything changed.
    """
    valid = set(_cluster_ids(entries))
    targets = {int(i) for i in ids} & valid
    if not targets:
        return False

    touched = set()
    changed = False
    for cluster_id in targets:
        members = _members(entries, cluster_id)
        if len(members) < 2:
            continue
        touched.update(members)
        changed = True

    if not changed:
        return False

    for cluster_id in touched:
        remaining = [i for i in _members(entries, cluster_id) if i not in targets]
        if cluster_id in targets or len(remaining) < 2:
            entries[cluster_id]['link'] = []
        else:
            entries[cluster_id]['link'] = list(remaining)

    return True


def group_colors_and_labels(entries):
    """Per-cluster display color and label, with members showing their leader's.

    Used by ``StyleToolbox.get_cluster_colormap`` so that a linked class draws
    in one color under one name everywhere -- map, legend, scatter -- without
    any plot having to know about grouping.

    Returns
    -------
    dict
        ``{cluster_id: (color, label)}`` for every real cluster id.
    """
    out = {}
    for leader, members in cluster_groups(entries):
        color = entries[leader].get('color')
        label = entries[leader].get('name')
        for cluster_id in members:
            out[cluster_id] = (color, label)
    return out
