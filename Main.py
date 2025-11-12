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

def classify_vertex(v_id, angles):
    if len(angles[v_id]) == 1 or len(angles[v_id]) == 2:
        return "L"
    elif len(angles[v_id]) == 3:
        if any(abs(a - 180) < 5 for a in angles[v_id]):
            return "T"
        elif any(a > 180 for a in angles[v_id]):
            return "ARROW"
        else:
            return "FORK"
    return "MULTI"

def generate_links(vertices, classifications):
    links = set()
    for v_id, v in vertices.items():
        kind_list = v["kind_list"]
        regions = [x for x in kind_list if isinstance(x, int)]
        vtype = classifications[v_id]

        if vtype == "FORK":
            for i in range(len(regions)):
                for j in range(i + 1, len(regions)):
                    add_link(links, regions[i], regions[j])
        elif vtype == "ARROW" and len(regions) >= 2:
            add_link(links, regions[0], regions[1])
    return links

def add_link(links, r1, r2):
    if r1 != r2:
        links.add(tuple(sorted((r1, r2))))

def initialize_nuclei(links, background):
    regions = set(sum(links, ()))
    return [{r} for r in regions if r != background]

def merge_nuclei(nuclei, a, b):
    for n1 in nuclei:
        if a in n1:
            for n2 in nuclei:
                if b in n2 and n1 != n2:
                    n1.update(n2)
                    nuclei.remove(n2)
                    return True
    return False
