# -*- coding: utf-8 -*-
import math
import maya.cmds as cmds

_AXIS_INDICES = {"x": 0, "y": 1, "z": 2}


def _compute_bbox_axis_info(node, axis):
    """Return spacing and direction data for ``node`` along ``axis``.

    Args:
        node (str): Transform to sample.
        axis (str): Local axis name (``"x"``, ``"y"``, ``"z"``).

    Returns:
        dict|None: ``{"spacing": float, "direction": tuple[float, float, float]}``
            in world-space. ``None`` when the bounding box information cannot be
            obtained.
    """

    if not cmds.objExists(node):
        return None

    axis = (axis or "x").lower()
    if axis not in _AXIS_INDICES:
        axis = "x"

    try:
        bbox = cmds.xform(node, q=True, bb=True, objectSpace=True)
    except RuntimeError:
        return None

    if not bbox or len(bbox) < 6:
        return None

    axis_index = _AXIS_INDICES[axis]
    min_value = bbox[axis_index]
    max_value = bbox[axis_index + 3]
    base_size = abs(max_value - min_value)
    if base_size <= 1e-6:
        return {"spacing": 0.0, "direction": None}

    try:
        matrix = cmds.xform(node, q=True, ws=True, matrix=True)
    except RuntimeError:
        return None

    axis_vectors = {
        "x": (matrix[0], matrix[4], matrix[8]),
        "y": (matrix[1], matrix[5], matrix[9]),
        "z": (matrix[2], matrix[6], matrix[10]),
    }
    vec = axis_vectors[axis]
    length = math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])
    if length <= 1e-6:
        return {"spacing": 0.0, "direction": None}

    spacing = base_size * length
    direction = (vec[0] / length, vec[1] / length, vec[2] / length)
    return {"spacing": spacing, "direction": direction}


def _compute_bbox_spacing(node, axis):
    """Return the world-space size of ``node`` along the given local ``axis``."""

    info = _compute_bbox_axis_info(node, axis)
    if not info:
        return None
    return info["spacing"]


def instance_child_between_parent(
    parent=None,
    child=None,
    count=5,
    include_end=False,
    orient="none",   # "none" | "aim" | "copy"
    parent_instances_to_parent=True,
    group_name=None,
    spacing=None,
    use_bbox_spacing=False,
    bbox_axis="x",
    alternate_scale=False,
    alternate_scale_axis="x",
    bbox_count_mode=False,
):
    """
    親(始点)と子(終点)の間に、子をインスタンス化して等間隔配置する。

    Args:
        parent (str): 親トランスフォーム。未指定なら選択1つ目。
        child (str):  子トランスフォーム（終点テンプレート）。未指定なら選択2つ目。
        count (int):  作成するインスタンスの数（間に置く個数）。>=1
        include_end (bool): Trueなら終点位置にもインスタンスを置く。
        orient (str): 配向の方法
            - "none": 回転は子の元の回転を維持
            - "aim":  各インスタンスを終点方向に向ける
            - "copy": 子のワールド回転をそのままコピー
        parent_instances_to_parent (bool):
            Trueならインスタンスを親(始点)の子にする。Falseならワールド直下。
        group_name (str|None):
            指定時は空グループを作成し、生成したインスタンスを全てその子にする。
            文字列が空の場合は "instanceGroup#" を利用。
            parent_instances_to_parent が True の場合はグループを parent の子にします。
        spacing (float|None): 指定した場合、親子間の距離に応じて等間隔配置する際の間隔。
        use_bbox_spacing (bool): True の場合、子のバウンディングボックスサイズを元に間隔を決定。
        bbox_axis (str): use_bbox_spacing=True のときに参照するローカル軸（"x"/"y"/"z"）。
        alternate_scale (bool): True の場合、インスタンスのスケールを交互に反転させる。
        alternate_scale_axis (str): スケールを反転させる軸（"x"/"y"/"z"）。
        bbox_count_mode (bool): True の場合、use_bbox_spacing=True と組み合わせて
            親を指定せずにバウンディングボックス幅を使った個数指定モードで配置する。
            parent を省略した場合も自動的にこのモードになります。
    Returns:
        list[str]: 作成したインスタンスノード名のリスト
    """
    sel = cmds.ls(sl=True, type="transform", long=True) or []
    selection_parent = sel[0] if len(sel) >= 1 else None
    selection_child = sel[1] if len(sel) >= 2 else None

    if child is None:
        if selection_child is not None:
            child = selection_child
        elif selection_parent is not None:
            child = selection_parent

    if parent is None and selection_parent is not None and selection_parent != child:
        parent = selection_parent

    if child is None or not cmds.objExists(child):
        cmds.error(u"指定した child が存在しません。")

    if parent is not None and not cmds.objExists(parent):
        cmds.error(u"指定した parent が存在しません。")

    count_mode = bool(use_bbox_spacing and (bbox_count_mode or parent is None))

    if not count_mode and parent is None:
        cmds.error(u"親→子の順で2つ選択するか、引数で parent と child を指定してください。")

    c_pos = cmds.xform(child, q=True, ws=True, t=True)
    p_pos = None
    if not count_mode:
        p_pos = cmds.xform(parent, q=True, ws=True, t=True)

    child_parent = None
    parents = cmds.listRelatives(child, parent=True, f=True) or []
    if parents:
        child_parent = parents[0]

    parent_target = None
    if parent_instances_to_parent:
        if count_mode:
            if parent and cmds.objExists(parent):
                parent_target = parent
            elif child_parent and cmds.objExists(child_parent):
                parent_target = child_parent
        else:
            if parent and cmds.objExists(parent):
                parent_target = parent

    group_node = None
    if group_name is not None:
        name = (group_name or "").strip() or "instanceGroup#"
        group_node = cmds.group(em=True, name=name)
        if parent_target:
            group_node = cmds.parent(group_node, parent_target)[0]

    alternate_axis = None
    base_scale_values = None
    if alternate_scale:
        alternate_axis = (alternate_scale_axis or "x").lower()
        if alternate_axis not in _AXIS_INDICES:
            alternate_axis = "x"
        try:
            base_scale_values = cmds.xform(child, q=True, r=True, s=True)
        except RuntimeError:
            base_scale_values = None
        if not base_scale_values or len(base_scale_values) < 3:
            base_scale_values = [1.0, 1.0, 1.0]
        else:
            base_scale_values = list(base_scale_values[:3])

    if count_mode:
        info = _compute_bbox_axis_info(child, bbox_axis)
        if not info:
            cmds.warning(u"バウンディングボックスの取得に失敗しました。距離指定で再試行してください。")
            return []
        spacing_value = info["spacing"]
        direction = info["direction"]
        if spacing_value is None or spacing_value <= 1e-6 or not direction:
            cmds.warning(u"選択したローカル軸でのサイズがゼロのため、配置できません。")
            return []
        try:
            count_value = int(count)
        except (TypeError, ValueError):
            cmds.warning(u"count は整数を指定してください。何も作成しません。")
            return []
        if count_value < 0:
            count_value = 0
        multipliers = list(range(1, count_value + 1))
        if include_end:
            multipliers.append(count_value + 1)
        if not multipliers:
            cmds.warning(u"count は 1 以上にしてください。何も作成しません。")
            return []

        created = []
        aim_helper = None
        try:
            for index, step in enumerate(multipliers):
                pos = [
                    c_pos[i] + direction[i] * spacing_value * step
                    for i in range(3)
                ]
                inst = cmds.instance(child, smartTransform=False)[0]

                if group_node:
                    inst = cmds.parent(inst, group_node)[0]
                elif parent_instances_to_parent and parent_target:
                    inst = cmds.parent(inst, parent_target)[0]

                cmds.xform(inst, ws=True, t=pos)

                if orient == "copy":
                    rot = cmds.xform(child, q=True, ws=True, ro=True)
                    cmds.xform(inst, ws=True, ro=rot)
                elif orient == "aim":
                    if aim_helper is None:
                        aim_helper = cmds.spaceLocator()[0]
                    target_pos = [pos[i] + direction[i] for i in range(3)]
                    cmds.xform(aim_helper, ws=True, t=target_pos)
                    ac = cmds.aimConstraint(
                        aim_helper,
                        inst,
                        aimVector=(0, 0, 1),
                        upVector=(0, 1, 0),
                        worldUpType="scene",
                    )[0]
                    cmds.delete(ac)

                if alternate_axis and base_scale_values:
                    axis_index = _AXIS_INDICES[alternate_axis]
                    flip = -1 if (index % 2 == 1) else 1
                    scale_values = list(base_scale_values)
                    scale_values[axis_index] = base_scale_values[axis_index] * flip
                    axis_attrs = ["scaleX", "scaleY", "scaleZ"]
                    for attr_index, attr_name in enumerate(axis_attrs):
                        value = scale_values[attr_index]
                        try:
                            cmds.setAttr(f"{inst}.{attr_name}", value)
                        except RuntimeError:
                            pass

                created.append(inst)
        finally:
            if aim_helper and cmds.objExists(aim_helper):
                cmds.delete(aim_helper)

        return created

    spacing_value = None
    use_spacing = False
    if use_bbox_spacing:
        spacing_value = _compute_bbox_spacing(child, bbox_axis)
        if spacing_value is None:
            cmds.warning(u"バウンディングボックスの取得に失敗しました。距離指定で再試行してください。")
            return []
        if spacing_value <= 1e-6:
            cmds.warning(u"選択したローカル軸でのサイズがゼロのため、配置できません。")
            return []
        use_spacing = True
    elif spacing is not None:
        try:
            spacing_value = float(spacing)
        except (TypeError, ValueError):
            cmds.warning(u"距離指定は数値を入力してください。何も作成しません。")
            return []
        if spacing_value <= 0:
            cmds.warning(u"距離指定は正の値にしてください。何も作成しません。")
            return []
        use_spacing = True

    steps = []
    if use_spacing:
        vec = [c_pos[i] - p_pos[i] for i in range(3)]
        total_dist = math.sqrt(sum(v * v for v in vec))
        eps = 1e-6
        if total_dist <= eps:
            if include_end:
                steps.append(1.0)
            else:
                cmds.warning(u"親と子の位置が同じため、距離指定では配置できません。")
                return []
        else:
            current = spacing_value
            while current < total_dist - eps:
                steps.append(current / total_dist)
                current += spacing_value
            if include_end:
                steps.append(1.0)
    else:
        if count < 1:
            cmds.warning(u"count は 1 以上にしてください。何も作成しません。")
            return []

        steps = [float(i)/(count+1) for i in range(1, count+1)]
        if include_end:
            steps.append(1.0)

    if not steps:
        cmds.warning(u"指定条件では配置するインスタンスがありません。")
        return []

    created = []
    for index, t in enumerate(steps):
        pos = [p_pos[i] + (c_pos[i] - p_pos[i]) * t for i in range(3)]
        inst = cmds.instance(child, smartTransform=False)[0]

        if group_node:
            inst = cmds.parent(inst, group_node)[0]
        elif parent_instances_to_parent and parent_target:
            inst = cmds.parent(inst, parent_target)[0]

        cmds.xform(inst, ws=True, t=pos)

        if orient == "copy":
            rot = cmds.xform(child, q=True, ws=True, ro=True)
            cmds.xform(inst, ws=True, ro=rot)
        elif orient == "aim":
            ac = cmds.aimConstraint(
                child,
                inst,
                aimVector=(0, 0, 1),
                upVector=(0, 1, 0),
                worldUpType="scene",
            )[0]
            cmds.delete(ac)

        if alternate_axis and base_scale_values:
            axis_index = _AXIS_INDICES[alternate_axis]
            flip = -1 if (index % 2 == 1) else 1
            scale_values = list(base_scale_values)
            scale_values[axis_index] = base_scale_values[axis_index] * flip
            axis_attrs = ["scaleX", "scaleY", "scaleZ"]
            for attr_index, attr_name in enumerate(axis_attrs):
                value = scale_values[attr_index]
                try:
                    cmds.setAttr(f"{inst}.{attr_name}", value)
                except RuntimeError:
                    pass

        created.append(inst)

    return created


# 使い方例:
# 親→子を選択してから実行
# instance_child_between_parent(count=5, include_end=True, orient="aim")
# instance_child_between_parent(spacing=2.5, include_end=False)
# instance_child_between_parent(use_bbox_spacing=True, bbox_count_mode=True, count=4)
