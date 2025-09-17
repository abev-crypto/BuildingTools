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


def mirror_selected_instances(axis="x"):
    """Mirror selected instances.

    This first tries Maya's :command:`CreateMirrorInstance` command.  If that
    runtime command is not available a scripted fallback is used that creates a
    mirrored instance by instancing the selection and flipping the requested
    scale axis.  When an already-instanced transform is selected, the existing
    instance is mirrored in place instead of creating an extra copy.

    Args:
        axis (str): Axis to mirror across. Only ``"x"``, ``"y"`` and ``"z"`` are
            supported. Defaults to ``"x"``.

    Returns:
        list[str]: Names of the mirrored (or newly created) transforms.
    """

    selection = cmds.ls(sl=True, type="transform", long=True) or []
    if not selection:
        cmds.warning(u"ミラーするインスタンスを選択してください。")
        return []

    created = _mirror_via_runtime(selection)
    if created is None:
        created = _mirror_instances_manually(selection, axis=axis)

    if created:
        try:
            cmds.select(created, r=True)
        except RuntimeError:
            pass
    else:
        cmds.warning(u"ミラーの結果として新しいインスタンスは作成されませんでした。")

    return created


def _mirror_via_runtime(selection):
    """Try to mirror using Maya's CreateMirrorInstance command.

    Args:
        selection (list[str]): Original transform selection.

    Returns:
        list[str] | None: Returns ``None`` when the runtime command is not
        available or fails. Otherwise returns the list of nodes reported by the
        command (which may be empty).
    """

    command = getattr(cmds, "CreateMirrorInstance", None)
    if not callable(command):
        return None

    before_nodes = set(cmds.ls(type="transform", long=True) or [])
    try:
        command()
    except RuntimeError as exc:
        cmds.warning(u"CreateMirrorInstance の実行に失敗したため、スクリプトによるミラー処理に切り替えます: %s" % exc)
        return None
    except Exception as exc:  # pylint: disable=broad-except
        cmds.warning(u"CreateMirrorInstance の呼び出しに失敗したため、スクリプトによるミラー処理に切り替えます: %s" % exc)
        return None

    after_nodes = set(cmds.ls(type="transform", long=True) or [])
    created = [node for node in after_nodes - before_nodes if cmds.objExists(node)]

    if not created:
        new_selection = cmds.ls(sl=True, type="transform", long=True) or []
        created = [node for node in new_selection if node not in selection and cmds.objExists(node)]

    return created


def _mirror_instances_manually(selection, axis="x"):
    """Mirror instances without relying on Maya's runtime command."""

    axis_key = _normalize_axis(axis)
    selection_set = set(selection)
    processed = set()
    mirrored_nodes = []

    for node in selection:
        if node in processed or not cmds.objExists(node):
            continue

        shared_transforms = _transforms_sharing_shapes(node)
        shared_transforms = [n for n in shared_transforms if cmds.objExists(n)]

        if shared_transforms and len(shared_transforms) > 1:
            targets = [n for n in shared_transforms if n in selection_set]
            if targets:
                for target in targets:
                    if target in processed or not cmds.objExists(target):
                        continue
                    if _mirror_existing_transform(target, axis_key):
                        mirrored_nodes.append(target)
                    processed.add(target)
                if node not in processed:
                    processed.add(node)
                continue

        new_node = _create_mirrored_instance(node, axis_key)
        if new_node:
            mirrored_nodes.append(new_node)
        processed.add(node)

    return mirrored_nodes


def _normalize_axis(axis):
    """Return a valid axis label for mirroring."""

    axis = (axis or "x").lower()
    return axis if axis in ("x", "y", "z") else "x"


def _transforms_sharing_shapes(node):
    """Return transforms that share shapes with *node*."""

    transforms = {node}
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
    for shape in shapes:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        transforms.update(parents)
    return list(transforms)


def _create_mirrored_instance(node, axis):
    """Instance *node* and apply a mirrored scale."""

    try:
        result = cmds.instance(node, smartTransform=False)
    except RuntimeError as exc:
        cmds.warning(u"%s のインスタンス作成に失敗しました: %s" % (node, exc))
        return None

    if not result:
        return None

    instance_node = result[0]
    parent = cmds.listRelatives(node, parent=True, fullPath=True)

    if parent:
        try:
            instance_node = cmds.parent(instance_node, parent[0])[0]
        except RuntimeError:
            pass

    try:
        matrix = cmds.xform(node, q=True, ws=True, matrix=True)
        cmds.xform(instance_node, ws=True, matrix=matrix)
    except RuntimeError:
        pass

    short_name = node.split("|")[-1]
    try:
        instance_node = cmds.rename(instance_node, f"{short_name}_mirror#")
    except RuntimeError:
        pass

    _apply_negative_scale(instance_node, axis, reference=node)

    return instance_node


def _mirror_existing_transform(node, axis):
    """Mirror an already existing instance by flipping its scale."""

    if not cmds.objExists(node):
        return False

    return _apply_negative_scale(node, axis)


def _apply_negative_scale(node, axis, reference=None):
    """Set the scale on *node* so that the *axis* component is negative."""

    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    attr_names = [".scaleX", ".scaleY", ".scaleZ"]

    source_node = reference if reference and cmds.objExists(reference) else node

    values = []
    for attr in attr_names:
        try:
            values.append(cmds.getAttr(source_node + attr))
        except RuntimeError:
            values.append(1.0)

    if not values:
        return False

    target_value = -abs(values[axis_index]) if values[axis_index] is not None else -1.0

    # Apply all three axes so that non-mirrored axes match the source.
    success = True
    for idx, attr in enumerate(attr_names):
        if not cmds.objExists(node + attr):
            continue
        value = values[idx] if values[idx] is not None else 1.0
        if idx == axis_index:
            value = target_value
        try:
            cmds.setAttr(node + attr, value)
        except RuntimeError as exc:
            cmds.warning(u"%s のスケール設定に失敗しました: %s" % (node, exc))
            success = False
            break

    return success


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

def sort_selected_by_position(nodes=None, axis="auto", descending=False, space="world"):
    """Sort selected transforms in the Outliner based on their position.

    Args:
        nodes (list[str] | None): Target transforms. Defaults to current selection.
        axis (str): Axis to sort by. ``"x"``, ``"y"``, ``"z"`` or ``"auto"``.
            ``"auto"`` picks the axis with the largest positional spread per parent.
        descending (bool): If True, reverse the sort order.
        space (str): Coordinate space used to query positions, ``"world"`` or ``"local"``.

    Returns:
        list[str]: Nodes reordered in their new Outliner sequence.
    """

    axis = (axis or "auto").lower()
    axis_map = {"x": 0, "y": 1, "z": 2}
    if axis not in axis_map and axis != "auto":
        cmds.error(u"axis には auto / x / y / z のいずれかを指定してください。")
        return []

    if isinstance(space, str):
        space_normalized = space.strip().lower() or "world"
    else:
        space_normalized = "world"

    if space_normalized not in {"world", "local"}:
        cmds.error(u"space には world / local のいずれかを指定してください。")
        return []

    use_world_space = space_normalized == "world"

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
        incomplete_positions = False
        for node in group:
            pos = cmds.xform(node, q=True, ws=use_world_space, t=True)
            if pos is None or len(pos) < 3:
                cmds.warning(u"%s の位置を取得できませんでした。" % node)
                incomplete_positions = True
                break
            cleaned = [float(pos[idx]) for idx in range(3)]
            data.append((node, cleaned))

        if incomplete_positions:
            sorted_nodes = sorted(group)
        else:
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
    "make_unique_combine_merge",
    "sort_selected_by_position",
]
