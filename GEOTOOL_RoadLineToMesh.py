from email.policy import default
import bpy
from bpy.props import IntProperty, BoolProperty, PointerProperty, EnumProperty
from mathutils import Vector
from mathutils import geometry
import time

bl_info = {
    "name": "GEOTOOL_RoadLineToMesh",
    "author": "TakuyaTazoe",
    "version": (1, 0, 0),
    "blender": (4, 5, 5),
    "location": "User > Original",
    "description": "路面標示ポリラインの生成・編集とメッシュ化",
    "category": "Object"
}

"""
オブジェクト・コレクションの操作
"""
# オブジェクトのTransformの位置・角度・スケールが正規化されているか
def is_transform_normalized(obj, eps=1e-6) -> bool:
    return (obj.location.length < eps and
            all(abs(a) < eps for a in obj.rotation_euler) and
            all(abs(s-1.0) < eps for s in obj.scale))
    
# オブジェクトのTransformの位置・角度・スケールがロックされているか
def is_transform_locked(obj) -> bool:
    return (all(obj.lock_location) and all(obj.lock_rotation) and all(obj.lock_scale))

# 指定した名前のコレクションを取得・新規作成
# 親コレクションを指定でその子供としてリンクされているという条件を追加
def get_or_create_collection(name, parent = None):
    collection = None
    parent_collection = None
    if parent:
        # 指定した親コレクションにリンクされている必要あり
        parent_collection = parent
        for child in parent.children:
            # 通し番号(.001)を考慮する
            if child.name.startswith(name):
                return child
    else:
        # 親コレクション指定なしはシーンコレクション
        parent_collection = bpy.context.scene.collection
        collection = bpy.data.collections.get(name)
    
    # コレクションが無ければ新規作成
    if collection is None:
        collection = bpy.data.collections.new(name)
    
    # 指定以外の親リンクを解除（children 走査で同一性比較）
    for possible_parent in bpy.data.collections:
        if possible_parent is parent_collection:
            continue
        # その親の子に含まれているかを安全に判定
        if any(child is collection for child in possible_parent.children):
            possible_parent.children.unlink(collection)
    
    # 指定の親にリンクされていなければリンク
    if not any(child is collection for child in parent_collection.children):
        parent_collection.children.link(collection)
    
    return collection

# 指定されたコレクションにリンクされているオブジェクトを削除
def clear_collection(collection) -> None:
    # コレクション内のオブジェクトをコピーして走査
    for obj in list(collection.objects):
        # このオブジェクトがリンクされているコレクション数
        linked_collections = obj.users_collection

        # コレクションからリンク解除
        collection.objects.unlink(obj)

        # このコレクションにしかリンクされていない場合は削除
        if len(linked_collections) == 1:
            # オブジェクト削除
            bpy.data.objects.remove(obj, do_unlink=True)

"""
ポリラインの操作
"""
# ポリラインから線形の頂点座標配列を生成
def polyline_to_line_points(polyline_obj, start_point : Vector):
    # オブジェクトがNoneじゃないか
    if not polyline_obj:
        raise RuntimeError("ポリラインが指定されていません。")
    
    # オブジェクトがメッシュかどうか
    if polyline_obj.type != 'MESH':
        raise RuntimeError(f"{polyline_obj.name}はメッシュではありません。\n中央線に沿ったペースポリラインを作成して指定してください。")
    
    # メッシュに頂点が2つ以上あるか
    if len(polyline_obj.data.vertices) < 2:
        raise RuntimeError(f"{polyline_obj.name}をポリラインとして認識するためには最低でも頂点が2つ以上必要です。")
    
    # メッシュに辺が1つ以上あるか
    if len(polyline_obj.data.edges) < 1:
        raise RuntimeError(f"{polyline_obj.name}をポリラインとして認識するためには最低でも辺が1つ以上必要です。")
    
    # メッシュに面が存在しないか
    if len(polyline_obj.data.polygons) > 0:
        raise RuntimeError(f"{polyline_obj.name}をポリラインとして認識するためには面が存在してはいけません。")
    
    # エッジ情報の辞書作成（{エッジ番号: (頂点番号1, 頂点番号2)}）
    edges_dict = {edge.index: (edge.vertices[0], edge.vertices[1]) for edge in polyline_obj.data.edges}
    
    # 頂点の他の頂点との接続関係を作成（{頂点番号: [接続頂点番号,...]}）
    vertex_connections = {}
    for v1, v2 in edges_dict.values():
        vertex_connections.setdefault(v1, []).append(v2)
        vertex_connections.setdefault(v2, []).append(v1)
    
    # 頂点接続情報から始点・終点を探す
    endpoints = []
    for vertex, connection in vertex_connections.items():
        if len(connection) == 0:
            raise RuntimeError(f"{polyline_obj.name}の頂点{vertex}は他のどの頂点とも接続されていません。不正なポリラインです。")
        elif len(connection) == 1:
            endpoints.append(vertex)
        elif len(connection) == 2:
            continue # 中間点なのでOK
        else:
            raise RuntimeError(f"{polyline_obj.name}の頂点{vertex}は{len(connection)}個の頂点と接続されています。分岐があるため線形ポリラインではありません。")
    
    # 始点・終点が正しく2つ見つかったか確認
    if len(endpoints) != 2:
        raise RuntimeError(f"{polyline_obj.name}からポリラインの始点/終点が正しく見つかりません。頂点に始点/終点のないループ形状になっている可能性があります。")
    
    # 指定された座標に近いほうを始点とする
    v0 = polyline_obj.data.vertices[endpoints[0]].co
    v1 = polyline_obj.data.vertices[endpoints[1]].co
    d0 = (v0 - start_point).length
    d1 = (v1 - start_point).length
    current = endpoints[0] if d0 <= d1 else endpoints[1]
    
    # 始点から線形に接続されている頂点座標配列を作成
    line_points = []
    visited = set()
    prev = None
    while True:
        # 探索頂点の座標を追加
        line_points.append(polyline_obj.data.vertices[current].co.copy())
        visited.add(current)
        
        # 次の頂点を探す（探索頂点が接続している前の頂点じゃない頂点）
        next_candidates = [vertex for vertex in vertex_connections[current] if vertex != prev]
        if not next_candidates:
            break  # 次の頂点がない場合は終点
        
        # 前の頂点、探索頂点を更新
        prev = current
        current = next_candidates[0]
    
    return line_points

# 線形の頂点座標配列の全長(m)
def total_line_points_length(line_points) -> float:
    """
    頂点座標配列(points)から全長(m)を返す。
    各頂点間の距離を合計した値。
    """
    if len(line_points) < 2:
        return 0.0

    line_length = 0.0
    for i in range(1, len(line_points)):
        line_length += (line_points[i] - line_points[i-1]).length
    return line_length

# 線形の頂点座標配列の始点から指定距離(m)の座標
def line_points_to_point(line_points, target_distance):
    """
    頂点座標配列(points)から target_distance(m) の位置の座標を返す。
    target_distance が全長を超える場合は終点を返す。
    """
    if len(line_points) < 2:
        raise RuntimeError("座標配列が2点未満のため補間できません。")
    
    # 累積距離を計算
    distances = [0.0]
    for i in range(1, len(line_points)):
        d = (line_points[i] - line_points[i-1]).length
        distances.append(distances[-1] + d)
    
    line_length = distances[-1]
    if target_distance >= line_length:
        return line_points[-1]
    
    # 指定距離が属するセグメントを探す
    for i in range(1, len(distances)):
        if distances[i] >= target_distance:
            t = (target_distance - distances[i-1]) / (distances[i] - distances[i-1] + 1e-12)
            return line_points[i-1].lerp(line_points[i], t)
    
    return line_points[-1]

# 線形の頂点座標配列からオフセット曲線を生成
def line_points_to_offset_line_points(line_points, offset):
    up = Vector((0,0,1))
    offset_segments = []
    for i in range(len(line_points)-1):
        p1, p2 = line_points[i], line_points[i+1]
        d = (p2 - p1).normalized()
        # XY平面での直交方向を計算
        d2d = Vector((d.x, d.y, 0)).normalized()
        n = Vector((-d2d.y, d2d.x, 0))
        offset_segments.append((p1 + n*offset, p2 + n*offset))
    
    offset_points = []
    offset_points.append(offset_segments[0][0])
    
    for i in range(len(offset_segments)-1):
        seg1 = offset_segments[i]
        seg2 = offset_segments[i+1]
        inter = geometry.intersect_line_line(seg1[0], seg1[1], seg2[0], seg2[1])
        if inter:
            offset_points.append(inter[0])
        else:
            offset_points.append(seg1[1])
    
    offset_points.append(offset_segments[-1][1])
    return offset_points

# 2点の座標を直線で繋ぐ線形の頂点座標配列を生成
def two_points_to_line_points(start_point, end_point, sample_distance):
    """
    start_point    : 始点座標
    end_point      : 終点座標
    sample_distance: サンプリング間隔(m)
    """
    # 2点間をサンプリング
    sampled_points = []
    dist = 0.0
    total_length = (end_point - start_point).length
    direction = (end_point - start_point).normalized()
    
    while dist <= total_length:
        sampled_points.append(start_point + direction * dist)
        dist += sample_distance
    sampled_points.append(end_point)
    
    return sampled_points

# 線形の頂点座標配列からポリラインを生成
def create_polyline_from_line_points(polyline_name, line_points):
    """
    polyline_name   : 作成するポリラインオブジェクト名
    line_points      : 線形の頂点座標配列
    """
    # メッシュを作成
    verts = [(p.x, p.y, p.z) for p in line_points]
    edges = [(i, i+1) for i in range(len(line_points)-1)]
    faces = []
    
    mesh_data = bpy.data.meshes.new(polyline_name + "_mesh")
    mesh_data.from_pydata(verts, edges, faces)
    mesh_data.update()
    
    # オブジェクトを作成
    polyline_obj_new = bpy.data.objects.new(polyline_name, mesh_data)
    bpy.context.collection.objects.link(polyline_obj_new)
    
    return polyline_obj_new

# ポリラインからメッシュを生成
def create_road_mesh_from_polyline(polyline_obj):
    # ポリラインから頂点座標配列と全長を取得
    line_points = polyline_to_line_points(polyline_obj, Vector((0,0,0)))
    total_length = total_line_points_length(line_points)
    
    # 頂点間距離(m)
    vertex_distance = polyline_obj.get("vertex_distance")
    if vertex_distance <= 0:
        raise RuntimeError("頂点間距離(m)が0以下になっています。")
    
    # ライン幅(m)
    line_width = polyline_obj.get("line_width")
    if line_width <= 0:
        raise RuntimeError("ライン幅(m)が0以下になっています。")
    half_width = line_width / 2.0
    
    # マテリアル
    material = polyline_obj.get("material")
    if not material:
        raise RuntimeError("マテリアルの取得に失敗しました。")
    
    # 路面標示のラインを破線にするか
    is_dash = polyline_obj.get("is_dash", False)
    dash_length = 5
    dash_gap = 5
    if is_dash:
        # 破線の長さ
        dash_length = polyline_obj.get("dash_length")
        if dash_length <= 0:
            raise RuntimeError("破線の長さ(m)が0以下になっています。")
        
        dash_gap = polyline_obj.get("dash_gap")
        if dash_gap <= 0:
            raise RuntimeError("破線の間隔(m)が0以下になっています。")
    
    # 高さオフセット
    height_offset = polyline_obj.get("height_offset", 0)
    up = Vector((0, 0, 1))
    z_offset = up * height_offset
    
    # 生成オフセット
    generate_offset_start = polyline_obj.get("generate_offset_start", 0.0)
    generate_offset_end   = polyline_obj.get("generate_offset_end", 0.0)
    start_dist = generate_offset_start
    end_dist   = total_length - generate_offset_end
    if end_dist <= start_dist:
        raise RuntimeError("generate_offset_start/endによるメッシュ生成オフセットで生成範囲が無くなっています。")
    
    # サンプリング（距離ベース）
    new_verts = []
    new_faces = []
    if not is_dash:
        # 実線：頂点間距離(m)ごとにサンプリングして帯状メッシュ
        sampled_points = []
        dist = start_dist
        while dist <= end_dist:
            sampled_points.append(line_points_to_point(line_points, dist))
            dist += vertex_distance
        sampled_points.append(line_points_to_point(line_points, end_dist))
        
        # 頂点生成
        left_indices = []
        right_indices = []
        for i, p in enumerate(sampled_points):
            if i == 0:
                direction = (sampled_points[i+1] - p).normalized()
            elif i == len(sampled_points)-1:
                direction = (p - sampled_points[i-1]).normalized()
            else:
                dir1 = (p - sampled_points[i-1]).normalized()
                dir2 = (sampled_points[i+1] - p).normalized()
                direction = (dir1 + dir2).normalized()
            side = direction.cross(up).normalized()
            v_left  = p + side * half_width + z_offset
            v_right = p - side * half_width + z_offset
            idx_left = len(new_verts); new_verts.append(v_left)
            idx_right = len(new_verts); new_verts.append(v_right)
            left_indices.append(idx_left); right_indices.append(idx_right)
        
        # 面生成
        for i in range(len(sampled_points)-1):
            new_faces.append((left_indices[i], right_indices[i], right_indices[i+1], left_indices[i+1]))
    else:
        # 破線：dash_lengthとdash_gapを繰り返して破線を生成
        dist = start_dist
        while dist < end_dist:
            # 破線区間の終点
            dash_end = min(dist + dash_length, end_dist)
            
            # 破線区間を頂点間距離(m)ごとにサンプリング
            dash_points = []
            d = dist
            while d <= dash_end:
                dash_points.append(line_points_to_point(line_points, d))
                d += vertex_distance
            dash_points.append(line_points_to_point(line_points, dash_end))  # 終点を追加
            
            # 頂点生成
            left_indices = []
            right_indices = []
            for i, p in enumerate(dash_points):
                if i == 0:
                    direction = (dash_points[i+1] - p).normalized()
                elif i == len(dash_points)-1:
                    direction = (p - dash_points[i-1]).normalized()
                else:
                    dir1 = (p - dash_points[i-1]).normalized()
                    dir2 = (dash_points[i+1] - p).normalized()
                    direction = (dir1 + dir2).normalized()
                side = direction.cross(up).normalized()
                v_left  = p + side * half_width + z_offset
                v_right = p - side * half_width + z_offset
                idx_left = len(new_verts); new_verts.append(v_left)
                idx_right = len(new_verts); new_verts.append(v_right)
                left_indices.append(idx_left); right_indices.append(idx_right)
            
            # 面生成
            for i in range(len(dash_points)-1):
                new_faces.append((left_indices[i], right_indices[i],
                                  right_indices[i+1], left_indices[i+1]))
            
            # gap 区間をスキップ
            dist = dash_end + dash_gap
    
    # メッシュ作成
    mesh_data = bpy.data.meshes.new(polyline_obj.name + "_mesh")
    mesh_data.from_pydata(new_verts, [], new_faces)
    mesh_data.update()
    
    mesh_obj = bpy.data.objects.new(polyline_obj.name + "_obj", mesh_data)
    bpy.context.collection.objects.link(mesh_obj)
    
    # マテリアル適用
    if material:
        if mesh_obj.data.materials:
            mesh_obj.data.materials[0] = material
        else:
            mesh_obj.data.materials.append(material)
    
    return mesh_obj

"""
オブジェクトのカスタムプロパティ・ビューポート表示
"""
viewport_white_solid_line_color = (0.0, 0.0, 1.0, 1.0)
viewport_white_dash_line_color = (0.0, 0.85, 1.0, 1.0)
viewport_yellow_solid_line_color = (1.0, 0.15, 0.0, 1.0)
viewport_yellow_dash_line_color = (1.0, 0.85, 0.0, 1.0)
viewport_stop_line_color = (1.0, 0.0, 0.9, 1.0)
viewport_crosswalk_color = (0.0, 1.0, 0.0, 1.0)

# 中央線のカスタムプロパティを設定
def set_property_center_line(context, polyline_obj) -> None:
    viewport_color = viewport_white_solid_line_color
    material = context.scene.WhiteLineMaterial
    if context.scene.center_line_yellow:
        material = context.scene.YellowLineMaterial
        if context.scene.center_line_dash:
            viewport_color = viewport_yellow_dash_line_color # 黄色_破線
        else:
            viewport_color = viewport_yellow_solid_line_color # 黄色_実線
    else:
        material = context.scene.WhiteLineMaterial
        if context.scene.center_line_dash:
            viewport_color = viewport_white_dash_line_color # 白色_破線
        else:
            viewport_color = viewport_white_solid_line_color # 白線_実線
    
    # 路面標示ポリラインのカスタムプロパティ設定
    set_road_line_property(
        polyline_obj,
        viewport_color, # ビューポートカラー
        material,
        context.scene.sample_distance,
        context.scene.height_offset,
        context.scene.default_line_width, # ライン幅(m)
        context.scene.center_line_dash,        # 破線フラグ
        context.scene.center_line_dash_length, # 破線の長さ(m)
        context.scene.center_line_dash_gap,  # 破線の間隔(m)
        context.scene.center_line_generate_offset_start, # 生成オフセット(m)始点側
        context.scene.center_line_generate_offset_end    # 生成オフセット(m)終点側
    )

# 車道外側線のカスタムプロパティを設定
def set_property_outside_lane_line(context, polyline_obj) -> None:
    # 路面標示ポリラインのカスタムプロパティ設定
    set_road_line_property(
        polyline_obj,
        viewport_white_solid_line_color, # ビューポートカラー
        context.scene.WhiteLineMaterial, # 白色マテリアル
        context.scene.sample_distance,
        context.scene.height_offset,
        context.scene.default_line_width, # ライン幅(m)
        False,                                        # 破線フラグ
        context.scene.lane_boundary_line_dash_length, # 破線の長さ(m)
        context.scene.lane_boundary_line_dash_gap,  # 破線の間隔(m)
        0.0, # 生成オフセット(m)始点側
        0.0  # 生成オフセット(m)終点側
    )

# 車線境界線のカスタムプロパティを設定
def set_property_lane_boundary_line(context, polyline_obj):
    viewport_color = viewport_white_dash_line_color if context.scene.lane_boundary_line_dash else viewport_white_solid_line_color
    
    # 路面標示ポリラインのカスタムプロパティ設定
    set_road_line_property(
        polyline_obj,
        viewport_color, # ビューポートカラー
        context.scene.WhiteLineMaterial, # 白色マテリアル
        context.scene.sample_distance,
        context.scene.height_offset,
        context.scene.default_line_width, # ライン幅(m)
        context.scene.lane_boundary_line_dash,        # 破線フラグ
        context.scene.lane_boundary_line_dash_length, # 破線の長さ(m)
        context.scene.lane_boundary_line_dash_gap,  # 破線の間隔(m)
        context.scene.lane_boundary_line_generate_offset_start, # 生成オフセット(m)始点側
        context.scene.lane_boundary_line_generate_offset_end    # 生成オフセット(m)終点側
    )

# 停止線のカスタムプロパティを設定
def set_property_stop_line(context, polyline_obj):
    generate_offset = context.scene.default_line_width/2.0 if context.scene.stop_line_add_generate_offset else 0.0
    
    # 路面標示ポリラインのカスタムプロパティ設定
    set_road_line_property(
        polyline_obj,
        viewport_stop_line_color, # ビューポートカラー
        context.scene.WhiteLineMaterial, # 白色マテリアル
        context.scene.sample_distance,
        context.scene.height_offset,
        context.scene.stop_line_width, # ライン幅(m)
        False,                                        # 破線フラグ
        context.scene.lane_boundary_line_dash_length, # 破線の長さ(m)
        context.scene.lane_boundary_line_dash_gap,  # 破線の間隔(m)
        generate_offset, # 生成オフセット(m)始点側
        generate_offset  # 生成オフセット(m)終点側
    )

# 横断歩道のカスタムプロパティを設定
def set_property_crosswalk(context, polyline_obj):
    # 路面標示ポリラインのカスタムプロパティ設定
    set_road_line_property(
        polyline_obj,
        viewport_crosswalk_color, # ビューポートカラー
        context.scene.WhiteLineMaterial, # 白色マテリアル
        context.scene.sample_distance,
        context.scene.height_offset,
        context.scene.crosswalk_width, # ライン幅(m)
        True,                                # 破線フラグ
        context.scene.crosswalk_dash_length, # 破線の長さ(m)
        context.scene.crosswalk_dash_gap,  # 破線の間隔(m)
        context.scene.crosswalk_generate_offset_start, # 生成オフセット(m)始点側
        context.scene.crosswalk_generate_offset_end    # 生成オフセット(m)終点側
    )

# 路面標示ポリラインのカスタムプロパティ設定
def set_road_line_property(polyline_obj, viewport_color, material,
                           vertex_distance : float, height_offset : float, line_width : float,
                           isDash : bool, dash_length : float, dash_gap : float,
                           generate_offset_start : float, generate_offset_end : float):
    # ビューポート表示を変更
    polyline_obj.show_in_front = True         # 最前面
    polyline_obj.display.show_shadows = False # 影
    polyline_obj.color = viewport_color       # カラー
    polyline_obj.display_type = 'WIRE'        # 表示タイプ
    
    # カスタムプロパティを設定
    polyline_obj["vertex_distance"] = vertex_distance # サンプリング距離(m)
    polyline_obj["height_offset"] = height_offset # 高さオフセット(m)
    polyline_obj["line_width"] = line_width # ライン幅(m)
    polyline_obj["material"] = material # マテリアル
    polyline_obj["is_dash"] = isDash # 破線フラグ
    polyline_obj["dash_length"] = dash_length # 破線の距離(m)
    polyline_obj["dash_gap"] = dash_gap # 破線の間隔(m)
    polyline_obj["generate_offset_start"] = generate_offset_start # 生成オフセット(m)始点側
    polyline_obj["generate_offset_end"] = generate_offset_end # 生成オフセット(m)終点側

"""
路面標示ポリラインの自動生成
ベースポリラインから路面標示ポリラインを自動生成する
"""
# 路面標示ポリラインの自動生成：処理
class GEOTOOL_BaseLineToRoadLine(bpy.types.Operator):
    bl_idname = "object.base_line_to_road_line"
    bl_label = "BaseLineToRoadLine"
    bl_description = "ベースポリラインから路面標示ポリラインを生成"
    dialog_message = ""
    
    # 処理関数(固定名)
    def execute(self, context):
        self.report({'INFO'}, f"{self.bl_label}.execute()")
        start_time = time.time()
        
        # ビュー視点をトップに変更
        try:
            # 3Dビューポートを表示しているエリアを取得
            areas  = [area for area in bpy.context.window.screen.areas if area.type == 'VIEW_3D']
            # 最初の3Dビューポートの視点をトップに変更
            with bpy.context.temp_override(
                window=bpy.context.window,
                area=areas[0],
                region=[region for region in areas[0].regions if region.type == 'WINDOW'][0],
                screen=bpy.context.window.screen
            ): 
                bpy.ops.view3d.view_axis(type='TOP')
                bpy.context.region_data.update()
        except Exception as e:
            self.report({'ERROR'}, f"ビュー視点をトップに変更できませんでした。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # オブジェクトモードに移行する
        try:
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        except Exception as e:
            self.report({'ERROR'}, f"オブジェクトモードへの切り替えに失敗しました。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # ベースポリラインの正規化・ロック処理
        try:
            # ベースポリラインの位置・回転・スケールを適用（正規化）
            if not is_transform_normalized(context.scene.BaseLineObject):
                bpy.ops.object.select_all(action='DESELECT')
                context.scene.BaseLineObject.select_set(True)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            # ベースポリラインの位置・回転・スケールをロック
            if not is_transform_locked(context.scene.BaseLineObject):
                context.scene.BaseLineObject.lock_location[0] = True  # X位置をロック
                context.scene.BaseLineObject.lock_location[1] = True  # Y位置をロック
                context.scene.BaseLineObject.lock_location[2] = True  # Z位置をロック
                context.scene.BaseLineObject.lock_rotation[0] = True  # X回転をロック
                context.scene.BaseLineObject.lock_rotation[1] = True  # Y回転をロック
                context.scene.BaseLineObject.lock_rotation[2] = True  # Z回転をロック
                context.scene.BaseLineObject.lock_scale[0] = True     # Xスケールをロック
                context.scene.BaseLineObject.lock_scale[1] = True     # Yスケールをロック
                context.scene.BaseLineObject.lock_scale[2] = True     # Zスケールをロック
        except Exception as e:
            self.report({'ERROR'}, f"ベースポリライン'{context.scene.BaseLineObject.name}'の正規化・ロックに失敗しました。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # 路面標示ポリライン用コレクションを取得
        try:
            # ベースポリラインの親コレクションを取得
            parent_collection = context.scene.BaseLineObject.users_collection[0]
            
            # 指定した親コレクションから路面標示ポリライン用コレクションを取得・新規作成
            context.scene.RoadLineCollection = get_or_create_collection(f"{context.scene.BaseLineObject.name}ToRoadLine", parent_collection)
            if not context.scene.RoadLineCollection:
                raise RuntimeError("not RoadLineCollection.")
            
            # 必要ならコレクションの初期化
            if context.scene.ClearCollection_RoadLinesToMesh:
                clear_collection(context.scene.RoadLineCollection)
        except Exception as e:
            self.report({'ERROR'}, f"路面標示ポリライン用コレクションの取得に失敗。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # ベースポリラインから頂点座標配列と全長を取得
        base_line_points = []
        base_line_length = 0.0
        try:
            # ポリラインから頂点座標配列を取得
            base_line_points = polyline_to_line_points(context.scene.BaseLineObject, Vector((0,0,0)))
            if len(base_line_points) < 2:
                raise RuntimeError("ポリラインの頂点座標が2点以上ありません。")
            
            # 頂点座標配列の全長を取得
            base_line_length = total_line_points_length(base_line_points)
            if base_line_length <= 0.0:
                raise RuntimeError("ポリラインの全長が0mです。")
        except Exception as e:
            self.report({'ERROR'}, f"路面標示ポリライン用コレクションの取得に失敗。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # 中央線のポリライン生成
        road_line_list = [] # 生成した路面標示ポリラインのオブジェクトリスト
        left_outside_lane_points = []  # 車道外側線_左の頂点座標配列
        left_outside_lane_length = 0.0
        right_outside_lane_points = [] # 車道外側線_右の頂点座標配列
        right_outside_lane_length = 0.0
        try:
            # 線種名
            center_line_name = "中央線"
            if context.scene.lane_left <= 0: # 左車線がない場合
                center_line_name = "車道外側線_左（中央）"
            elif context.scene.lane_right <= 0: # 右車線がない場合
                center_line_name = "車道外側線_右（中央）"
            
            # 路面標示ポリライン生成
            center_line_obj = create_polyline_from_line_points(center_line_name, base_line_points)
            road_line_list.append(center_line_obj)
            
            # 路面標示ポリラインのカスタムプロパティ設定
            if context.scene.lane_left <= 0:
                # 車道外側線_左
                set_property_outside_lane_line(context, center_line_obj)
                left_outside_lane_points = base_line_points
                left_outside_lane_length = base_line_length
            elif context.scene.lane_right <= 0:
                # 車道外側線_右
                set_property_outside_lane_line(context, center_line_obj)
                right_outside_lane_points = base_line_points
                right_outside_lane_length = base_line_length
            else:
                set_property_center_line(context, center_line_obj)
        except Exception as e:
            self.report({'ERROR'}, f"中央線ポリラインの生成に失敗しました。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # 左右車線のポリライン生成（車道外側線 / 車線境界線 / 停止線）
        for right_or_left in [True, False]:
            # 中央線を前回生成の車線として設定
            prev_points = base_line_points
            prev_length = base_line_length
            
            # 車線のオフセット（右車線 or 左車線で方向反転）
            lane_offset = (context.scene.lane_distance+context.scene.default_line_width) if right_or_left else -(context.scene.lane_distance+context.scene.default_line_width)
            
            # 車線数（右車線と左車線で変更）
            lanes = context.scene.lane_right if right_or_left else context.scene.lane_left
            index = 1
            while index <= lanes:
                # 線種名
                outside_lane_name = f"{'車道外側線' if index == lanes else '車線境界線'}_{'右' if right_or_left else '左'}_{index}"
                
                # 路面標示ポリライン生成
                outside_lane_obj = None
                outside_lane_points = []
                outside_lane_length = 0.0
                try:
                    # 中央線からのオフセットで左右車線を作成
                    outside_lane_points = line_points_to_offset_line_points(base_line_points, lane_offset*index)
                    outside_lane_length = total_line_points_length(outside_lane_points)
                    
                    # 車道外側線 or 車線境界線の生成が有効な時に生成
                    if index == lanes or context.scene.lane_boundary_line_generate:
                        outside_lane_obj = create_polyline_from_line_points(outside_lane_name, outside_lane_points)
                        road_line_list.append(outside_lane_obj)
                except Exception as e:
                    self.report({'ERROR'}, f"{outside_lane_name}の生成に失敗しました。\n詳細: {str(e)}")
                    return {'CANCELLED'}
                
                # 路面標示ポリラインのカスタムプロパティ設定
                if outside_lane_obj:
                    try:
                        if index == lanes:
                            # 車道外側線
                            set_property_outside_lane_line(context, outside_lane_obj)
                        else:
                            # 車線境界線
                            set_property_lane_boundary_line(context, outside_lane_obj)
                    except Exception as e:
                        self.report({'ERROR'}, f"{outside_lane_name}のカスタムプロパティの設定に失敗しました。\n詳細: {str(e)}")
                        return {'CANCELLED'}
                
                # 停止線ポリライン生成（始点 / 終点）
                for start_or_end in [True,False]:
                    # 始点側の生成時に生成が必要なければスキップ
                    if start_or_end and not context.scene.stop_line_generate_start:
                        continue
                    # 終点側の生成時に生成が必要なければスキップ
                    if not start_or_end and not context.scene.stop_line_generate_end:
                        continue
                    
                    # 停止線ポリライン生成
                    stop_line_obj = None
                    try:
                        # 停止線ポリライン名
                        stop_line_name = f"停止線_{'右' if right_or_left else '左'}_{'始点側' if start_or_end else '終点側'}_{index}"
                        
                        # 停止線開始始点
                        start_distance = context.scene.stop_line_position_offset if start_or_end else prev_length-context.scene.stop_line_position_offset
                        start_point = line_points_to_point(prev_points, start_distance)
                        
                        # 停止線終了地点
                        end_distance = context.scene.stop_line_position_offset if start_or_end else outside_lane_length-context.scene.stop_line_position_offset
                        end_point = line_points_to_point(outside_lane_points, end_distance)
                        
                        # 開始から終了への頂点配列生成
                        stop_line_points = two_points_to_line_points(start_point, end_point, context.scene.sample_distance)
                        
                        # 停止線ポリライン生成
                        stop_line_obj = create_polyline_from_line_points(stop_line_name, stop_line_points)
                        road_line_list.append(stop_line_obj)
                    except Exception as e:
                        self.report({'ERROR'}, f"{stop_line_name}の生成に失敗しました。\n詳細: {str(e)}")
                        return {'CANCELLED'}
                    
                    # 停止線ポリラインのカスタムプロパティ設定
                    try:
                        set_property_stop_line(context, stop_line_obj)
                    except Exception as e:
                        self.report({'ERROR'}, f"{stop_line_obj.name}のカスタムプロパティの設定に失敗しました。\n詳細: {str(e)}")
                        return {'CANCELLED'}
                
                prev_points = outside_lane_points
                prev_length = outside_lane_length
                index += 1
            
            # 車道外側線のバックアップ
            if right_or_left:
                right_outside_lane_points = prev_points
                right_outside_lane_length = prev_length
            else:
                left_outside_lane_points = prev_points
                left_outside_lane_length = prev_length
        
        # 横断歩道のポリライン生成（始点 / 終点）
        self.report({'INFO'}, f"横断歩道生成\n車道外側線_左：{len(left_outside_lane_points)}({left_outside_lane_length}m)\n車道外側線_右：{len(right_outside_lane_points)}({right_outside_lane_length}m)")
        for start_or_end in [True,False]:
            # 車道外側線_左～車道外側線_右で横断歩道生成
            # 始点側の生成時に生成が必要なければスキップ
            if start_or_end and not context.scene.crosswalk_generate_start:
                continue
            # 終点側の生成時に生成が必要なければスキップ
            if not start_or_end and not context.scene.crosswalk_generate_end:
                continue
            
            # 横断歩道ポリライン生成
            crosswalk_obj = None
            try:
                # 横断歩道ポリライン名
                crosswalk_name = f"横断歩道_{'始点側' if start_or_end else '終点側'}"
                
                # 横断歩道開始始点
                start_distance = context.scene.crosswalk_position_offset if start_or_end else left_outside_lane_length-context.scene.crosswalk_position_offset
                start_point = line_points_to_point(left_outside_lane_points, start_distance)
                
                # 横断歩道終了地点
                end_distance = context.scene.crosswalk_position_offset if start_or_end else right_outside_lane_length-context.scene.crosswalk_position_offset
                end_point = line_points_to_point(right_outside_lane_points, end_distance)
                
                # 開始から終了への頂点配列生成
                crosswalk_points = two_points_to_line_points(start_point, end_point, context.scene.sample_distance)
                
                # 横断歩道ポリライン生成
                crosswalk_obj = create_polyline_from_line_points(crosswalk_name, crosswalk_points)
                road_line_list.append(crosswalk_obj)
            except Exception as e:
                self.report({'ERROR'}, f"{crosswalk_name}の生成に失敗しました。\n詳細: {str(e)}")
                return {'CANCELLED'}
            
            # 横断歩道ポリラインのカスタムプロパティ設定
            try:
                set_property_crosswalk(context, crosswalk_obj)
            except Exception as e:
                self.report({'ERROR'}, f"{crosswalk_obj.name}のカスタムプロパティの設定に失敗しました。\n詳細: {str(e)}")
                return {'CANCELLED'}
        
        # 路面標示ポリラインのコレクション移動
        try:
            for road_line in road_line_list:
                # 路面標示ポリライン用コレクション以外のリンク解除
                for coll in list(road_line.users_collection):
                    if coll != context.scene.RoadLineCollection:
                        coll.objects.unlink(road_line)
                
                # 路面標示ポリライン用コレクションにリンクされていなければ登録
                if not any(obj is road_line for obj in context.scene.RoadLineCollection.objects):
                    context.scene.RoadLineCollection.objects.link(road_line)
        except Exception as e:
            self.report({'ERROR'}, f"路面標示ポリラインのコレクション移動に失敗しました。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # 路面標示ポリラインの正規化・ロック処理
        for road_line in road_line_list:
            # 路面標示ポリラインの位置・回転・スケールを適用（正規化）
            if not is_transform_normalized(road_line):
                bpy.ops.object.select_all(action='DESELECT')
                road_line.select_set(True)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            # 路面標示ポリラインの位置・回転・スケールをロック
            if not is_transform_locked(road_line):
                road_line.lock_location[0] = True  # X位置をロック
                road_line.lock_location[1] = True  # Y位置をロック
                road_line.lock_location[2] = True  # Z位置をロック
                road_line.lock_rotation[0] = True  # X回転をロック
                road_line.lock_rotation[1] = True  # Y回転をロック
                road_line.lock_rotation[2] = True  # Z回転をロック
                road_line.lock_scale[0] = True     # Xスケールをロック
                road_line.lock_scale[1] = True     # Yスケールをロック
                road_line.lock_scale[2] = True     # Zスケールをロック
        
        self.report({'INFO'}, f"処理時間：{(time.time() - start_time):.3f}秒")
        return {'FINISHED'}
    
    # GUIから呼ばれる関数(固定名)
    def invoke(self, context, event):
        self.report({'INFO'}, f"{self.bl_label}.invoke()")
        
        # 白色のマテリアルが指定されていない場合は中断
        if not context.scene.WhiteLineMaterial:
            self.report({'ERROR'}, "白色のマテリアルが指定されていません。\n白線のマテリアルとして路面標示ポリラインのカスタムプロパティに設定するのに使用します。\n路面標示ポリラインからメッシュ生成時にマテリアルとして設定されます。")
            return {'CANCELLED'}
        
        # 中央線が黄色の場合
        if context.scene.center_line_yellow:
            # 黄色のマテリアルが指定されていなければ中断
            if not context.scene.YellowLineMaterial:
                self.report({'ERROR'}, "中央線が黄色の場合は黄色のマテリアルを指定してください。\n黄色のマテリアルとして路面標示ポリライン（中央線）のカスタムプロパティに設定するのに使用します。\n路面標示ポリラインからメッシュ生成時にマテリアルとして設定されます。")
                return {'CANCELLED'}
        
        # 車線数が0の場合
        if context.scene.lane_left + context.scene.lane_right <= 0:
            self.report({'ERROR'}, "左右の車線数が0のため生成できる路面標示がありません。")
            return {'CANCELLED'}
        
        # ベースポリラインがポリラインかチェック
        try:
            polyline_to_line_points(context.scene.BaseLineObject, Vector((0,0,0)))
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        # ベースポリラインが正規化・ロックされているか
        is_normalized = is_transform_normalized(context.scene.BaseLineObject)
        is_locked = is_transform_locked(context.scene.BaseLineObject)
        if is_normalized and is_locked:
            return self.execute(context)
        else:
            # 確認ダイアログを表示
            if not is_normalized and not is_locked:
                self.dialog_message = f"'{context.scene.BaseLineObject.name}'は正規化・ロックされていません。\n自動で正規化・ロックして処理を継続しますか？"
            elif not is_normalized:
                self.dialog_message = f"'{context.scene.BaseLineObject.name}'は正規化されていません。\n自動で正規化して処理を継続しますか？"
            else:
                self.dialog_message = f"'{context.scene.BaseLineObject.name}'はロックされていません。\n自動でロックして処理を継続しますか？"
            return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        for message in self.dialog_message.splitlines(): # 改行で分割
            self.layout.label(text=message)

# 路面標示ポリラインの自動生成：UI
class GEOTOOL_BaseLineToRoadLine_Panel(bpy.types.Panel):
    bl_label = "1.路面標示ポリラインの自動生成"
    bl_idname = "1_BaseLineToRoadLine"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TOOL"
    
    def draw(self, context):
        self.layout.prop_search(context.scene, "BaseLineObject", context.scene, "objects", text="ベース")
        
        # 共通設定
        common_box = self.layout.box()
        common_column = common_box.column(align=True)
        common_column.prop(context.scene, "WhiteLineMaterial", text="白色")
        common_column.prop(context.scene, "sample_distance", text="サンプリング距離(m)")
        common_column.prop(context.scene, "height_offset", text="高さオフセット(m)")
        common_column.prop(context.scene, "default_line_width", text="ライン幅(m)")
        common_column.prop(context.scene, "lane_distance", text="レーン間距離(m)")
        common_lane_row = common_column.row(align=True)
        common_lane_row.prop(context.scene, "lane_left", text="左車線数")
        common_lane_row.prop(context.scene, "lane_right", text="右車線数")
        
        # 中央線（左右に1車線以上ある場合）
        if context.scene.lane_left >= 1 and context.scene.lane_right >= 1:
            center_line_box = self.layout.box()
            center_line_column = center_line_box.column(align=True)
            # 中央線が黄色
            center_line_column.prop(context.scene, "center_line_yellow", text="中央線が黄色")
            if context.scene.center_line_yellow:
                center_line_column.prop(context.scene, "YellowLineMaterial", text="黄色")
            # 中央線のメッシュ生成オフセット
            center_line_column.label(text="中央線の生成オフセット(m)")
            center_line_generate_offset_row = center_line_column.row(align=True)
            center_line_generate_offset_row.prop(context.scene, "center_line_generate_offset_start", text="始点側")
            center_line_generate_offset_row.prop(context.scene, "center_line_generate_offset_end", text="終点側")
            # 中央線が破線
            center_line_column.prop(context.scene, "center_line_dash", text="中央線が破線")
            if context.scene.center_line_dash:
                center_line_column.prop(context.scene, "center_line_dash_length", text="中央線の破線の長さ(m)")
                center_line_column.prop(context.scene, "center_line_dash_gap", text="中央線の破線の間隔(m)")
        
        # 車線境界線（左右どちらかが2車線以上の場合）
        if 2 <= context.scene.lane_left or 2 <= context.scene.lane_right:
            lane_boundary_line_box = self.layout.box()
            lane_boundary_line_column = lane_boundary_line_box.column(align=True)
            # 車線境界線の生成
            lane_boundary_line_column.prop(context.scene, "lane_boundary_line_generate", text="車線境界線を生成")
            if context.scene.lane_boundary_line_generate:
                # 車線境界線のメッシュ生成オフセット
                lane_boundary_line_column.label(text="車線境界線の生成オフセット(m)")
                lane_boundary_line_generate_offset_row = lane_boundary_line_column.row(align=True)
                lane_boundary_line_generate_offset_row.prop(context.scene, "lane_boundary_line_generate_offset_start", text="始点側")
                lane_boundary_line_generate_offset_row.prop(context.scene, "lane_boundary_line_generate_offset_end", text="終点側")
                # 車線境界線が破線
                lane_boundary_line_column.prop(context.scene, "lane_boundary_line_dash", text="車線境界線が破線")
                if context.scene.lane_boundary_line_dash:
                    lane_boundary_line_column.prop(context.scene, "lane_boundary_line_dash_length", text="車線境界線の破線の長さ(m)")
                    lane_boundary_line_column.prop(context.scene, "lane_boundary_line_dash_gap", text="車線境界線の破線の間隔(m)")
        
        # 車道外側線 / 横断歩道 / 停止線（左右どちらかが1車線以上の場合）
        if 1 <= context.scene.lane_left or 1 <= context.scene.lane_right:
            # 車道外側線
            outside_lane_line_box = self.layout.box()
            outside_lane_line_column = outside_lane_line_box.column(align=True)
            # 車道外側線のメッシュ生成オフセット
            outside_lane_line_column.label(text="車道外側線の生成オフセット(m)")
            outside_lane_line_generate_offset_row = outside_lane_line_column.row(align=True)
            outside_lane_line_generate_offset_row.prop(context.scene, "outside_lane_line_generate_offset_start", text="始点側")
            outside_lane_line_generate_offset_row.prop(context.scene, "outside_lane_line_generate_offset_end", text="終点側")
            
            # 横断歩道
            crosswalk_box = self.layout.box()
            crosswalk_column = crosswalk_box.column(align=True)
            crosswalk_column.label(text="横断歩道の生成")
            crosswalk_generate_row = crosswalk_column.row(align=True)
            crosswalk_generate_row.prop(context.scene, "crosswalk_generate_start", text="始点側")
            crosswalk_generate_row.prop(context.scene, "crosswalk_generate_end", text="終点側")
            if context.scene.crosswalk_generate_start or context.scene.crosswalk_generate_end:
                crosswalk_column.prop(context.scene, "crosswalk_width", text="横断歩道の幅(m)")
                crosswalk_column.prop(context.scene, "crosswalk_position_offset", text="横断歩道の位置オフセット(m)")
                crosswalk_column.prop(context.scene, "crosswalk_dash_length", text="横断歩道の破線の長さ(m)")
                crosswalk_column.prop(context.scene, "crosswalk_dash_gap", text="横断歩道の破線の間隔(m)")
                crosswalk_column.label(text="横断歩道の生成オフセット(m)")
                crosswalk_generate_offset_row = crosswalk_column.row(align=True)
                crosswalk_generate_offset_row.prop(context.scene, "crosswalk_generate_offset_start", text="始点側")
                crosswalk_generate_offset_row.prop(context.scene, "crosswalk_generate_offset_end", text="終点側")
            
            # 停止線
            stop_line_box = self.layout.box()
            stop_line_column = stop_line_box.column(align=True)
            stop_line_column.label(text="停止線の生成")
            stop_line_generate_row = stop_line_column.row(align=True)
            stop_line_generate_row.prop(context.scene, "stop_line_generate_start", text="始点側")
            stop_line_generate_row.prop(context.scene, "stop_line_generate_end", text="終点側")
            if context.scene.stop_line_generate_start or context.scene.stop_line_generate_end:
                stop_line_column.prop(context.scene, "stop_line_width", text="停止線の幅(m)")
                stop_line_column.prop(context.scene, "stop_line_position_offset", text="停止線の位置オフセット(m)")
                stop_line_column.prop(context.scene, "stop_line_add_generate_offset", text="ライン幅の生成オフセット追加")
        
        create_column = self.layout.column(align=True)
        create_column.prop(context.scene, "ClearCollection_BaseLineToRoadLine", text="生成先のコレクションを初期化")
        create_column.operator(GEOTOOL_BaseLineToRoadLine.bl_idname, text="路面標示ポリライン生成", icon="PLAY")

# 路面標示ポリラインの自動生成：登録
def GEOTOOL_BaseLineToRoadLine_register():
    bpy.utils.register_class(GEOTOOL_BaseLineToRoadLine)
    bpy.utils.register_class(GEOTOOL_BaseLineToRoadLine_Panel)
    
    bpy.types.Scene.BaseLineObject = bpy.props.PointerProperty(
        name="BaseLineObject",
        type=bpy.types.Object,
        description="路面標示ポリライン生成のベースポリライン"
    )
    bpy.types.Scene.WhiteLineMaterial = bpy.props.PointerProperty(
        name="WhiteLineMaterial",
        type=bpy.types.Material,
        description="白線のマテリアル"
    )
    bpy.types.Scene.sample_distance = bpy.props.FloatProperty(
        name="sample_distance",
        description="サンプリング距離(m)",
        default=5.0,
        min = 0.1,
        max = 50.0
    )
    bpy.types.Scene.height_offset = bpy.props.FloatProperty(
        name="height_offset",
        description="高さオフセット(m)",
        default=0.01,
        min = -100.0,
        max = 100.0
    )
    bpy.types.Scene.default_line_width = bpy.props.FloatProperty(
        name="default_line_width",
        description="ライン幅(m)",
        default=0.17,
        min = 0.01,
        max = 10.0
    )
    bpy.types.Scene.lane_distance = bpy.props.FloatProperty(
        name="lane_distance",
        description="レーン間距離(m)",
        default=1.25,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.lane_left = bpy.props.IntProperty(
        name="lane_left",
        description="左車線数",
        default=2,
        min = 0,
        max = 10
    )
    bpy.types.Scene.lane_right = bpy.props.IntProperty(
        name="lane_right",
        description="右車線数",
        default=2,
        min = 0,
        max = 10
    )
    bpy.types.Scene.center_line_yellow = bpy.props.BoolProperty(
        name="center_line_yellow",
        description="中央線が黄色かどうか",
        default=True
    )
    bpy.types.Scene.YellowLineMaterial = bpy.props.PointerProperty(
        name="YellowLineMaterial",
        type=bpy.types.Material,
        description="黄線のマテリアル"
    )
    bpy.types.Scene.center_line_generate_offset_start = bpy.props.FloatProperty(
        name="center_line_generate_offset_start",
        description="中央線の始点側のメッシュ生成オフセット距離(m)",
        default=5.65,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.center_line_generate_offset_end = bpy.props.FloatProperty(
        name="center_line_generate_offset_end",
        description="中央線の終点側のメッシュ生成オフセット距離(m)",
        default=5.65,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.center_line_dash = bpy.props.BoolProperty(
        name="center_line_dash",
        description="中央線が破線かどうか",
        default=True
    )
    bpy.types.Scene.center_line_dash_length = bpy.props.FloatProperty(
        name="center_line_dash_length",
        description="中央線の破線の長さ(m)",
        default=5.0,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.center_line_dash_gap = bpy.props.FloatProperty(
        name="center_line_dash_gap",
        description="中央線の破線の間隔(m)",
        default=5.0,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.lane_boundary_line_generate = bpy.props.BoolProperty(
        name="lane_boundary_line_generate",
        description="車線境界線を生成するかどうか",
        default=True
    )
    bpy.types.Scene.lane_boundary_line_generate_offset_start = bpy.props.FloatProperty(
        name="lane_boundary_line_generate_offset_start",
        description="車線境界線の始点側のメッシュ生成オフセット(m)",
        default=5.65,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.lane_boundary_line_generate_offset_end = bpy.props.FloatProperty(
        name="lane_boundary_line_generate_offset_end",
        description="車線境界線の終点側のメッシュ生成オフセット(m)",
        default=5.65,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.lane_boundary_line_dash = bpy.props.BoolProperty(
        name="lane_boundary_line_dash",
        description="車線境界線が破線かどうか",
        default=True
    )
    bpy.types.Scene.lane_boundary_line_dash_length = bpy.props.FloatProperty(
        name="lane_boundary_line_dash_length",
        description="車線境界線の破線の長さ(m)",
        default=3.0,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.lane_boundary_line_dash_gap = bpy.props.FloatProperty(
        name="lane_boundary_line_dash_gap",
        description="車線境界線の破線の間隔(m)",
        default=3.0,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.outside_lane_line_generate_offset_start = bpy.props.FloatProperty(
        name="outside_lane_line_generate_offset_start",
        description="車道外側線の始点側のメッシュ生成オフセット(m)",
        default=0.0,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.outside_lane_line_generate_offset_end = bpy.props.FloatProperty(
        name="outside_lane_line_generate_offset_end",
        description="車道外側線の終点側のメッシュ生成オフセット(m)",
        default=0.0,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.crosswalk_generate_start = bpy.props.BoolProperty(
        name="crosswalk_generate_start",
        description="ベースポリラインの始点に横断歩道を生成するかどうか",
        default=True
    )
    bpy.types.Scene.crosswalk_generate_end = bpy.props.BoolProperty(
        name="crosswalk_generate_end",
        description="ベースポリラインの終点に横断歩道を生成するかどうか",
        default=True
    )
    bpy.types.Scene.crosswalk_width = bpy.props.FloatProperty(
        name="crosswalk_width",
        description="横断歩道の幅(m)",
        default=3.0,
        min = 0.01,
        max = 10.0
    )
    bpy.types.Scene.crosswalk_position_offset = bpy.props.FloatProperty(
        name="crosswalk_position_offset",
        description="横断歩道の位置オフセット(m)",
        default=2.0,
        min = 0.0,
        max = 10.0
    )
    bpy.types.Scene.crosswalk_dash_length = bpy.props.FloatProperty(
        name="crosswalk_dash_length",
        description="横断歩道の破線の長さ(m)",
        default=0.45,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.crosswalk_dash_gap = bpy.props.FloatProperty(
        name="crosswalk_dash_gap",
        description="横断歩道の破線の間隔(m)",
        default=0.45,
        min = 0.1,
        max = 10.0
    )
    bpy.types.Scene.crosswalk_generate_offset_start = bpy.props.FloatProperty(
        name="crosswalk_generate_offset_start",
        description="横断歩道の始点側のメッシュ生成オフセット(m)",
        default=0.45,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.crosswalk_generate_offset_end = bpy.props.FloatProperty(
        name="crosswalk_generate_offset_end",
        description="横断歩道の終点側のメッシュ生成オフセット(m)",
        default=0.45,
        min = 0.0,
        max = 100.0
    )
    bpy.types.Scene.stop_line_generate_start = bpy.props.BoolProperty(
        name="stop_line_generate_start",
        description="ベースポリラインの始点に停止線を生成するかどうか",
        default=True
    )
    bpy.types.Scene.stop_line_generate_end = bpy.props.BoolProperty(
        name="stop_line_generate_end",
        description="ベースポリラインの終点に停止線を生成するかどうか",
        default=True
    )
    bpy.types.Scene.stop_line_width = bpy.props.FloatProperty(
        name="stop_line_width",
        description="停止線の幅(m)",
        default=0.3,
        min = 0.01,
        max = 10.0
    )
    bpy.types.Scene.stop_line_position_offset = bpy.props.FloatProperty(
        name="stop_line_position_offset",
        description="停止線の位置オフセット(m)",
        default=5.5,
        min = 0.0,
        max = 10.0
    )
    bpy.types.Scene.stop_line_add_generate_offset = bpy.props.BoolProperty(
        name="stop_line_add_generate_offset",
        description="停止線の始点/終点にライン幅(m)のメッシュ生成オフセット(m)を追加",
        default=False
    )
    bpy.types.Scene.ClearCollection_BaseLineToRoadLine = bpy.props.BoolProperty(
        name="ClearCollection_BaseLineToRoadLine",
        description="生成前にコレクションを初期化するか",
        default=True
    )

# 路面標示ポリラインの自動生成：解除
def GEOTOOL_BaseLineToRoadLine_unregister():
    bpy.utils.unregister_class(GEOTOOL_BaseLineToRoadLine)
    bpy.utils.unregister_class(GEOTOOL_BaseLineToRoadLine_Panel)
    
    del bpy.types.Scene.BaseLineObject
    del bpy.types.Scene.WhiteLineMaterial
    del bpy.types.Scene.sample_distance
    del bpy.types.Scene.height_offset
    del bpy.types.Scene.default_line_width
    del bpy.types.Scene.lane_distance
    del bpy.types.Scene.lane_left
    del bpy.types.Scene.lane_right
    del bpy.types.Scene.center_line_yellow
    del bpy.types.Scene.YellowLineMaterial
    del bpy.types.Scene.center_line_generate_offset_start
    del bpy.types.Scene.center_line_generate_offset_end
    del bpy.types.Scene.center_line_dash
    del bpy.types.Scene.center_line_dash_length
    del bpy.types.Scene.center_line_dash_gap
    del bpy.types.Scene.lane_boundary_line_generate
    del bpy.types.Scene.lane_boundary_line_generate_offset_start
    del bpy.types.Scene.lane_boundary_line_generate_offset_end
    del bpy.types.Scene.lane_boundary_line_dash
    del bpy.types.Scene.lane_boundary_line_dash_length
    del bpy.types.Scene.lane_boundary_line_dash_gap
    del bpy.types.Scene.outside_lane_line_generate_offset_start
    del bpy.types.Scene.outside_lane_line_generate_offset_end
    del bpy.types.Scene.crosswalk_generate_start
    del bpy.types.Scene.crosswalk_generate_end
    del bpy.types.Scene.crosswalk_width
    del bpy.types.Scene.crosswalk_position_offset
    del bpy.types.Scene.crosswalk_dash_length
    del bpy.types.Scene.crosswalk_dash_gap
    del bpy.types.Scene.crosswalk_generate_offset_start
    del bpy.types.Scene.crosswalk_generate_offset_end
    del bpy.types.Scene.stop_line_generate_start
    del bpy.types.Scene.stop_line_generate_end
    del bpy.types.Scene.stop_line_width
    del bpy.types.Scene.stop_line_position_offset
    del bpy.types.Scene.stop_line_add_generate_offset
    del bpy.types.Scene.ClearCollection_BaseLineToRoadLine

"""
路面標示ポリラインを編集
"""
# 路面標示ポリラインを編集
class GEOTOOL_EditRoadLine(bpy.types.Operator):
    bl_idname = "object.edit_road_line"
    bl_label = "EditRoadLine"
    bl_description = "路面標示ポリラインを編集"
    dialog_message = ""
    
    process_type: EnumProperty(
        name="Process Type",
        description="処理内容",
        items=[
            ('PRESET_WHITE_SOLID_LINE', "プリセット：白の実線", ""),
            ('PRESET_WHITE_DASH_LINE', "プリセット：白の破線", ""),
            ('PRESET_YELLOW_SOLID_LINE', "プリセット：黄の実線", ""),
            ('PRESET_YELLOW_DASH_LINE', "プリセット：黄の破線", ""),
            ('PRESET_STOP_LINE', "プリセット：停止線", ""),
            ('PRESET_CROSSWALK', "プリセット：横断歩道", ""),
            ('TWO_POINTS_TO_POLYLINE', "2点からポリライン生成", ""),
            ('ADD_OFFSET_TO_POLYLINE', "左右オフセットを追加したポリライン生成", ""),
            ('CUTTING_TO_POLYLINE', "ポリラインを切断", ""),
        ]
    ) # type: ignore
    
    # 処理関数(固定名)
    def execute(self, context):
        self.report({'INFO'}, f"{self.bl_label}.execute() process_type={self.process_type}")
        
        # 処理内容をprocess_typeで判別
        if self.process_type.startswith('PRESET_'): # 路面標示ポリラインのカスタムプロパティをプリセットで変更
            for road_line_object in self.road_line_objects:
                try:
                    # 対象ポリラインの設定値取得
                    viewport_color = viewport_white_solid_line_color
                    material = road_line_object.get("material", context.scene.WhiteLineMaterial)
                    vertex_distance = road_line_object.get("vertex_distance", context.scene.sample_distance)
                    height_offset = road_line_object.get("height_offset", context.scene.height_offset)
                    line_width = road_line_object.get("line_width", 0.0)
                    is_dash = road_line_object.get("is_dash", False)
                    dash_length = road_line_object.get("dash_length", 0.0)
                    dash_gap = road_line_object.get("dash_gap", 0.0)
                    generate_offset_start = road_line_object.get("generate_offset_start", 0.0)
                    generate_offset_end = road_line_object.get("generate_offset_end", 0.0)
                    
                    # プリセットごとに設定値変更
                    if vertex_distance <= 0.0:
                        vertex_distance = context.scene.sample_distance
                    
                    if self.process_type == 'PRESET_WHITE_SOLID_LINE':
                        # 白色の実線
                        viewport_color = viewport_white_solid_line_color
                        material = context.scene.WhiteLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.default_line_width
                        is_dash = False
                        if dash_length <= 0.0:
                            dash_length = context.scene.lane_boundary_line_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.lane_boundary_line_dash_gap
                    elif self.process_type == 'PRESET_WHITE_DASH_LINE':
                        # 白色の破線
                        viewport_color = viewport_white_dash_line_color
                        material = context.scene.WhiteLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.default_line_width
                        is_dash = True
                        if dash_length <= 0.0:
                            dash_length = context.scene.lane_boundary_line_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.lane_boundary_line_dash_gap
                    elif self.process_type == 'PRESET_YELLOW_SOLID_LINE':
                        # 黄色の実線
                        viewport_color = viewport_yellow_solid_line_color
                        material = context.scene.YellowLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.default_line_width
                        is_dash = False
                        if dash_length <= 0.0:
                            dash_length = context.scene.center_line_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.center_line_dash_gap
                    elif self.process_type == 'PRESET_YELLOW_DASH_LINE':
                        # 黄色の破線
                        viewport_color = viewport_yellow_dash_line_color
                        material = context.scene.YellowLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.default_line_width
                        is_dash = True
                        if dash_length <= 0.0:
                            dash_length = context.scene.center_line_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.center_line_dash_gap
                    elif self.process_type == 'PRESET_STOP_LINE':
                        # 停止線
                        viewport_color = viewport_stop_line_color
                        material = context.scene.WhiteLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.stop_line_width
                        is_dash = False
                        if dash_length <= 0.0:
                            dash_length = context.scene.lane_boundary_line_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.lane_boundary_line_dash_gap
                        if context.scene.stop_line_add_generate_offset:
                            if generate_offset_start <= 0.0:
                                generate_offset_start = context.scene.default_line_width/2.0
                            if generate_offset_end <= 0.0:
                                generate_offset_end = context.scene.default_line_width/2.0
                    elif self.process_type == 'PRESET_CROSSWALK':
                        # 横断歩道
                        viewport_color = viewport_crosswalk_color
                        material = context.scene.WhiteLineMaterial
                        if line_width <= 0.0:
                            line_width = context.scene.crosswalk_width
                        is_dash = True
                        if dash_length <= 0.0:
                            dash_length = context.scene.crosswalk_dash_length
                        if dash_gap <= 0.0:
                            dash_gap = context.scene.crosswalk_dash_gap
                        if generate_offset_start <= 0.0:
                                generate_offset_start = context.scene.crosswalk_generate_offset_start
                        if generate_offset_end <= 0.0:
                            generate_offset_end = context.scene.crosswalk_generate_offset_end
                    
                    # 変更をカスタムプロパティに反映
                    set_road_line_property(
                        road_line_object,
                        viewport_color,
                        material,
                        vertex_distance,
                        height_offset,
                        line_width,
                        is_dash,
                        dash_length,
                        dash_gap,
                        generate_offset_start,
                        generate_offset_end
                    )
                except Exception as e:
                    self.report({'ERROR'}, f"'{road_line_object.name}'のカスタムプロパティを白色の実線に変更する処理に失敗しました。\n{str(e)}")
                    return {'CANCELLED'}
        elif self.process_type == 'TWO_POINTS_TO_POLYLINE': # 2点からポリライン生成
            # 指定されたポリラインと距離から2点座標取得
            point_list = []
            for polyline_object, select_distance in [{context.scene.SelectPolylineObject1, context.scene.select_distance_1}, {context.scene.SelectPolylineObject2, context.scene.select_distance_2}]:
                # ポリラインを線形の頂点座標配列に変換
                line_points = []
                try:
                    line_points = polyline_to_line_points(polyline_object, Vector((0,0,0)))
                except Exception as e:
                    self.report({'ERROR'}, f"'{polyline_object.name}'の頂点配列の取得に失敗しました。\n{str(e)}")
                    return {'CANCELLED'}
                
                # 頂点座標配列から座標を取得
                try:
                    point = line_points_to_point(line_points, select_distance)
                    point_list.append(point)
                except Exception as e:
                    self.report({'ERROR'}, f"'{polyline_object.name}'の頂点配列から距離{select_distance}mの座標の取得に失敗しました。\n{str(e)}")
                    return {'CANCELLED'}
            
            if len(point_list) != 2:
                self.report({'ERROR'}, "指定されたポリラインと距離から2点の座標の取得に失敗しました。")
                return {'CANCELLED'}
            
            # 2点間の頂点配列生成
            between_line_points = []
            try:
                between_line_points = two_points_to_line_points(point_list[0], point_list[1], context.scene.sample_distance)
            except Exception as e:
                self.report({'ERROR'}, f"2点間を繋ぐ直線の頂点配列の生成に失敗しました。\n{str(e)}")
                return {'CANCELLED'}
            
            # 2点間ポリライン生成
            between_line_obj = None
            try:
                between_line_obj = create_polyline_from_line_points(f"{context.scene.SelectPolylineObject1.name} - {context.scene.SelectPolylineObject2.name}", between_line_points)
            except Exception as e:
                self.report({'ERROR'}, f"2点間を繋ぐ直線のポリライン'{context.scene.SelectPolylineObject1.name} - {context.scene.SelectPolylineObject2.name}'の生成に失敗しました。\n{str(e)}")
                return {'CANCELLED'}
            
            # ポリラインのコレクション移動
            try:
                # 親コレクション取得
                parent_collection = context.scene.SelectPolylineObject1.users_collection[0]
                
                # 親コレクション以外のリンク解除
                for coll in list(between_line_obj.users_collection):
                    if coll != parent_collection:
                        coll.objects.unlink(between_line_obj)
                
                # 親コレクションにリンクされていなければ登録
                if not any(obj is between_line_obj for obj in parent_collection.objects):
                    parent_collection.objects.link(between_line_obj)
            except Exception as e:
                self.report({'ERROR'}, f"路面標示ポリラインのコレクション移動に失敗しました。\n詳細: {str(e)}")
                return {'CANCELLED'}
        elif self.process_type == 'ADD_OFFSET_TO_POLYLINE': # 左右オフセットを追加したポリライン生成
            # ポリラインを線形の頂点座標配列に変換
            line_points = []
            try:
                line_points = polyline_to_line_points(context.scene.SelectPolylineObject1, Vector((0,0,0)))
            except Exception as e:
                self.report({'ERROR'}, f"'{context.scene.SelectPolylineObject1.name}'の頂点配列の取得に失敗しました。\n{str(e)}")
                return {'CANCELLED'}
            
            # 頂点座標配列にオフセットを追加
            offset_line_points = []
            try:
                offset_line_points = line_points_to_offset_line_points(line_points, context.scene.select_distance_1)
            except Exception as e:
                self.report({'ERROR'}, f"'{context.scene.SelectPolylineObject1.name}'の頂点配列へオフセットを追加する処理に失敗しました。\n{str(e)}")
                return {'CANCELLED'}
            
            # オフセット追加ポリラインを生成
            offset_line_obj = None
            try:
                offset_line_obj = create_polyline_from_line_points(f"{context.scene.SelectPolylineObject1.name}_Offset{context.scene.select_distance_1}", offset_line_points)
            except Exception as e:
                self.report({'ERROR'}, f"オフセットを追加したポリライン'{context.scene.SelectPolylineObject1.name}_Offset{context.scene.select_distance_1}'の生成に失敗しました。\n{str(e)}")
                return {'CANCELLED'}
            
            # ポリラインのコレクション移動
            try:
                # 親コレクション取得
                parent_collection = context.scene.SelectPolylineObject1.users_collection[0]
                
                # 親コレクション以外のリンク解除
                for coll in list(offset_line_obj.users_collection):
                    if coll != parent_collection:
                        coll.objects.unlink(offset_line_obj)
                
                # 親コレクションにリンクされていなければ登録
                if not any(obj is offset_line_obj for obj in parent_collection.objects):
                    parent_collection.objects.link(offset_line_obj)
            except Exception as e:
                self.report({'ERROR'}, f"路面標示ポリラインのコレクション移動に失敗しました。\n詳細: {str(e)}")
                return {'CANCELLED'}
        return {'FINISHED'}
    
    # GUIから呼ばれる関数(固定名)
    def invoke(self, context, event):
        self.report({'INFO'}, f"{self.bl_label}.invoke() process_type={self.process_type}")
        
        if self.process_type.startswith('PRESET_'): # 路面標示ポリラインのカスタムプロパティをプリセットで変更
            # 処理対象のオブジェクトがない場合は中断
            if len(context.selected_objects) == 0:
                self.report({'ERROR'}, "対象のオブジェクトが選択されていません。\n対象オブジェクトを選択してから実行してください。\n対象オブジェクトが非表示の場合は表示状態にしてください。")
                return {'CANCELLED'}
            
            # 路面標示ポリライン用コレクションのオブジェクトで路面標示ポリラインじゃないオブジェクトはスキップ
            self.road_line_objects = []
            for road_line_object in context.selected_objects:
                # オブジェクトがポリラインかどうか
                try:
                    polyline_to_line_points(road_line_object, Vector((0,0,0)))
                except Exception as e:
                    self.report({'WARNING'}, f"選択中の'{road_line_object.name}'はポリラインではないため処理をスキップします。\n{str(e)}")
                    continue
                
                self.road_line_objects.append(road_line_object)
            
            # 処理対象の路面標示ポリラインのリストが空の場合は中断
            if len(self.road_line_objects) == 0:
                self.report({'ERROR'}, f"選択中のオブジェクトに路面標示ポリラインのオブジェクトがありません。")
                return {'CANCELLED'}
            
            return self.execute(context)
        elif self.process_type == 'TWO_POINTS_TO_POLYLINE': # 2点からポリライン生成
            # 選択ポリライン1が指定されていない場合は中断
            if not context.scene.SelectPolylineObject1:
                self.report({'ERROR'}, "線1のポリラインが指定されていません。")
                return {'CANCELLED'}
            
            # 選択ポリライン2が指定されていない場合は中断
            if not context.scene.SelectPolylineObject2:
                self.report({'ERROR'}, "線2のポリラインが指定されていません。")
                return {'CANCELLED'}
            
            # オブジェクトがポリラインかどうか
            for polyline_object in [context.scene.SelectPolylineObject1, context.scene.SelectPolylineObject2]:
                try:
                    polyline_to_line_points(polyline_object, Vector((0,0,0)))
                except Exception as e:
                    self.report({'ERROR'}, f"ポリラインの2点を繋ぐポリライン生成のポリラインチェックに失敗。\n{str(e)}")
                    return {'CANCELLED'}
            
            return self.execute(context)
        elif self.process_type == 'ADD_OFFSET_TO_POLYLINE': # 左右オフセットを追加したポリライン生成
            # 選択ポリライン1が指定されていない場合は中断
            if not context.scene.SelectPolylineObject1:
                self.report({'ERROR'}, "線のポリラインが指定されていません。")
                return {'CANCELLED'}
            
            # オブジェクトがポリラインかどうか
            try:
                polyline_to_line_points(context.scene.SelectPolylineObject1, Vector((0,0,0)))
            except Exception as e:
                self.report({'ERROR'}, f"{context.scene.SelectPolylineObject1.name}のポリラインチェックに失敗。\n{str(e)}")
                return {'CANCELLED'}
            
            return self.execute(context)
        else:
            self.report({'ERROR'}, "路面標示ポリラインを編集で不明な処理内容です。\n開発者に確認してください。")
            return {'CANCELLED'}

# 路面標示ポリラインを編集：UI
class GEOTOOL_EditRoadLine_Panel(bpy.types.Panel):
    bl_label = "2.路面標示ポリラインを編集"
    bl_idname = "2_EditRoadLine"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TOOL"
    
    def draw(self, context):
        # プリセットかんたん設定
        line_box = self.layout.box()
        line_column = line_box.column(align=True)
        line_column.label(text="プリセットかんたん設定")
        line_row_1 = line_column.row(align=True)
        line_row_1.operator(GEOTOOL_EditRoadLine.bl_idname, text="白の実線").process_type = 'PRESET_WHITE_SOLID_LINE'
        line_row_1.operator(GEOTOOL_EditRoadLine.bl_idname, text="白の破線").process_type = 'PRESET_WHITE_DASH_LINE'
        line_row_2 = line_column.row(align=True)
        line_row_2.operator(GEOTOOL_EditRoadLine.bl_idname, text="黄の実線").process_type = 'PRESET_YELLOW_SOLID_LINE'
        line_row_2.operator(GEOTOOL_EditRoadLine.bl_idname, text="黄の破線").process_type = 'PRESET_YELLOW_DASH_LINE'
        line_row_3 = line_column.row(align=True)
        line_row_3.operator(GEOTOOL_EditRoadLine.bl_idname, text="停止線").process_type = 'PRESET_STOP_LINE'
        line_row_3.operator(GEOTOOL_EditRoadLine.bl_idname, text="横断歩道").process_type = 'PRESET_CROSSWALK'
        
        # ポリラインの2点を繋ぐポリライン生成
        two_points_line_box = self.layout.box()
        two_points_line_box.label(text="ポリラインの2点を繋ぐポリライン生成")
        
        two_points_line_column1 = two_points_line_box.column(align=True)
        two_points_line_column1.prop_search(context.scene, "SelectPolylineObject1", context.scene, "objects", text="線1")
        two_points_line_row1 = two_points_line_column1.row(align=True)
        two_points_line_row1.prop(context.scene, "select_distance_1_start", text="")
        two_points_line_row1.label(text=f"{'始点' if context.scene.select_distance_1_start else '終点'}側から")
        two_points_line_row1.prop(context.scene, "select_distance_1", text="")
        two_points_line_row1.label(text=f"(m)の座標")
        
        two_points_line_column2 = two_points_line_box.column(align=True)
        two_points_line_column2.prop_search(context.scene, "SelectPolylineObject2", context.scene, "objects", text="線2")
        two_points_line_row2 = two_points_line_column2.row(align=True)
        two_points_line_row2.prop(context.scene, "select_distance_2_start", text="")
        two_points_line_row2.label(text=f"{'始点' if context.scene.select_distance_2_start else '終点'}側から")
        two_points_line_row2.prop(context.scene, "select_distance_2", text="")
        two_points_line_row2.label(text=f"(m)の座標")
        
        two_points_line_box.operator(GEOTOOL_EditRoadLine.bl_idname, text="新規ポリライン生成").process_type = 'TWO_POINTS_TO_POLYLINE'
        
        # 左右オフセットを追加したポリライン生成
        offset_line_box = self.layout.box()
        offset_line_box.label(text="左右オフセットを追加したポリライン生成")
        offset_line_column1 = offset_line_box.column(align=True)
        offset_line_column1.prop_search(context.scene, "SelectPolylineObject1", context.scene, "objects", text="線")
        offset_line_column1.prop(context.scene, "select_distance_1", text="オフセット距離(m)")
        offset_line_box.operator(GEOTOOL_EditRoadLine.bl_idname, text="新規ポリライン生成").process_type = 'ADD_OFFSET_TO_POLYLINE'
        
        # ポリラインを切断
        cutting_line_box = self.layout.box()
        cutting_line_box.label(text="ポリラインを切断（未実装）")
        cutting_line_column1 = cutting_line_box.column(align=True)
        cutting_line_column1.prop_search(context.scene, "SelectPolylineObject1", context.scene, "objects", text="線")
        cutting_line_row1 = cutting_line_column1.row(align=True)
        cutting_line_row1.prop(context.scene, "select_distance_1_start", text="")
        cutting_line_row1.label(text=f"{'始点' if context.scene.select_distance_1_start else '終点'}側から")
        cutting_line_row1.prop(context.scene, "select_distance_1", text="")
        cutting_line_row1.label(text=f"(m)の座標")
        cutting_line_box.operator(GEOTOOL_EditRoadLine.bl_idname, text="新規ポリライン生成").process_type = 'CUTTING_TO_POLYLINE'
        
        self.layout.operator(GEOTOOL_EditRoadLine.bl_idname, text="ゼブラ生成機能（未実装）")

# 路面標示ポリラインを編集：登録
def GEOTOOL_EditRoadLineProperty_register():
    bpy.utils.register_class(GEOTOOL_EditRoadLine)
    bpy.utils.register_class(GEOTOOL_EditRoadLine_Panel)
    
    bpy.types.Scene.SelectPolylineObject1 = bpy.props.PointerProperty(
        name="SelectPolylineObject1",
        type=bpy.types.Object,
        description="選択ポリライン1"
    )
    bpy.types.Scene.SelectPolylineObject2 = bpy.props.PointerProperty(
        name="SelectPolylineObject2",
        type=bpy.types.Object,
        description="選択ポリライン2"
    )
    bpy.types.Scene.select_distance_1 = bpy.props.FloatProperty(
        name="select_distance_1",
        description="選択距離1(m)",
        default=0.0,
        min = 0.0,
        max = 1000.0
    )
    bpy.types.Scene.select_distance_2 = bpy.props.FloatProperty(
        name="select_distance_2",
        description="選択距離2(m)",
        default=0.0,
        min = 0.0,
        max = 1000.0
    )
    bpy.types.Scene.select_distance_1_start = bpy.props.BoolProperty(
        name="select_distance_1_start",
        description="選択距離1(m)が始点側からの距離か",
        default=True
    )
    bpy.types.Scene.select_distance_2_start = bpy.props.BoolProperty(
        name="select_distance_2_start",
        description="選択距離2(m)が始点側からの距離か",
        default=True
    )

# 路面標示ポリラインを編集：解除
def GEOTOOL_EditRoadLineProperty_unregister():
    bpy.utils.unregister_class(GEOTOOL_EditRoadLine)
    bpy.utils.unregister_class(GEOTOOL_EditRoadLine_Panel)
    
    del bpy.types.Scene.SelectPolylineObject1
    del bpy.types.Scene.SelectPolylineObject2
    del bpy.types.Scene.select_distance_1
    del bpy.types.Scene.select_distance_2
    del bpy.types.Scene.select_distance_1_start
    del bpy.types.Scene.select_distance_2_start

"""
路面標示ポリラインをメッシュ化
"""
# 路面標示ポリラインをメッシュ化：処理
class GEOTOOL_RoadLinesToMesh(bpy.types.Operator):
    bl_idname = "object.road_lines_to_mesh"
    bl_label = "RoadLinesToMesh"
    bl_description = "路面標示ポリラインからメッシュを生成"
    dialog_message = ""
    
    process_type: EnumProperty(
        name="Process Type",
        description="処理内容",
        items=[
            ('GenerateRoadLinesToMesh', "路面標示ポリラインからメッシュ生成", ""),
            ('ClearCollection', "生成メッシュのコレクション初期化", ""),
        ]
    ) # type: ignore

    # 処理関数(固定名)
    def execute(self, context):
        self.report({'INFO'}, f"{self.bl_label}.execute() process_type={self.process_type}")
        start_time = time.time()
        
        # ビュー視点をトップに変更
        try:
            # 3Dビューポートを表示しているエリアを取得
            areas  = [area for area in bpy.context.window.screen.areas if area.type == 'VIEW_3D']
            # 最初の3Dビューポートの視点をトップに変更
            with bpy.context.temp_override(
                window=bpy.context.window,
                area=areas[0],
                region=[region for region in areas[0].regions if region.type == 'WINDOW'][0],
                screen=bpy.context.window.screen
            ): 
                bpy.ops.view3d.view_axis(type='TOP')
                bpy.context.region_data.update()
        except Exception as e:
            self.report({'ERROR'}, f"ビュー視点をトップに変更できませんでした。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        # オブジェクトモードに移行する
        try:
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        except Exception as e:
            self.report({'ERROR'}, f"オブジェクトモードへの切り替えに失敗しました。\n詳細: {str(e)}")
            return {'CANCELLED'}
        
        if self.process_type == 'GenerateRoadLinesToMesh':
            # 路面標示ポリラインからメッシュ生成
            # 路面標示ポリラインの正規化・ロック処理
            for road_line_object in self.road_line_objects:
                # 路面標示ポリラインの位置・回転・スケールを適用（正規化）
                if not is_transform_normalized(road_line_object):
                    bpy.ops.object.select_all(action='DESELECT')
                    road_line_object.select_set(True)
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                
                # 路面標示ポリラインの位置・回転・スケールをロック
                if not is_transform_locked(road_line_object):
                    road_line_object.lock_location[0] = True  # X位置をロック
                    road_line_object.lock_location[1] = True  # Y位置をロック
                    road_line_object.lock_location[2] = True  # Z位置をロック
                    road_line_object.lock_rotation[0] = True  # X回転をロック
                    road_line_object.lock_rotation[1] = True  # Y回転をロック
                    road_line_object.lock_rotation[2] = True  # Z回転をロック
                    road_line_object.lock_scale[0] = True     # Xスケールをロック
                    road_line_object.lock_scale[1] = True     # Yスケールをロック
                    road_line_object.lock_scale[2] = True     # Zスケールをロック
            
            # 路面標示メッシュ用コレクションを取得
            road_lines_to_mesh_collection = None
            try:
                # 路面標示ポリライン用コレクションの親コレクションを取得
                parent_collection = None
                for collection in bpy.data.collections:
                    if context.scene.RoadLineCollection.name in collection.children.keys():
                        parent_collection = collection
                        break
                
                # 指定した親コレクションから路面標示メッシュ用コレクションを取得・新規
                road_lines_to_mesh_collection = get_or_create_collection(f"{context.scene.RoadLineCollection.name}ToMesh", parent_collection)
                if not road_lines_to_mesh_collection:
                    raise RuntimeError("not road_lines_to_mesh_collection.")
                
                # 必要ならコレクションの初期化
                if context.scene.ClearCollection_RoadLinesToMesh:
                    clear_collection(road_lines_to_mesh_collection)
            except Exception as e:
                self.report({'ERROR'}, f"路面標示ポリライン用コレクションの取得に失敗。\n詳細: {str(e)}")
                return {'CANCELLED'}
             
            # 路面標示ポリラインからメッシュの生成
            road_line_mesh_list = []
            for road_line_object in self.road_line_objects:
                try:
                    # メッシュオブジェクト生成
                    road_obj = create_road_mesh_from_polyline(road_line_object)
                    road_line_mesh_list.append(road_obj)
                    self.report({'INFO'}, f"'{road_line_object.name}'からメッシュ'{road_obj.name}'を生成しました。")
                except Exception as e:
                    self.report({'ERROR'}, f"'{road_line_object.name}'からのメッシュの生成に失敗しました。\n詳細: {str(e)}")
                    return {'CANCELLED'}
            
            # 路面標示メッシュのコレクション移動
            try:
                for road_line_mesh in road_line_mesh_list:
                    # 路面標示メッシュ用コレクション以外のリンク解除
                    for coll in list(road_line_mesh.users_collection):
                        if coll != road_lines_to_mesh_collection:
                            coll.objects.unlink(road_line_mesh)
                    
                    # 路面標示ポリライン用コレクションにリンクされていなければ登録
                    if not any(obj is road_line_mesh for obj in road_lines_to_mesh_collection.objects):
                        road_lines_to_mesh_collection.objects.link(road_line_mesh)
            except Exception as e:
                self.report({'ERROR'}, f"路面標示メッシュのコレクション移動に失敗しました。\n詳細: {str(e)}")
                return {'CANCELLED'}
        elif self.process_type == 'ClearCollection':
            # 路面標示ポリラインから生成したメッシュ削除
            # 路面標示メッシュ用コレクションを取得
            road_lines_to_mesh_collection = None
            try:
                # 路面標示ポリライン用コレクションの親コレクションを取得
                parent_collection = None
                for collection in bpy.data.collections:
                    if context.scene.RoadLineCollection.name in collection.children.keys():
                        parent_collection = collection
                        break
                
                # 指定した親コレクションから路面標示メッシュ用コレクションを取得・新規
                road_lines_to_mesh_collection = get_or_create_collection(f"{context.scene.RoadLineCollection.name}ToMesh", parent_collection)
                if not road_lines_to_mesh_collection:
                    raise RuntimeError("not road_lines_to_mesh_collection.")
            except Exception as e:
                self.report({'ERROR'}, f"路面標示ポリライン用コレクションの取得に失敗。\n詳細: {str(e)}")
                return {'CANCELLED'}
            
            # コレクションの初期化
            try:
                clear_collection(road_lines_to_mesh_collection)
            except Exception as e:
                self.report({'ERROR'}, f"路面標示ポリライン用コレクションの初期化に失敗。\n詳細: {str(e)}")
                return {'CANCELLED'}
        
        self.report({'INFO'}, f"処理時間：{(time.time() - start_time):.3f}秒")
        return {'FINISHED'}
    
    # GUIから呼ばれる関数(固定名)
    def invoke(self, context, event):
        self.report({'INFO'}, f"{self.bl_label}.invoke() process_type={self.process_type}")
        
        # 路面標示ポリライン用コレクションがない場合は中断
        if not context.scene.RoadLineCollection:
            self.report({'ERROR'}, f"路面標示ポリライン用コレクションが指定されていません。\n「路面標示ポリライン生成」で路面標示ポリラインが生成されたコレクションを指定する必要があります。")
            return {'CANCELLED'}
        
        if self.process_type == 'GenerateRoadLinesToMesh':
            # 路面標示ポリラインからメッシュ生成
            # 路面標示ポリライン用コレクションにオブジェクトがない場合は中断
            if len(context.scene.RoadLineCollection.objects) == 0:
                self.report({'ERROR'}, f"'{context.scene.RoadLineCollection.name}'にオブジェクトがありません。\n先に中央線に沿ったベースポリラインを作成して「路面標示ポリライン生成」を実行してください。")
                return {'CANCELLED'}
        
            # 路面標示ポリライン用コレクションのオブジェクトで路面標示ポリラインじゃないオブジェクトはスキップ
            self.road_line_objects = []
            for road_line_object in context.scene.RoadLineCollection.objects:
                # オブジェクトがポリラインかどうか
                base_line_points = []
                base_line_length = 0.0
                try:
                    base_line_points = polyline_to_line_points(road_line_object, Vector((0,0,0)))
                    base_line_length = total_line_points_length(base_line_points)
                except Exception as e:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'はポリラインではないため処理をスキップします。\n{str(e)}")
                    continue
            
                # マテリアル
                if not "material" in road_line_object:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'material'にマテリアルが設定されていません。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                    continue
                elif road_line_object.get("material") == None:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'material'がNoneになっています。マテリアルを設定してください。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                    continue
            
                # ライン幅(m)
                if not "line_width" in road_line_object:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'line_width'にライン幅(m)が設定されていません。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                    continue
                elif road_line_object.get("line_width") <= 0:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'line_width'のライン幅(m)に0以下の値が設定されています。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                    continue
            
                # 頂点間距離(m)
                if not "vertex_distance" in road_line_object:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'vertex_distance'にライン幅(m)が設定されていません。\n頂点間距離(m)は生成するメッシュの頂点同士の距離です。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                    continue
                elif road_line_object.get("vertex_distance") <= 0:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'vertex_distance'の頂点間距離(m)に0以下の値が設定されています。\n頂点間距離(m)は生成するメッシュの頂点同士の距離です。")
                    continue
            
                # 破線が設定されTrueになっている時
                if "is_dash" in road_line_object and road_line_object.get("is_dash"):
                    if not "dash_length" in road_line_object:
                        self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'is_dash'=Trueで破線の指定があるのに'dash_length'で破線の長さ(m)が設定されていません。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                        continue
                    elif road_line_object.get("dash_length") <= 0:
                        self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'is_dash'=Trueで破線の指定があるのに'dash_length'の破線の長さ(m)に0以下の値が設定されています。")
                        continue
                
                    if not "dash_gap" in road_line_object:
                        self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'is_dash'=Trueで破線の指定があるのに'dash_gap'で破線の間隔(m)が設定されていません。\n路面標示ポリライン生成でパスを作り直すか手動で設定してください。")
                        continue
                    elif road_line_object.get("dash_gap") <= 0:
                        self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'is_dash'=Trueで破線の指定があるのに'dash_gap'の破線の間隔(m)に0以下の値が設定されています。")
                        continue
            
                 # 生成オフセット
                generate_offset_start = road_line_object.get("generate_offset_start", 0.0)
                generate_offset_end   = road_line_object.get("generate_offset_end", 0.0)
                start_dist = generate_offset_start
                end_dist   = base_line_length - generate_offset_end
                if end_dist <= start_dist:
                    self.report({'WARNING'}, f"'{context.scene.RoadLineCollection.name}' > '{road_line_object.name}'のカスタムプロパティ'generate_offset_start/end'によるメッシュ生成オフセットで生成範囲が無くなっています。")
                    continue
            
                # 路面標示ポリラインとして処理対象に追加
                self.road_line_objects.append(road_line_object)
        
            # 処理対象の路面標示ポリラインのリストが空の場合は中断
            if len(self.road_line_objects) == 0:
                self.report({'ERROR'}, f"'{context.scene.RoadLineCollection.name}'にメッシュを生成できるポリラインのオブジェクトがありません。")
                return {'CANCELLED'}
        
            # パスが正規化・ロックされているか
            is_normalized = True
            is_locked = True
            for road_line_object in self.road_line_objects:
                if is_normalized:
                    is_normalized = is_transform_normalized(road_line_object)
                if is_locked:
                    is_locked = is_transform_locked(road_line_object)
            if is_normalized and is_locked:
                return self.execute(context)
            else:
                # 確認ダイアログを表示
                if not is_normalized and not is_locked:
                    self.dialog_message = "正規化・ロックされていないパスがあります。\n自動で正規化・ロックして処理を継続しますか？"
                elif not is_normalized:
                    self.dialog_message = "正規化されていないパスがあります。\n自動で正規化して処理を継続しますか？"
                else:
                    self.dialog_message = "ロックされていないパスがあります。\n自動でロックして処理を継続しますか？"
                return context.window_manager.invoke_props_dialog(self)
        elif self.process_type == 'ClearCollection':
            # 路面標示ポリラインから生成したメッシュ削除
            self.dialog_message = f"'{context.scene.RoadLineCollection.name}'の路面標示ポリラインから\n生成したメッシュを削除しますか？"
            return context.window_manager.invoke_props_dialog(self)
        else:
            self.report({'ERROR'}, "路面標示ポリラインをメッシュ化で不明な処理内容です。\n開発者に確認してください。")
            return {'CANCELLED'}
    
    def draw(self, context):
        for message in self.dialog_message.splitlines(): # 改行で分割
            self.layout.label(text=message)

# 路面標示ポリラインをメッシュ化：UI
class GEOTOOL_RoadLinesToMesh_Panel(bpy.types.Panel):
    bl_label = "3.路面標示ポリラインのメッシュ化"
    bl_idname = "3_RoadLinesToMesh"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TOOL"
    
    def draw(self, context):
        collection_column = self.layout.column(align=True)
        collection_column.label(text="路面標示ポリラインのコレクション")
        collection_column.prop(context.scene, "RoadLineCollection", text="")

        create_column = self.layout.column(align=True)
        create_column.prop(context.scene, "ClearCollection_RoadLinesToMesh", text="生成先のコレクションを初期化")
        create_column.operator(GEOTOOL_RoadLinesToMesh.bl_idname, text="メッシュ生成", icon="PLAY").process_type = 'GenerateRoadLinesToMesh'
        create_column.operator(GEOTOOL_RoadLinesToMesh.bl_idname, text="メッシュ削除", icon="PLAY").process_type = 'ClearCollection'

# 路面標示ポリラインをメッシュ化：登録
def GEOTOOL_RoadLinesToMesh_register():
    bpy.utils.register_class(GEOTOOL_RoadLinesToMesh)
    bpy.utils.register_class(GEOTOOL_RoadLinesToMesh_Panel)
    
    bpy.types.Scene.RoadLineCollection = bpy.props.PointerProperty(
        name="RoadLineCollection",
        type=bpy.types.Collection,
        description="路面標示ポリライン用コレクション"
    )
    bpy.types.Scene.ClearCollection_RoadLinesToMesh = bpy.props.BoolProperty(
        name="ClearCollection_RoadLinesToMesh",
        description="生成前にコレクションを初期化するか",
        default=True
    )

# 路面標示ポリラインをメッシュ化：解除
def GEOTOOL_RoadLinesToMesh_unregister():
    bpy.utils.unregister_class(GEOTOOL_RoadLinesToMesh)
    bpy.utils.unregister_class(GEOTOOL_RoadLinesToMesh_Panel)
    
    del bpy.types.Scene.RoadLineCollection
    del bpy.types.Scene.ClearCollection_RoadLinesToMesh

"""
Blenderアドオンとして各機能を登録 
"""
def register():
    GEOTOOL_BaseLineToRoadLine_register()
    GEOTOOL_EditRoadLineProperty_register()
    GEOTOOL_RoadLinesToMesh_register()

def unregister():
    GEOTOOL_BaseLineToRoadLine_unregister()
    GEOTOOL_EditRoadLineProperty_unregister()
    GEOTOOL_RoadLinesToMesh_unregister()

if __name__ == "__main__":
    register()