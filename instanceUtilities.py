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


__all__ = ["replace_with_first_instance", "make_selected_unique"]
