# -*- coding: utf-8 -*-
"""Radial instance placement utilities."""

import maya.cmds as cmds


def create_instance_circle_with_rotation(num_instances=8, axis="y", group_name=None, radius=0.0):
    """Create instances of the second selected object around the first.

    Args:
        num_instances (int): Number of instances to create around the circle.
        axis (str): Axis to rotate around ("x", "y", or "z").
        group_name (str|None):
            指定時は空グループを新規作成し、生成した null をその子に、
            null 配下のインスタンスもまとめる。空文字なら "instanceGroup#"。
        radius (float): Distance to offset along the rotation axis before rotating.
    """
    sel = cmds.ls(selection=True, type="transform")
    if len(sel) < 2:
        cmds.error(
            u"2つのオブジェクトを選択してください：1つ目に基準のTransform、2つ目にインスタンス対象"
        )
        return []

    base = sel[0]
    target = sel[1]

    axis = axis.lower()
    if axis not in {"x", "y", "z"}:
        cmds.error(u"axis は x / y / z のいずれかを指定してください。")
        return []

    angle_step = 360.0 / float(num_instances)
    created = []

    group_node = None
    if group_name is not None:
        name = (group_name or "").strip() or "instanceGroup#"
        group_node = cmds.group(empty=True, name=name)

    for i in range(num_instances):
        null = cmds.group(empty=True, name=f"circle_null_{i:02}")

        # Transformの一致をMatchTransform系で行う
        cmds.matchTransform(null, base, pos=True, rot=True)

        if group_node:
            null = cmds.parent(null, group_node)[0]
        if radius:
            offset_vector = {
                "x": (radius, 0.0, 0.0),
                "y": (0.0, radius, 0.0),
                "z": (0.0, 0.0, radius),
            }[axis]
            cmds.move(*offset_vector, null, relative=True, objectSpace=True)

        # インスタンス作成・親子付け
        instance = cmds.instance(target, name=f"{target}_inst_{i:02}")[0]
        instance = cmds.parent(instance, null)[0]

        # 回転追加
        cmds.setAttr(f"{null}.rotate{axis.upper()}", angle_step * i)

        created.append(instance)

    cmds.select(created, r=True)
    return created


def show_circle_instance_ui():
    """Show a small UI for the radial instance creator."""
    if cmds.window("circleInstanceWin", exists=True):
        cmds.deleteUI("circleInstanceWin")

    win = cmds.window("circleInstanceWin", title=u"円状インスタンス配置", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="center")

    cmds.text(label=u"1つ目：基準Transform\n2つ目：インスタンス対象", align="center")
    num_field = cmds.intFieldGrp(label=u"個数", value1=8)
    axis_radio = cmds.radioButtonGrp(
        label=u"回転軸",
        labelArray3=["X", "Y", "Z"],
        numberOfRadioButtons=3,
        select=2,  # Y軸デフォルト
    )

    def on_create_pressed(*_):
        count = cmds.intFieldGrp(num_field, q=True, value1=True)
        axis_index = cmds.radioButtonGrp(axis_radio, q=True, select=True)
        axis_value = ["x", "y", "z"][axis_index - 1]
        create_instance_circle_with_rotation(num_instances=count, axis=axis_value)

    cmds.button(label=u"作成", command=on_create_pressed, bgc=(0.6, 0.8, 0.6))
    cmds.setParent("..")
    cmds.showWindow(win)


__all__ = ["create_instance_circle_with_rotation", "show_circle_instance_ui"]
