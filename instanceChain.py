# -*- coding: utf-8 -*-
import maya.cmds as cmds
import math


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]

def _vec_sub(a,b): return [a[i]-b[i] for i in range(3)]
def _vec_add(a,b): return [a[i]+b[i] for i in range(3)]
def _vec_mul(a,s): return [a[i]*s for i in range(3)]
def _dot(a,b): return sum(a[i]*b[i] for i in range(3))
def _len(a): return math.sqrt(_dot(a,a))
def _norm(a):
    L = _len(a)
    return [a[i]/L for i in range(3)] if L>1e-12 else [0,0,0]

def _world_pos(node):
    return cmds.xform(node, q=True, ws=True, t=True)


def _world_bbox_data(node):
    try:
        bbox = cmds.exactWorldBoundingBox(node)
    except RuntimeError:
        return None
    if not bbox or len(bbox) < 6:
        return None

    min_x, min_y, min_z, max_x, max_y, max_z = bbox
    corners = []
    for ix in (min_x, max_x):
        for iy in (min_y, max_y):
            for iz in (min_z, max_z):
                corners.append([ix, iy, iz])

    center = [
        (min_x + max_x) * 0.5,
        (min_y + max_y) * 0.5,
        (min_z + max_z) * 0.5,
    ]

    return {"corners": corners, "center": center}


def _project_range(points, axis, origin):
    values = [_dot(_vec_sub(p, origin), axis) for p in points]
    return (min(values), max(values)) if values else (0.0, 0.0)

def _max_dist_pair(points):
    # 全点間の最遠ペアを見つけて並び方向を安定化
    n = len(points)
    maxd = -1.0
    pair = (0, 0)
    for i in range(n):
        pi = points[i]
        for j in range(i+1, n):
            pj = points[j]
            d = _len(_vec_sub(pi, pj))
            if d > maxd:
                maxd = d
                pair = (i, j)
    return pair  # (idxA, idxB)

try:
    string_types = (basestring,)  # type: ignore[name-defined]
except NameError:  # pragma: no cover - Python 3 only
    string_types = (str,)


def instance_between_chain(
    template=None,
    targets=None,
    per_segment=1,                 # 各区間に何個置くか（= 1なら中点のみ）
    parent_instances_to=None,      # None: ワールド直下 / "same": 対象と同じ親 / 具体名: そのノード
    orient="none",                # "none" | "aim" | "copy"
    group_name=None,
    spacing=None,
    fill_boxes=False,
    fill_divisions=1,
    fill_alternate_scale=False,
    fill_alternate_axis="x",
):
    """
    選択： [テンプレ(最初)] + [対象群(2個以上)]
    対象群を空間上の並びで自動整列し、隣り合う各ペア区間にテンプレのインスタンスを per_segment 個 等間隔配置。

    Args:
        template (str|None): 最初に選んだインスタンス元。未指定なら選択先頭。fill_boxes=True の場合は無視。
        targets (list[str]|None): 並びの対象ノード。未指定なら選択2つ目以降。fill_boxes=True の場合は選択全て。
        per_segment (int): 各区間に置く個数（1で中点のみ、2で1/3・2/3…）。
        parent_instances_to (str|None): 親付け先
            - None: 親付けしない（ワールド）
            - "same": 直前の左ノードと同じ親にする
            - 具体ノード名: そのノードの子にする
        orient (str): "none" (回転維持) / "aim" (区間の+Zを進行方向へ) / "copy"(templateのWS回転コピー)
        group_name (str|None):
            指定時は空グループを作成し、その子に全インスタンスを入れる。空文字なら "instanceGroup#"。
            parent_instances_to が "same" の場合は最初の対象と同じ親に、
            ノード名を指定した場合はそのノードの子にグループを配置します。
        spacing (float|None): 各区間でのインスタンス間隔。指定時は距離から自動的に配置数を決定。
        fill_boxes (bool): True の場合、各区間を埋める Box を自動生成してインスタンス化します。
        fill_divisions (int): fill_boxes=True の場合に区間を何分割するか。
        fill_alternate_scale (bool): fill_boxes=True の場合にスケールを交互に反転させるか。
        fill_alternate_axis (str): 交互反転させる軸（"x"/"y"/"z"）。
    Returns:
        list[str]: 生成インスタンスの名前
    """
    sel = cmds.ls(sl=True, type="transform", long=True) or []
    if fill_boxes:
        if targets is None:
            if len(sel) < 2:
                cmds.error(u"対象を2つ以上選択するか、targets を指定してください。")
            targets = sel
    else:
        if template is None or targets is None:
            if len(sel) < 3:
                cmds.error(u"最初にテンプレ、その後に少なくとも2つの対象を選択してください。")
            template = template or sel[0]
            targets  = targets  or sel[1:]

        if not cmds.objExists(template):
            cmds.error(u"template が存在しません。")
    targets = [t for t in targets if cmds.objExists(t)]
    if len(targets) < 2:
        cmds.error(u"targets は2つ以上必要です。")

    # 位置取得
    pts = [_world_pos(t) for t in targets]

    # 並び順を自動推定（最遠ペアを端点に採用→片端から投影値でソート）
    iA, iB = _max_dist_pair(pts)
    A = pts[iA]; B = pts[iB]
    dirAB = _norm(_vec_sub(B, A))
    # Aを原点として投影値で昇順
    order = sorted(range(len(targets)), key=lambda i: _dot(_vec_sub(pts[i], A), dirAB))
    ordered_nodes = [targets[i] for i in order]
    ordered_pts   = [pts[i] for i in order]

    group_node = None
    if group_name is not None:
        name = (group_name or "").strip() or "instanceGroup#"
        group_node = cmds.group(em=True, name=name)
        if parent_instances_to == "same" and ordered_nodes:
            parent = cmds.listRelatives(ordered_nodes[0], p=True, f=True)
            if parent:
                group_node = cmds.parent(group_node, parent[0])[0]
        elif (
            isinstance(parent_instances_to, string_types)
            and parent_instances_to not in ("", "same")
            and cmds.objExists(parent_instances_to)
        ):
            group_node = cmds.parent(group_node, parent_instances_to)[0]
    spacing_value = None
    use_spacing = False
    if fill_boxes:
        use_spacing = False
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

    created = []
    fill_divisions_value = 1
    alternate_axis_index = None
    axis_attrs = ["scaleX", "scaleY", "scaleZ"]
    if fill_boxes:
        try:
            fill_divisions_value = int(fill_divisions)
        except (TypeError, ValueError):
            fill_divisions_value = 1
        if fill_divisions_value < 1:
            fill_divisions_value = 1

        alt_axis = (fill_alternate_axis or "x").lower()
        if fill_alternate_scale and alt_axis in {"x", "y", "z"}:
            alternate_axis_index = {"x": 0, "y": 1, "z": 2}[alt_axis]

    box_template = None
    created_template = False
    global_index = 0

    for k in range(len(ordered_nodes)-1):
        left_node  = ordered_nodes[k]
        right_node = ordered_nodes[k+1]
        if fill_boxes:
            left_bbox = _world_bbox_data(left_node)
            right_bbox = _world_bbox_data(right_node)
            if not left_bbox or not right_bbox:
                continue

            anchor = left_bbox["center"]
            dir_vec = _vec_sub(right_bbox["center"], anchor)
            dir_len = _len(dir_vec)
            if dir_len < 1e-6:
                continue
            dir_z = [dir_vec[i] / dir_len for i in range(3)]

            left_proj = _project_range(left_bbox["corners"], dir_z, anchor)
            right_proj = _project_range(right_bbox["corners"], dir_z, anchor)
            left_proj_max = left_proj[1]
            right_proj_min = right_proj[0]
            gap_total = right_proj_min - left_proj_max
            if gap_total <= 1e-6:
                continue

            up_ref = (0.0, 1.0, 0.0)
            if abs(_dot(dir_z, up_ref)) > 0.999:
                up_ref = (1.0, 0.0, 0.0)
            dir_x = _cross(up_ref, dir_z)
            if _len(dir_x) < 1e-6:
                dir_x = [1.0, 0.0, 0.0]
            dir_x = _norm(dir_x)
            dir_y = _cross(dir_z, dir_x)
            dir_y = _norm(dir_y)
            dir_x = _norm(_cross(dir_y, dir_z))

            left_x_range = _project_range(left_bbox["corners"], dir_x, anchor)
            right_x_range = _project_range(right_bbox["corners"], dir_x, anchor)
            left_y_range = _project_range(left_bbox["corners"], dir_y, anchor)
            right_y_range = _project_range(right_bbox["corners"], dir_y, anchor)

            left_x_size = left_x_range[1] - left_x_range[0]
            right_x_size = right_x_range[1] - right_x_range[0]
            left_y_size = left_y_range[1] - left_y_range[0]
            right_y_size = right_y_range[1] - right_y_range[0]

            size_x = max(abs(left_x_size), abs(right_x_size), 1e-3)
            size_y = max(abs(left_y_size), abs(right_y_size), 1e-3)

            center_offset_x = 0.5 * (
                (left_x_range[0] + left_x_range[1]) * 0.5
                + (right_x_range[0] + right_x_range[1]) * 0.5
            )
            center_offset_y = 0.5 * (
                (left_y_range[0] + left_y_range[1]) * 0.5
                + (right_y_range[0] + right_y_range[1]) * 0.5
            )

            segment_length = gap_total / float(fill_divisions_value)
            for div in range(fill_divisions_value):
                start = left_proj_max + segment_length * div
                mid_scalar = start + segment_length * 0.5

                scale_values = [size_x, size_y, segment_length]
                if alternate_axis_index is not None and (global_index % 2 == 1):
                    scale_values[alternate_axis_index] *= -1.0

                if box_template is None:
                    created_template = True
                    box_template, _ = cmds.polyCube(w=1, h=1, d=1, ch=False)
                    inst = box_template
                else:
                    inst = cmds.instance(box_template, smartTransform=False)[0]

                if group_node:
                    inst = cmds.parent(inst, group_node)[0]
                    if created_template:
                        box_template = inst
                elif parent_instances_to == "same":
                    parent = cmds.listRelatives(left_node, p=True, f=True)
                    if parent:
                        inst = cmds.parent(inst, parent[0])[0]
                        if created_template:
                            box_template = inst
                elif isinstance(parent_instances_to, string_types):
                    if cmds.objExists(parent_instances_to):
                        inst = cmds.parent(inst, parent_instances_to)[0]
                        if created_template:
                            box_template = inst

                matrix = [
                    dir_x[0], dir_y[0], dir_z[0], 0.0,
                    dir_x[1], dir_y[1], dir_z[1], 0.0,
                    dir_x[2], dir_y[2], dir_z[2], 0.0,
                    0.0,       0.0,       0.0,       1.0,
                ]
                cmds.xform(inst, ws=True, matrix=matrix)

                center_pos = anchor
                center_pos = _vec_add(center_pos, _vec_mul(dir_x, center_offset_x))
                center_pos = _vec_add(center_pos, _vec_mul(dir_y, center_offset_y))
                center_pos = _vec_add(center_pos, _vec_mul(dir_z, mid_scalar))
                cmds.xform(inst, ws=True, t=center_pos)

                for axis_i, attr in enumerate(axis_attrs):
                    try:
                        cmds.setAttr(f"{inst}.{attr}", scale_values[axis_i])
                    except RuntimeError:
                        pass

                created.append(inst)
                created_template = False
                global_index += 1

            continue

        p0 = ordered_pts[k]
        p1 = ordered_pts[k+1]
        seg = _vec_sub(p1, p0)

        if use_spacing:
            seg_len = _len(seg)
            eps = 1e-6
            t_values = []
            if seg_len > eps:
                current = spacing_value
                while current < seg_len - eps:
                    t_values.append(current / seg_len)
                    current += spacing_value
            else:
                t_values = []
        else:
            t_values = [float(s)/(per_segment+1) for s in range(1, per_segment+1)]

        for t in t_values:
            pos = _vec_add(p0, _vec_mul(seg, t))

            inst = cmds.instance(template, smartTransform=False)[0]

            # 親付け
            if group_node:
                inst = cmds.parent(inst, group_node)[0]
            elif parent_instances_to == "same":
                # 左ノードと同じ親
                parent = cmds.listRelatives(left_node, p=True, f=True)
                if parent:
                    inst = cmds.parent(inst, parent[0])[0]
            elif isinstance(parent_instances_to, string_types):
                if cmds.objExists(parent_instances_to):
                    inst = cmds.parent(inst, parent_instances_to)[0]
            # None の場合は親付けしない

            # 位置
            cmds.xform(inst, ws=True, t=pos)

            # 回転
            if orient == "copy":
                rot = cmds.xform(template, q=True, ws=True, ro=True)
                cmds.xform(inst, ws=True, ro=rot)
            elif orient == "aim":
                # 区間方向へ +Z を向ける（必要なら aimVector/upVector 調整）
                ac = cmds.aimConstraint(
                    right_node, inst,
                    aimVector=(0,0,1),
                    upVector=(0,1,0),
                    worldUpType="scene"
                )[0]
                cmds.delete(ac)
            # "none" は何もしない

            created.append(inst)

    if spacing_value is not None and not created:
        cmds.warning(u"指定条件では配置するインスタンスがありません。")

    if fill_boxes and not created:
        cmds.warning(u"ボックスを作成できる区間がありませんでした。")

    return created

# 使い方：
# 1) テンプレ（新たに置きたいオブジェクト）を先に選択
# 2) その後、「前スクリプトで作った並び」を2つ以上選択
# 3) 実行例（中点1つ、親は左ノードと同じ、向きは区間方向に向ける）:
# instance_between_chain(per_segment=1, parent_instances_to="same", orient="aim")

# 例：各区間に2個置きたい（1/3 と 2/3 の位置）
# instance_between_chain(per_segment=2, parent_instances_to=None, orient="none")

# 例：各区間を 2.0 の距離で埋めたい
# instance_between_chain(spacing=2.0, parent_instances_to=None, orient="none")
