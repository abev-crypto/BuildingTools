# -*- coding: utf-8 -*-
"""Unified UI for the instance placement helper scripts."""

import maya.cmds as cmds

import instanceArray
import instanceChain
import instanceRadial
import instanceUtilities


WINDOW_NAME = "buildingToolsWin"


def _show_error(message):
    cmds.inViewMessage(amg=f"<span style='color:#ffaaaa'>{message}</span>", pos="midCenter", fade=True)


def show_ui():
    """Display the Building Tools UI window."""
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    win = cmds.window(WINDOW_NAME, title=u"Building Tools", sizeable=False)
    tabs = cmds.tabLayout(innerMarginWidth=8, innerMarginHeight=8)

    # ------------------------------------------------------------------
    # Array tab
    # ------------------------------------------------------------------
    array_tab = cmds.columnLayout(adj=True, rowSpacing=6, columnAttach=("both", 8))
    cmds.text(label=u"選択：親(始点) → 子(終点)", align="left")
    array_spec_mode = cmds.optionMenuGrp(
        label=u"指定方法",
        columnWidth=[(1, 100)],
    )
    cmds.menuItem(label=u"個数指定")
    cmds.menuItem(label=u"距離指定")

    array_count = cmds.intFieldGrp(label=u"間に置く個数", value1=5, columnWidth=[(1, 100), (2, 60)])
    array_spacing = cmds.floatFieldGrp(
        label=u"間隔 (距離)",
        value1=1.0,
        columnWidth=[(1, 100), (2, 80)],
        enable=False,
    )
    array_include_end = cmds.checkBox(label=u"終点にも配置する", value=False)
    array_orient = cmds.optionMenuGrp(label=u"向き", columnWidth=[(1, 100)])
    cmds.menuItem(label=u"維持 (none)")
    cmds.menuItem(label=u"終点方向 (aim)")
    cmds.menuItem(label=u"コピー (copy)")
    array_parent = cmds.checkBox(label=u"親(始点)の子にする", value=True)

    def on_array_spec_mode_changed(*_):
        use_spacing = cmds.optionMenuGrp(array_spec_mode, q=True, select=True) == 2
        cmds.intFieldGrp(array_count, e=True, enable=not use_spacing)
        cmds.floatFieldGrp(array_spacing, e=True, enable=use_spacing)

    cmds.optionMenuGrp(array_spec_mode, e=True, changeCommand=on_array_spec_mode_changed)
    on_array_spec_mode_changed()

    def on_array_execute(*_):
        try:
            orient_idx = cmds.optionMenuGrp(array_orient, q=True, select=True)
            orient_value = ["none", "aim", "copy"][orient_idx - 1]
            use_spacing = cmds.optionMenuGrp(array_spec_mode, q=True, select=True) == 2
            spacing_value = None
            if use_spacing:
                spacing_value = cmds.floatFieldGrp(array_spacing, q=True, value1=True)
            result = instanceArray.instance_child_between_parent(
                count=cmds.intFieldGrp(array_count, q=True, value1=True),
                include_end=cmds.checkBox(array_include_end, q=True, value=True),
                orient=orient_value,
                parent_instances_to_parent=cmds.checkBox(array_parent, q=True, value=True),
                spacing=spacing_value,
            )
            if result:
                cmds.inViewMessage(
                    amg=u"<span style='color:#b0ffb0'>%d 個のインスタンスを作成しました。</span>" % len(result),
                    pos="midCenter",
                    fade=True,
                )
        except RuntimeError as exc:
            _show_error(str(exc))

    cmds.button(label=u"配置", command=on_array_execute, bgc=(0.6, 0.8, 0.6))
    cmds.setParent("..")

    # ------------------------------------------------------------------
    # Chain tab
    # ------------------------------------------------------------------
    chain_tab = cmds.columnLayout(adj=True, rowSpacing=6, columnAttach=("both", 8))
    cmds.text(label=u"選択：テンプレート → 対象2つ以上", align="left")
    chain_spec_mode = cmds.optionMenuGrp(
        label=u"指定方法",
        columnWidth=[(1, 110)],
    )
    cmds.menuItem(label=u"個数指定")
    cmds.menuItem(label=u"距離指定")

    chain_count = cmds.intFieldGrp(label=u"各区間の個数", value1=1, columnWidth=[(1, 110), (2, 60)])
    chain_spacing = cmds.floatFieldGrp(
        label=u"各区間の間隔",
        value1=1.0,
        columnWidth=[(1, 110), (2, 80)],
        enable=False,
    )

    def on_parent_mode_changed(selection):
        enable = selection == u"指定ノード"
        cmds.textFieldGrp(chain_parent_target, e=True, enable=enable)

    chain_parent_mode = cmds.optionMenuGrp(
        label=u"親付け",
        columnWidth=[(1, 110)],
        changeCommand=on_parent_mode_changed,
    )
    cmds.menuItem(label=u"なし (ワールド)")
    cmds.menuItem(label=u"左ノードと同じ")
    cmds.menuItem(label=u"指定ノード")
    chain_parent_target = cmds.textFieldGrp(label=u"親ノード名", text="", enable=False)

    chain_orient = cmds.optionMenuGrp(label=u"向き", columnWidth=[(1, 110)])
    cmds.menuItem(label=u"維持 (none)")
    cmds.menuItem(label=u"区間方向 (aim)")
    cmds.menuItem(label=u"コピー (copy)")

    def on_chain_spec_mode_changed(*_):
        use_spacing = cmds.optionMenuGrp(chain_spec_mode, q=True, select=True) == 2
        cmds.intFieldGrp(chain_count, e=True, enable=not use_spacing)
        cmds.floatFieldGrp(chain_spacing, e=True, enable=use_spacing)

    cmds.optionMenuGrp(chain_spec_mode, e=True, changeCommand=on_chain_spec_mode_changed)
    on_chain_spec_mode_changed()

    def on_chain_execute(*_):
        try:
            orient_idx = cmds.optionMenuGrp(chain_orient, q=True, select=True)
            orient_value = ["none", "aim", "copy"][orient_idx - 1]
            parent_idx = cmds.optionMenuGrp(chain_parent_mode, q=True, select=True)
            if parent_idx == 1:
                parent_mode = None
            elif parent_idx == 2:
                parent_mode = "same"
            else:
                parent_text = cmds.textFieldGrp(chain_parent_target, q=True, text=True).strip()
                parent_mode = parent_text or None
            use_spacing = cmds.optionMenuGrp(chain_spec_mode, q=True, select=True) == 2
            spacing_value = None
            if use_spacing:
                spacing_value = cmds.floatFieldGrp(chain_spacing, q=True, value1=True)
            result = instanceChain.instance_between_chain(
                per_segment=cmds.intFieldGrp(chain_count, q=True, value1=True),
                parent_instances_to=parent_mode,
                orient=orient_value,
                spacing=spacing_value,
            )
            if result:
                cmds.inViewMessage(
                    amg=u"<span style='color:#b0ffb0'>%d 個のインスタンスを作成しました。</span>" % len(result),
                    pos="midCenter",
                    fade=True,
                )
        except RuntimeError as exc:
            _show_error(str(exc))

    cmds.button(label=u"配置", command=on_chain_execute, bgc=(0.6, 0.8, 0.6))
    cmds.setParent("..")

    # ------------------------------------------------------------------
    # Radial tab
    # ------------------------------------------------------------------
    radial_tab = cmds.columnLayout(adj=True, rowSpacing=6, columnAttach=("both", 8))
    cmds.text(label=u"選択：基準 → インスタンス対象", align="left")
    radial_count = cmds.intFieldGrp(label=u"個数", value1=8, columnWidth=[(1, 100), (2, 60)])
    radial_axis = cmds.optionMenuGrp(label=u"回転軸", columnWidth=[(1, 100)])
    cmds.menuItem(label="X")
    cmds.menuItem(label="Y")
    cmds.menuItem(label="Z")

    def on_radial_execute(*_):
        try:
            axis_idx = cmds.optionMenuGrp(radial_axis, q=True, select=True)
            axis_value = ["x", "y", "z"][axis_idx - 1]
            result = instanceRadial.create_instance_circle_with_rotation(
                num_instances=cmds.intFieldGrp(radial_count, q=True, value1=True),
                axis=axis_value,
            )
            if result:
                cmds.inViewMessage(
                    amg=u"<span style='color:#b0ffb0'>%d 個のインスタンスを作成しました。</span>" % len(result),
                    pos="midCenter",
                    fade=True,
                )
        except RuntimeError as exc:
            _show_error(str(exc))

    cmds.button(label=u"作成", command=on_radial_execute, bgc=(0.6, 0.8, 0.6))
    cmds.setParent("..")

    # ------------------------------------------------------------------
    # Utility tab
    # ------------------------------------------------------------------
    util_tab = cmds.columnLayout(adj=True, rowSpacing=8, columnAttach=("both", 8))
    cmds.text(label=u"選択：最初にテンプレート → 置換したいオブジェクト", align="left")

    def on_replace(*_):
        try:
            result = instanceUtilities.replace_with_first_instance()
            if result:
                cmds.inViewMessage(
                    amg=u"<span style='color:#b0ffb0'>%d 個のオブジェクトを置換しました。</span>" % len(result),
                    pos="midCenter",
                    fade=True,
                )
        except RuntimeError as exc:
            _show_error(str(exc))

    cmds.button(label=u"選択をテンプレートのインスタンスで置換", command=on_replace, bgc=(0.6, 0.7, 0.9))

    cmds.separator(style="in")
    cmds.text(label=u"選択：インスタンス化を解除したいオブジェクト", align="left")

    def on_make_unique(*_):
        result = instanceUtilities.make_selected_unique()
        if result:
            cmds.inViewMessage(
                amg=u"<span style='color:#b0ffb0'>%d 個のインスタンスを解除しました。</span>" % len(result),
                pos="midCenter",
                fade=True,
            )

    cmds.button(label=u"インスタンス解除", command=on_make_unique, bgc=(0.9, 0.7, 0.6))
    cmds.setParent("..")

    cmds.tabLayout(
        tabs,
        edit=True,
        tabLabel=[
            (array_tab, u"ライン"),
            (chain_tab, u"チェーン"),
            (radial_tab, u"ラジアル"),
            (util_tab, u"ユーティリティ"),
        ],
    )

    cmds.showWindow(win)
    return win


if __name__ == "__main__":
    show_ui()
