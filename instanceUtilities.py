# -*- coding: utf-8 -*-
"""Utility functions for working with instances."""

import maya.cmds as cmds


def replace_with_first_instance(template=None, targets=None):
    """Replace targets with instances of the template transform.

    Args:
        template (str | None): Transform node to instance. Defaults to first selection.
        targets (list[str] | None): Target transforms to replace. Defaults to remaining selection.

    Returns:
        list[str]: Names of created instances.
    """
    sel = cmds.ls(sl=True, type="transform", long=True) or []
    if template is None or targets is None:
        if len(sel) < 2:
            cmds.error(u"テンプレートと置換対象を選択してください。（最初にテンプレート）")
            return []
        template = template or sel[0]
        targets = targets or sel[1:]

    if not cmds.objExists(template):
        cmds.error(u"テンプレートが存在しません。")
        return []

    created = []
    for target in targets:
        if target == template or not cmds.objExists(target):
            continue

        parent = cmds.listRelatives(target, parent=True, fullPath=True)
        matrix = cmds.xform(target, q=True, ws=True, m=True)
        short_name = target.split("|")[-1]

        inst = cmds.instance(template, smartTransform=False)[0]
        if parent:
            inst = cmds.parent(inst, parent[0])[0]

        cmds.xform(inst, ws=True, m=matrix)

        cmds.delete(target)
        inst = cmds.rename(inst, short_name)
        created.append(inst)

    if created:
        cmds.select(created, r=True)
    else:
        cmds.warning(u"置換されたオブジェクトがありませんでした。")

    return created


def make_selected_unique(nodes=None):
    """Convert selected instances to unique copies by duplicating them."""
    nodes = nodes or cmds.ls(sl=True, type="transform", long=True) or []
    if not nodes:
        cmds.warning(u"インスタンスを解除する対象を選択してください。")
        return []

    unique_nodes = []
    for node in nodes:
        if not cmds.objExists(node):
            continue

        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        matrix = cmds.xform(node, q=True, ws=True, m=True)
        short_name = node.split("|")[-1]

        duplicate = cmds.duplicate(node, name=f"{short_name}_unique#", rr=True, rc=True)[0]
        if parent:
            duplicate = cmds.parent(duplicate, parent[0])[0]

        cmds.xform(duplicate, ws=True, m=matrix)

        cmds.delete(node)
        duplicate = cmds.rename(duplicate, short_name)
        unique_nodes.append(duplicate)

    if unique_nodes:
        cmds.select(unique_nodes, r=True)

    return unique_nodes


def sort_selected_by_position(nodes=None, axis="auto", descending=False):
    """Sort selected transforms in the Outliner based on their world position.

    Args:
        nodes (list[str] | None): Target transforms. Defaults to current selection.
        axis (str): Axis to sort by. ``"x"``, ``"y"``, ``"z"`` or ``"auto"``.
            ``"auto"`` picks the axis with the largest positional spread per parent.
        descending (bool): If True, reverse the sort order.

    Returns:
        list[str]: Nodes reordered in their new Outliner sequence.
    """

    axis = (axis or "auto").lower()
    axis_map = {"x": 0, "y": 1, "z": 2}
    if axis not in axis_map and axis != "auto":
        cmds.error(u"axis には auto / x / y / z のいずれかを指定してください。")
        return []

    nodes = nodes or cmds.ls(sl=True, type="transform", long=True) or []
    nodes = [node for node in nodes if cmds.objExists(node)]
    if len(nodes) < 2:
        if not nodes:
            cmds.warning(u"並べ替えるオブジェクトを選択してください。")
        else:
            cmds.warning(u"並べ替えには 2 つ以上のオブジェクトを選択してください。")
        return []

    parent_groups = {}
    parent_order = []
    for node in nodes:
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        parent = parent[0] if parent else None
        if parent not in parent_groups:
            parent_groups[parent] = []
            parent_order.append(parent)
        parent_groups[parent].append(node)

    ordered_selection = []
    processed_count = 0
    epsilon = 1e-6

    def _choose_axis(data):
        if axis != "auto":
            return axis_map[axis]
        ranges = []
        for idx in range(3):
            coords = [pos[idx] for _, pos in data]
            if coords:
                axis_range = max(coords) - min(coords)
            else:
                axis_range = 0.0
            ranges.append(axis_range)
        max_range = max(ranges) if ranges else 0.0
        if max_range <= epsilon:
            return None
        return ranges.index(max_range)

    for parent in parent_order:
        group = [node for node in parent_groups.get(parent, []) if cmds.objExists(node)]
        if len(group) < 2:
            ordered_selection.extend(group)
            continue

        data = []
        for node in group:
            pos = cmds.xform(node, q=True, ws=True, t=True)
            data.append((node, pos))

        axis_index = _choose_axis(data)
        if axis_index is None:
            sorted_nodes = sorted(group)
        else:
            secondary_axes = [idx for idx in range(3) if idx != axis_index]

            def _sort_key(item):
                pos = item[1]
                key_values = [round(pos[axis_index], 6)]
                key_values.extend(round(pos[idx], 6) for idx in secondary_axes)
                key_values.append(item[0])
                return tuple(key_values)

            sorted_nodes = [item[0] for item in sorted(data, key=_sort_key)]

        if descending:
            sorted_nodes.reverse()

        if parent:
            children = cmds.listRelatives(parent, children=True, type="transform", fullPath=True) or []
        else:
            children = cmds.ls(assemblies=True, long=True) or []

        selected_set = set(group)
        queue = list(sorted_nodes)
        final_order = []
        queue_index = 0
        for child in children:
            if child in selected_set:
                if queue_index < len(queue):
                    final_order.append(queue[queue_index])
                    queue_index += 1
            else:
                final_order.append(child)
        if queue_index < len(queue):
            # Append any nodes that lost their parent between evaluation and reorder.
            final_order.extend(queue[queue_index:])

        if not final_order:
            continue

        if final_order == children:
            ordered_selection.extend(sorted_nodes)
            processed_count += len(sorted_nodes)
            continue

        try:
            for child in reversed(final_order):
                cmds.reorder(child, front=True)
        except RuntimeError:
            label = parent or u"ルート"
            cmds.warning(u"%s 配下の並べ替えに失敗しました。" % label)
            ordered_selection.extend(group)
            continue

        ordered_selection.extend(sorted_nodes)
        processed_count += len(sorted_nodes)

    if processed_count:
        cmds.select(ordered_selection, r=True)
        return ordered_selection

    # Nothing was reordered (e.g. each group had 1 child)
    cmds.warning(u"並べ替え可能なオブジェクトが見つかりませんでした。")
    return []


__all__ = [
    "replace_with_first_instance",
    "make_selected_unique",
    "sort_selected_by_position",
]
