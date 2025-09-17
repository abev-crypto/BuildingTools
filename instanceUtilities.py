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


def _filter_mesh_transforms(nodes):
    """Return only transform nodes that have a mesh shape."""

    mesh_nodes = []
    skipped = []
    for node in nodes:
        if not cmds.objExists(node):
            continue
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
        has_mesh = any(cmds.nodeType(shape) == "mesh" for shape in shapes)
        if has_mesh:
            mesh_nodes.append(node)
        else:
            skipped.append(node)
    return mesh_nodes, skipped


def make_unique_combine_merge(nodes=None, merge_distance=0.001, delete_history=True):
    """Make instances unique, combine them, merge vertices, and delete history."""

    nodes = nodes or cmds.ls(sl=True, type="transform", long=True) or []
    if not nodes:
        cmds.warning(u"インスタンスを解除する対象を選択してください。")
        return None

    mesh_nodes, skipped = _filter_mesh_transforms(nodes)
    if not mesh_nodes:
        cmds.warning(u"ポリゴンメッシュを持つノードが見つかりませんでした。")
        return None

    unique_nodes = make_selected_unique(nodes=mesh_nodes)
    if not unique_nodes:
        return None

    unique_nodes = [n for n in unique_nodes if cmds.objExists(n)]
    if not unique_nodes:
        return None

    source_count = len(unique_nodes)
    base_name = unique_nodes[0].split("|")[-1]
    combined_node = unique_nodes[0]

    if source_count > 1:
        try:
            result = cmds.polyUnite(
                unique_nodes,
                ch=False,
                mergeUVSets=True,
                name=f"{base_name}_combined#",
            )
        except RuntimeError as exc:
            cmds.warning(u"Combine に失敗しました: %s" % exc)
            return None

        combined_node = result[0] if isinstance(result, (list, tuple)) else result
        try:
            cmds.delete(unique_nodes)
        except RuntimeError:
            pass

    try:
        merge_distance_value = float(merge_distance)
    except (TypeError, ValueError):
        merge_distance_value = 0.0

    if merge_distance_value > 0 and cmds.objExists(combined_node):
        try:
            cmds.polyMergeVertex(
                combined_node,
                d=merge_distance_value,
                am=True,
                ch=False,
            )
        except RuntimeError as exc:
            cmds.warning(u"頂点マージに失敗しました: %s" % exc)

    if delete_history and cmds.objExists(combined_node):
        cmds.delete(combined_node, ch=True)

    if skipped:
        short_names = ", ".join(node.split("|")[-1] for node in skipped)
        cmds.warning(u"メッシュを持たないノードをスキップしました: %s" % short_names)

    if cmds.objExists(combined_node):
        cmds.select(combined_node, r=True)

    return combined_node, source_count


__all__ = [
    "replace_with_first_instance",
    "make_selected_unique",
    "make_unique_combine_merge",
]
