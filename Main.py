import json
import math
def load_scene(filename):
    # Open and read the JSON file
    with open(filename, 'r') as f:
        data = json.load(f)    

# Extract useful parts from the data
    vertices = data.get("vertices", {})
    regions = data.get("regions", [])
    kind_lists = data.get("kind_lists", {})
    
    # Return the information for later use
    return vertices, regions, kind_lists

def get_connected_vertices(vertices):
    connected = {}
    for vid, v in vertices.items():
        connected[vid] = [x for x in v["kind_list"] if isinstance(x, str)]
    return connected

def compute_angle(v1, v2, v3, vertices):
    (x1, y1), (x2, y2), (x3, y3) = vertices[v1]["coords"], vertices[v2]["coords"], vertices[v3]["coords"]
    ang1 = math.atan2(y2 - y1, x2 - x1)
    ang2 = math.atan2(y3 - y1, x3 - x1)
    angle = math.degrees((ang2 - ang1) % (2 * math.pi))
    return angle

def get_edge_angles(vertices, connected):
    all_angles = {}
    for v1, neighbors in connected.items():
        angles = []
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                angles.append(compute_angle(v1, neighbors[i], neighbors[j], vertices))
        all_angles[v1] = angles
    return all_angles

