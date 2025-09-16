# -*- coding: utf-8 -*-
import maya.cmds as cmds
import math

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
):
    """
    選択： [テンプレ(最初)] + [対象群(2個以上)]
    対象群を空間上の並びで自動整列し、隣り合う各ペア区間にテンプレのインスタンスを per_segment 個 等間隔配置。

    Args:
        template (str|None): 最初に選んだインスタンス元。未指定なら選択先頭。
        targets (list[str]|None): 並びの対象ノード。未指定なら選択2つ目以降。
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
    Returns:
        list[str]: 生成インスタンスの名前
    """
    sel = cmds.ls(sl=True, type="transform", long=True) or []
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
    if spacing is not None:
        try:
            spacing_value = float(spacing)
        except (TypeError, ValueError):
            cmds.warning(u"距離指定は数値を入力してください。何も作成しません。")
            return []
        if spacing_value <= 0:
            cmds.warning(u"距離指定は正の値にしてください。何も作成しません。")
            return []

    created = []
    for k in range(len(ordered_nodes)-1):
        left_node  = ordered_nodes[k]
        right_node = ordered_nodes[k+1]
        p0 = ordered_pts[k]
        p1 = ordered_pts[k+1]
        seg = _vec_sub(p1, p0)

        if spacing_value is not None:
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
