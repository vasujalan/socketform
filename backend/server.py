import io
import os
import tempfile
import uuid

import numpy as np
import open3d as o3d
import trimesh
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(title="SocketForm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}
SUPPORTED_FORMATS = {"stl", "obj", "ply", "glb", "gltf"}


@app.get("/api/health")
def health():
    return {"status": "ok", "open3d_version": o3d.__version__}


@app.post("/api/upload")
async def upload_scan(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported format: {ext}")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        mesh_tm = trimesh.load(tmp_path, force="mesh")

        o3d_mesh = o3d.geometry.TriangleMesh()
        o3d_mesh.vertices = o3d.utility.Vector3dVector(np.array(mesh_tm.vertices, dtype=np.float64))
        o3d_mesh.triangles = o3d.utility.Vector3iVector(np.array(mesh_tm.faces, dtype=np.int32))
        o3d_mesh.compute_vertex_normals()

        triangle_count = len(mesh_tm.faces)
        warnings = []

        if triangle_count > 200000:
            o3d_mesh = o3d_mesh.simplify_quadric_decimation(80000)
            warnings.append(f"Decimated from {triangle_count // 1000}k to ~80k triangles")
            triangle_count = len(np.asarray(o3d_mesh.triangles))

        is_watertight = o3d_mesh.is_watertight()
        if not is_watertight:
            o3d_mesh.remove_duplicated_vertices()
            o3d_mesh.remove_duplicated_triangles()
            o3d_mesh.remove_degenerate_triangles()
            warnings.append("Mesh had open edges — basic repair applied")

        aabb = o3d_mesh.get_axis_aligned_bounding_box()
        extent = aabb.get_extent()
        h = float(extent[1])

        if h > 500:
            scale_guess = "mm"
        elif h < 0.5:
            scale_guess = "m"
        else:
            scale_guess = "cm"

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "mesh": o3d_mesh,
            "filename": file.filename,
            "scale_unit": scale_guess,
        }

        return {
            "session_id": session_id,
            "format": ext.upper(),
            "file_size_mb": round(file_size_mb, 2),
            "triangle_count": int(triangle_count),
            "is_watertight": is_watertight,
            "bounding_box": {
                "x": round(float(extent[0]), 3),
                "y": round(float(extent[1]), 3),
                "z": round(float(extent[2]), 3),
            },
            "scale_unit_guess": scale_guess,
            "warnings": warnings,
        }
    finally:
        os.unlink(tmp_path)


@app.get("/api/export/{session_id}")
def export_socket(
    session_id: str,
    format: str = "stl",
    liner: float = 3.0,
    wall: float = 12.0,
    trim: float = 75.0,
    flare: float = 8.0,
):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    source_mesh = sessions[session_id]["mesh"]
    socket = o3d.geometry.TriangleMesh(source_mesh)

    aabb = socket.get_axis_aligned_bounding_box()
    center = aabb.get_center()
    extent = aabb.get_extent()
    socket.translate(-center)

    avg_radius = float(np.mean([extent[0], extent[2]])) / 2.0
    liner_cm = liner / 10.0
    wall_cm = wall / 10.0
    scale_factor = 1.0 + (liner_cm + wall_cm) / max(avg_radius, 1e-6)

    vertices = np.asarray(socket.vertices).copy()
    ys = vertices[:, 1]
    y_min, y_max = float(ys.min()), float(ys.max())
    y_range = max(y_max - y_min, 1e-6)
    y_norm = (ys - y_min) / y_range

    flare_extra = np.tan(np.radians(flare)) * y_norm * 0.3
    radial_scale = scale_factor + flare_extra
    vertices[:, 0] *= radial_scale
    vertices[:, 2] *= radial_scale

    trim_y = y_min + y_range * (trim / 100.0)
    triangles = np.asarray(socket.triangles)
    below = vertices[:, 1] <= trim_y
    keep = below[triangles[:, 0]] & below[triangles[:, 1]] & below[triangles[:, 2]]

    socket.vertices = o3d.utility.Vector3dVector(vertices)
    socket.triangles = o3d.utility.Vector3iVector(triangles[keep])
    socket.remove_unreferenced_vertices()
    socket.translate(center)
    socket.compute_vertex_normals()

    fmt = format.lower()
    if fmt not in {"stl", "obj", "ply"}:
        raise HTTPException(400, f"Unsupported export format: {format}")

    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        o3d.io.write_triangle_mesh(tmp_path, socket)
        with open(tmp_path, "rb") as f:
            data_bytes = f.read()
    finally:
        os.unlink(tmp_path)

    media_types = {
        "stl": "model/stl",
        "obj": "text/plain",
        "ply": "application/octet-stream",
    }
    return StreamingResponse(
        io.BytesIO(data_bytes),
        media_type=media_types[fmt],
        headers={"Content-Disposition": f'attachment; filename="socket.{fmt}"'},
    )
