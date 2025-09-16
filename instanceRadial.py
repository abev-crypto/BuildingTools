import maya.cmds as cmds

def create_instance_circle_with_rotation(num_instances=8, axis='y'):
    sel = cmds.ls(selection=True)
    if len(sel) < 2:
        cmds.error("2つのオブジェクトを選択してください：1つ目に基準のTransform、2つ目にインスタンス対象")
        return

    base = sel[0]
    target = sel[1]

    axis = axis.lower()
    axis_index = {'x': 0, 'y': 1, 'z': 2}[axis]
    angle_step = 360.0 / num_instances

    for i in range(num_instances):
        null = cmds.group(empty=True, name=f"circle_null_{i:02}")

        # Transformの一致をMatchTransform系で行う
        cmds.matchTransform(null, base, pos=True, rot=True)

        # インスタンス作成・親子付け
        instance = cmds.instance(target, name=f"{target}_inst_{i:02}")[0]
        cmds.parent(instance, null)

        # 回転追加
        cmds.setAttr(f"{null}.rotate{axis.upper()}", angle_step * i)

    cmds.select(clear=True)
    print(f"{num_instances} 個の Null + インスタンスが作成されました。")


def show_circle_instance_ui():
    if cmds.window("circleInstanceWin", exists=True):
        cmds.deleteUI("circleInstanceWin")

    win = cmds.window("circleInstanceWin", title="円状インスタンス配置", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="center")

    cmds.text(label="1つ目：基準Transform\n2つ目：インスタンス対象", align='center')
    num_field = cmds.intFieldGrp(label="個数", value1=8)
    axis_radio = cmds.radioButtonGrp(
        label='回転軸',
        labelArray3=['X', 'Y', 'Z'],
        numberOfRadioButtons=3,
        select=2  # Y軸デフォルト
    )

    def on_create_pressed(*args):
        count = cmds.intFieldGrp(num_field, q=True, value1=True)
        axis_index = cmds.radioButtonGrp(axis_radio, q=True, select=True)
        axis = ['x', 'y', 'z'][axis_index - 1]
        create_instance_circle_with_rotation(num_instances=count, axis=axis)

    cmds.button(label="作成", command=on_create_pressed, bgc=(0.6, 0.8, 0.6))
    cmds.setParent("..")
    cmds.showWindow(win)

# 実行
show_circle_instance_ui()
