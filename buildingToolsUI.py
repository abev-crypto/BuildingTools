# -*- coding: utf-8 -*-
"""Unified UI for the instance placement helper scripts."""

import maya.cmds as cmds

import instanceArray
import instanceChain
import instanceRadial
import instanceUtilities


WINDOW_NAME = "buildingToolsWin"

OPTION_VAR_PREFIX = "buildingToolsUI_"
_UI_CONTROLS = {}


def _option_var_name(key):
    return f"{OPTION_VAR_PREFIX}{key}"


def load_prefs():
    """Restore previously saved UI values from Maya's optionVar."""
    if not _UI_CONTROLS:
        return

    controls = _UI_CONTROLS

    def _get_option(key):
        option_name = _option_var_name(key)
        if cmds.optionVar(exists=option_name):
            return cmds.optionVar(q=option_name)
        return None

    value = _get_option("array_count")
    if value is not None:
        try:
            cmds.intFieldGrp(controls["array_count"], e=True, value1=int(value))
        except (TypeError, ValueError):
            pass

    value = _get_option("array_include_end")
    if value is not None:
        try:
            cmds.checkBox(controls["array_include_end"], e=True, value=bool(int(value)))
        except (TypeError, ValueError):
            pass

    value = _get_option("array_orient")
    if value is not None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = None
        if index is not None:
            num_items = cmds.optionMenuGrp(controls["array_orient"], q=True, numberOfItems=True)
            index = max(1, min(num_items, index))
            cmds.optionMenuGrp(controls["array_orient"], e=True, select=index)

    value = _get_option("array_parent")
    if value is not None:
        try:
            cmds.checkBox(controls["array_parent"], e=True, value=bool(int(value)))
        except (TypeError, ValueError):
            pass

    value = _get_option("chain_count")
    if value is not None:
        try:
            cmds.intFieldGrp(controls["chain_count"], e=True, value1=int(value))
        except (TypeError, ValueError):
            pass

    value = _get_option("chain_parent_mode")
    if value is not None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = None
        if index is not None:
            num_items = cmds.optionMenuGrp(controls["chain_parent_mode"], q=True, numberOfItems=True)
            index = max(1, min(num_items, index))
            cmds.optionMenuGrp(controls["chain_parent_mode"], e=True, select=index)

    value = _get_option("chain_parent_target")
    if value is not None:
        cmds.textFieldGrp(controls["chain_parent_target"], e=True, text=value)

    value = _get_option("chain_orient")
    if value is not None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = None
        if index is not None:
            num_items = cmds.optionMenuGrp(controls["chain_orient"], q=True, numberOfItems=True)
            index = max(1, min(num_items, index))
            cmds.optionMenuGrp(controls["chain_orient"], e=True, select=index)

    value = _get_option("radial_count")
    if value is not None:
        try:
            cmds.intFieldGrp(controls["radial_count"], e=True, value1=int(value))
        except (TypeError, ValueError):
            pass

    value = _get_option("radial_axis")
    if value is not None:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = None
        if index is not None:
            num_items = cmds.optionMenuGrp(controls["radial_axis"], q=True, numberOfItems=True)
            index = max(1, min(num_items, index))
            cmds.optionMenuGrp(controls["radial_axis"], e=True, select=index)

    # Ensure the chain parent target field has the correct enabled state.
    chain_parent_label = cmds.optionMenuGrp(controls["chain_parent_mode"], q=True, value=True)
    cmds.textFieldGrp(
        controls["chain_parent_target"],
        e=True,
        enable=chain_parent_label == u"指定ノード",
    )


def save_prefs():
    """Persist current UI values via Maya's optionVar."""
    if not _UI_CONTROLS:
        return

    controls = _UI_CONTROLS

    cmds.optionVar(
        iv=(
            _option_var_name("array_count"),
            int(cmds.intFieldGrp(controls["array_count"], q=True, value1=True)),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("array_include_end"),
            int(bool(cmds.checkBox(controls["array_include_end"], q=True, value=True))),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("array_orient"),
            int(cmds.optionMenuGrp(controls["array_orient"], q=True, select=True)),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("array_parent"),
            int(bool(cmds.checkBox(controls["array_parent"], q=True, value=True))),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("chain_count"),
            int(cmds.intFieldGrp(controls["chain_count"], q=True, value1=True)),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("chain_parent_mode"),
            int(cmds.optionMenuGrp(controls["chain_parent_mode"], q=True, select=True)),
        )
    )
    cmds.optionVar(
        sv=(
            _option_var_name("chain_parent_target"),
            cmds.textFieldGrp(controls["chain_parent_target"], q=True, text=True),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("chain_orient"),
            int(cmds.optionMenuGrp(controls["chain_orient"], q=True, select=True)),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("radial_count"),
            int(cmds.intFieldGrp(controls["radial_count"], q=True, value1=True)),
        )
    )
    cmds.optionVar(
        iv=(
            _option_var_name("radial_axis"),
            int(cmds.optionMenuGrp(controls["radial_axis"], q=True, select=True)),
        )
    )


def _show_error(message):
    cmds.inViewMessage(amg=f"<span style='color:#ffaaaa'>{message}</span>", pos="midCenter", fade=True)


def show_ui():
    """Display the Building Tools UI window."""
    global _UI_CONTROLS
    if cmds.window(WINDOW_NAME, exists=True):
        save_prefs()
        cmds.deleteUI(WINDOW_NAME)
        _UI_CONTROLS = {}

    win = cmds.window(WINDOW_NAME, title=u"Building Tools", sizeable=False)
    cmds.columnLayout(adj=True, rowSpacing=8, columnAttach=("both", 8))
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
    array_group = cmds.checkBox(label=u"インスタンスをグループ化", value=False)
    array_group_name = cmds.textFieldGrp(label=u"グループ名", text="", enable=False)

    def on_array_group_changed(value):
        cmds.textFieldGrp(array_group_name, e=True, enable=value)

    cmds.checkBox(array_group, e=True, changeCommand=on_array_group_changed)

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
            group_name = None
            if cmds.checkBox(array_group, q=True, value=True):
                text = cmds.textFieldGrp(array_group_name, q=True, text=True).strip()
                group_name = text if text else ""
            use_spacing = cmds.optionMenuGrp(array_spec_mode, q=True, select=True) == 2
            spacing_value = None
            if use_spacing:
                spacing_value = cmds.floatFieldGrp(array_spacing, q=True, value1=True)
            result = instanceArray.instance_child_between_parent(
                count=cmds.intFieldGrp(array_count, q=True, value1=True),
                include_end=cmds.checkBox(array_include_end, q=True, value=True),
                orient=orient_value,
                parent_instances_to_parent=cmds.checkBox(array_parent, q=True, value=True),
                group_name=group_name,
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
    chain_group = cmds.checkBox(label=u"インスタンスをグループ化", value=False)
    chain_group_name = cmds.textFieldGrp(label=u"グループ名", text="", enable=False)

    def on_chain_group_changed(value):
        cmds.textFieldGrp(chain_group_name, e=True, enable=value)

    cmds.checkBox(chain_group, e=True, changeCommand=on_chain_group_changed)

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
            group_name = None
            if cmds.checkBox(chain_group, q=True, value=True):
                text = cmds.textFieldGrp(chain_group_name, q=True, text=True).strip()
                group_name = text if text else ""
            use_spacing = cmds.optionMenuGrp(chain_spec_mode, q=True, select=True) == 2
            spacing_value = None
            if use_spacing:
                spacing_value = cmds.floatFieldGrp(chain_spacing, q=True, value1=True)
            result = instanceChain.instance_between_chain(
                per_segment=cmds.intFieldGrp(chain_count, q=True, value1=True),
                parent_instances_to=parent_mode,
                orient=orient_value,
                group_name=group_name,
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
    radial_radius = cmds.intFieldGrp(label=u"半径", value1=10, columnWidth=[(1, 100), (2, 60)])
    radial_axis = cmds.optionMenuGrp(label=u"回転軸", columnWidth=[(1, 100)])
    cmds.menuItem(label="X")
    cmds.menuItem(label="Y")
    cmds.menuItem(label="Z")
    radial_group = cmds.checkBox(label=u"インスタンスをグループ化", value=False)
    radial_group_name = cmds.textFieldGrp(label=u"グループ名", text="", enable=False)

    def on_radial_group_changed(value):
        cmds.textFieldGrp(radial_group_name, e=True, enable=value)

    cmds.checkBox(radial_group, e=True, changeCommand=on_radial_group_changed)

    def on_radial_execute(*_):
        try:
            axis_idx = cmds.optionMenuGrp(radial_axis, q=True, select=True)
            axis_value = ["x", "y", "z"][axis_idx - 1]
            group_name = None
            if cmds.checkBox(radial_group, q=True, value=True):
                text = cmds.textFieldGrp(radial_group_name, q=True, text=True).strip()
                group_name = text if text else ""
            result = instanceRadial.create_instance_circle_with_rotation(
                num_instances=cmds.intFieldGrp(radial_count, q=True, value1=True),
                axis=axis_value,
                group_name=group_name,
                radius=cmds.intFieldGrp(radial_radius, q=True, value1=True),
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

    cmds.separator(style="in")
    cmds.text(label=u"選択：アウトライナ順を並べ替えたいオブジェクト", align="left")
    util_sort_axis = cmds.optionMenuGrp(
        label=u"基準軸",
        columnWidth=[(1, 100)],
    )
    cmds.menuItem(label=u"自動 (最大距離)")
    cmds.menuItem(label="X")
    cmds.menuItem(label="Y")
    cmds.menuItem(label="Z")
    util_sort_desc = cmds.checkBox(label=u"降順 (大きい順)", value=False)

    def on_sort_selected(*_):
        axis_idx = cmds.optionMenuGrp(util_sort_axis, q=True, select=True)
        axis_value = {1: "auto", 2: "x", 3: "y", 4: "z"}[axis_idx]
        descending = cmds.checkBox(util_sort_desc, q=True, value=True)
        try:
            result = instanceUtilities.sort_selected_by_position(axis=axis_value, descending=descending)
            if result:
                axis_label = {
                    "auto": u"自動", "x": "X", "y": "Y", "z": "Z"
                }[axis_value]
                order_label = u"降順" if descending else u"昇順"
                cmds.inViewMessage(
                    amg=u"<span style='color:#b0ffb0'>%d 個のオブジェクトを %s (%s) で並べ替えました。</span>"
                    % (len(result), axis_label, order_label),
                    pos="midCenter",
                    fade=True,
                )
        except RuntimeError as exc:
            _show_error(str(exc))

    cmds.button(label=u"ポジションで並べ替え", command=on_sort_selected, bgc=(0.7, 0.9, 0.7))
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

    cmds.setParent("..")

    def on_save_settings(*_):
        save_prefs()
        cmds.inViewMessage(
            amg=u"<span style='color:#b0ffb0'>設定を保存しました。</span>",
            pos="midCenter",
            fade=True,
        )

    cmds.button(label=u"設定保存", command=on_save_settings, bgc=(0.8, 0.8, 0.8))

    _UI_CONTROLS = {
        "array_count": array_count,
        "array_include_end": array_include_end,
        "array_orient": array_orient,
        "array_parent": array_parent,
        "chain_count": chain_count,
        "chain_parent_mode": chain_parent_mode,
        "chain_parent_target": chain_parent_target,
        "chain_orient": chain_orient,
        "radial_count": radial_count,
        "radial_axis": radial_axis,
    }

    load_prefs()

    def on_close(*_):
        global _UI_CONTROLS
        try:
            save_prefs()
        finally:
            _UI_CONTROLS = {}

    cmds.window(win, e=True, closeCommand=on_close)

    cmds.showWindow(win)
    return win


if __name__ == "__main__":
    show_ui()
