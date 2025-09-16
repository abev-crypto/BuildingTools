# -*- coding: utf-8 -*-
import math
import maya.cmds as cmds

def instance_child_between_parent(
    parent=None,
    child=None,
    count=5,
    include_end=False,
    orient="none",   # "none" | "aim" | "copy"
    parent_instances_to_parent=True,
    group_name=None,
    spacing=None,
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
    Returns:
        list[str]: 作成したインスタンスノード名のリスト
    """
    sel = cmds.ls(sl=True, type="transform", long=True) or []
    if parent is None or child is None:
        if len(sel) < 2:
            cmds.error(u"親→子の順で2つ選択するか、引数で parent と child を指定してください。")
        parent = parent or sel[0]
        child  = child  or sel[1]

    if not (cmds.objExists(parent) and cmds.objExists(child)):
        cmds.error(u"指定した parent または child が存在しません。")

    # ワールド座標の取得
    p_pos = cmds.xform(parent, q=True, ws=True, t=True)
    c_pos = cmds.xform(child,  q=True, ws=True, t=True)

    # グループ化
    group_node = None
    if group_name is not None:
        name = (group_name or "").strip() or "instanceGroup#"
        group_node = cmds.group(em=True, name=name)
        if parent_instances_to_parent and parent and cmds.objExists(parent):
            group_node = cmds.parent(group_node, parent)[0]

    # 配置割合の計算
    steps = [float(i)/(count+1) for i in range(1, count+1)]
    if include_end:
        steps.append(1.0)
    # 補間ステップの決定
    steps = []
    if spacing is not None:
        try:
            spacing_value = float(spacing)
        except (TypeError, ValueError):
            cmds.warning(u"距離指定は数値を入力してください。何も作成しません。")
            return []
        if spacing_value <= 0:
            cmds.warning(u"距離指定は正の値にしてください。何も作成しません。")
            return []

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
    for t in steps:
        pos = [p_pos[i] + (c_pos[i] - p_pos[i]) * t for i in range(3)]
        inst = cmds.instance(child, smartTransform=False)[0]

        # 親子付け
        if group_node:
            inst = cmds.parent(inst, group_node)[0]
        elif parent_instances_to_parent:
            inst = cmds.parent(inst, parent)[0]

        # 配置
        cmds.xform(inst, ws=True, t=pos)

        # 回転処理
        if orient == "copy":
            rot = cmds.xform(child, q=True, ws=True, ro=True)
            cmds.xform(inst, ws=True, ro=rot)
        elif orient == "aim":
            ac = cmds.aimConstraint(
                child, inst,
                aimVector=(0, 0, 1),
                upVector=(0, 1, 0),
                worldUpType="scene"
            )[0]
            cmds.delete(ac)

        created.append(inst)

    return created


# 使い方例:
# 親→子を選択してから実行
# instance_child_between_parent(count=5, include_end=True, orient="aim")
# instance_child_between_parent(spacing=2.5, include_end=False)
