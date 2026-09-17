"""Tests for cluster grouping (``src/data/cluster_groups.py``).

Linking merges clusters that are really one mineral into a single class. The
guarantees that matter: it never re-clusters anything, merging touches whole
groups rather than splitting them, and a link list left behind by an earlier
run with more clusters does not blow up the table.

Qt-free -- these run against the plain dict ``AppData.cluster_group_changed``
builds.
"""
import pytest

from src.data.cluster_groups import (
    cluster_groups,
    expand_to_groups,
    group_colors_and_labels,
    group_index,
    group_of,
    link_clusters,
    unlink_clusters,
)


def entries(n=4, with_mask=False):
    """The int-keyed part of ``cluster_dict[method]``, plus its settings keys."""
    d = {
        'n_clusters': n,
        'seed': 23,
        'selected_clusters': [],
    }
    for i in range(n):
        d[i] = {'name': f'Cluster {i + 1}', 'link': [], 'color': f'#00000{i}'}
    if with_mask:
        d[99] = {'name': 'Mask', 'link': [], 'color': '#808080'}
    return d


def test_unlinked_clusters_are_groups_of_one():
    """Callers iterate regions without special-casing an unlinked cluster."""
    d = entries(3)

    assert cluster_groups(d) == [(0, [0]), (1, [1]), (2, [2])]
    assert group_of(d, 1) is None
    assert group_index(d, 1) is None


def test_settings_and_mask_keys_are_not_clusters():
    """'seed'/'n_clusters' are str keys; 99 is the masked/noise placeholder."""
    d = entries(2, with_mask=True)

    assert cluster_groups(d) == [(0, [0]), (1, [1])]


def test_linking_makes_one_group_led_by_the_lowest_id():
    d = entries(4)

    leader = link_clusters(d, [2, 0])

    assert leader == 0
    assert cluster_groups(d) == [(0, [0, 2]), (1, [1]), (3, [3])]
    assert group_of(d, 2) == 0
    assert d[0]['link'] == [0, 2] and d[2]['link'] == [0, 2]


def test_members_take_the_leaders_color():
    """A linked class has to read as one color on the map."""
    d = entries(3)

    link_clusters(d, [1, 2])

    assert d[2]['color'] == d[1]['color'] == '#000001'
    # names are left alone -- ClusterTab rejects duplicate cluster names
    assert d[2]['name'] == 'Cluster 3'


def test_linking_merges_whole_groups_not_just_the_named_ids():
    """Touching one member pulls its group in, so a group is never split."""
    d = entries(5)
    link_clusters(d, [0, 1])
    link_clusters(d, [3, 4])

    leader = link_clusters(d, [1, 4])

    assert leader == 0
    assert cluster_groups(d) == [(0, [0, 1, 3, 4]), (2, [2])]


def test_relinking_the_same_group_is_a_no_op():
    d = entries(3)
    link_clusters(d, [0, 1])

    assert link_clusters(d, [0, 1]) is None


def test_linking_fewer_than_two_clusters_does_nothing():
    d = entries(3)

    assert link_clusters(d, [1]) is None
    assert link_clusters(d, []) is None
    assert cluster_groups(d) == [(0, [0]), (1, [1]), (2, [2])]


def test_unlinking_removes_only_the_named_clusters():
    d = entries(4)
    link_clusters(d, [0, 1, 2])

    assert unlink_clusters(d, [2]) is True
    assert cluster_groups(d) == [(0, [0, 1]), (2, [2]), (3, [3])]
    assert d[2]['link'] == []


def test_unlinking_dissolves_a_group_left_with_one_member():
    """A group of one is just an unlinked cluster."""
    d = entries(3)
    link_clusters(d, [0, 1])

    unlink_clusters(d, [0])

    assert d[1]['link'] == []
    assert group_of(d, 1) is None


def test_unlinking_an_unlinked_cluster_reports_no_change():
    d = entries(3)

    assert unlink_clusters(d, [1]) is False
    assert unlink_clusters(d, [99]) is False


def test_group_index_numbers_only_real_groups():
    """The Link column shows 'Group 1', 'Group 2' with no gaps for singletons."""
    d = entries(6)
    link_clusters(d, [0, 1])
    link_clusters(d, [3, 5])

    assert group_index(d, 0) == group_index(d, 1) == 1
    assert group_index(d, 3) == group_index(d, 5) == 2
    assert group_index(d, 2) is None and group_index(d, 4) is None


def test_expand_to_groups_grows_a_partial_selection():
    """Checking one member of a class selects the class."""
    d = entries(5)
    link_clusters(d, [1, 3])

    assert expand_to_groups(d, [1]) == [1, 3]
    assert expand_to_groups(d, [0, 3]) == [0, 1, 3]
    assert expand_to_groups(d, []) == []


@pytest.mark.parametrize('stale', [[0, 7], [0, 99], 'nonsense', None, [0, 'x']])
def test_stale_or_malformed_link_lists_normalize_instead_of_raising(stale):
    """Re-running clustering rebuilds the int keys; nothing cleans old lists.

    A link list naming a cluster that no longer exists (or the mask group, or
    junk) must degrade to "unlinked", not break the cluster table.
    """
    d = entries(2)
    d[0]['link'] = stale

    assert cluster_groups(d) == [(0, [0]), (1, [1])]
    assert group_of(d, 0) is None


def test_a_link_list_missing_its_own_id_still_includes_itself():
    d = entries(3)
    d[0]['link'] = [1]

    assert group_of(d, 0) == 0
    assert cluster_groups(d) == [(0, [0, 1]), (2, [2])]


def test_group_colors_and_labels_gives_members_their_leaders_identity():
    """One legend entry per class falls out of this mapping."""
    d = entries(3)
    d[0]['name'] = 'Plagioclase'
    link_clusters(d, [0, 2])

    mapping = group_colors_and_labels(d)

    assert mapping[0] == mapping[2] == ('#000000', 'Plagioclase')
    assert mapping[1] == ('#000001', 'Cluster 2')
