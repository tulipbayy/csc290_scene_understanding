import json
import math
import sys
from collections import defaultdict

# ---------------------------
# LOAD SCENE
# ---------------------------
def load_scene(filename):
    """Load the JSON scene file with vertex-data and background."""
    with open(filename, 'r') as f:
        data = json.load(f)

    vertex_data = data.get("vertex-data", [])
    background = data.get("background")

    vertices = {}
    for v in vertex_data:
        vertices[v["id"]] = {
            "coords": tuple(v["coords"]),
            "kind_list": v["kind-list"]
        }

    return vertices, background


# ---------------------------
# CONNECTIONS
# ---------------------------
def get_connected_vertices(vertices):
    """Extract neighbor vertices (letters) from kind-list."""
    connected = {}
    for vid, v in vertices.items():
        connected[vid] = [x for x in v["kind_list"] if isinstance(x, str)]
    return connected


# ---------------------------
# ANGLE CALCULATION
# ---------------------------
def compute_angle(v1, v2, v3, vertices):
    """Return the smaller interior angle (0–180°) at v1 between v2 and v3."""
    (x1, y1), (x2, y2), (x3, y3) = (
        vertices[v1]["coords"],
        vertices[v2]["coords"],
        vertices[v3]["coords"],
    )

    v12 = (x2 - x1, y2 - y1)
    v13 = (x3 - x1, y3 - y1)

    dot = v12[0]*v13[0] + v12[1]*v13[1]
    mag1 = math.hypot(*v12)
    mag2 = math.hypot(*v13)
    if mag1 == 0 or mag2 == 0:
        return 0.0

    cos_theta = dot / (mag1 * mag2)
    cos_theta = max(-1, min(1, cos_theta))  # avoid rounding errors
    return math.degrees(math.acos(cos_theta))


def get_edge_angles(vertices, connected):
    """Compute all pairwise angles at each vertex."""
    all_angles = {}
    for v1, neighbors in connected.items():
        angles = []
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                ang = compute_angle(v1, neighbors[i], neighbors[j], vertices)
                angles.append(round(ang, 2))
        all_angles[v1] = angles
    return all_angles


# ---------------------------
# CLASSIFY VERTICES
# ---------------------------
def classify_vertex(v_id, angles):
    """Determine vertex type based on angle geometry."""
    a = angles[v_id]
    if len(a) <= 1:
        return "L"
    elif len(a) == 2:
        if any(abs(x - 180) < 15 for x in a):
            return "T"
        else:
            return "L"
    elif len(a) >= 3:
        if any(x > 150 for x in a):
            return "ARROW"
        elif all(x < 150 for x in a):
            return "FORK"
        else:
            return "MULTI"
    return "MULTI"


# ---------------------------
# REGION LINKING
# ---------------------------
def add_link(links, r1, r2):
    if r1 != r2:
        links.add(tuple(sorted((r1, r2))))


def generate_links(vertices, classifications):
    """Create region-to-region links based on vertex type."""
    links = set()
    for v_id, v in vertices.items():
        regions = [x for x in v["kind_list"] if isinstance(x, int)]
        vtype = classifications[v_id]

        if len(regions) < 2:
            continue

        if vtype == "FORK":
            for i in range(len(regions)):
                for j in range(i + 1, len(regions)):
                    add_link(links, regions[i], regions[j])
                    print(f"[FORK] {v_id}: linked {regions[i]} - {regions[j]}")
        elif vtype == "ARROW":
            add_link(links, regions[0], regions[1])
            print(f"[ARROW] {v_id}: linked {regions[0]} - {regions[1]}")
    return links


# ---------------------------
# MERGING FUNCTIONS
# ---------------------------
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


def run_GLOBAL(links, background):
    """Strong merging step."""
    link_counts = defaultdict(int)
    for a, b in links:
        if background not in (a, b):
            link_counts[tuple(sorted((a, b)))] += 1

    nuclei = initialize_nuclei(links, background)
    changed = True
    while changed:
        changed = False
        for (a, b), n in link_counts.items():
            if n >= 1 and merge_nuclei(nuclei, a, b):
                print(f"[GLOBAL] merged {a}, {b}")
                changed = True
    return nuclei


def run_SINGLEBODY(links, nuclei, background):
    """Weaker merging step."""
    link_map = defaultdict(set)
    for a, b in links:
        if background not in (a, b):
            link_map[a].add(b)
            link_map[b].add(a)

    changed = True
    while changed:
        changed = False
        for n in list(nuclei):
            if len(n) == 1:
                region = next(iter(n))
                if len(link_map[region]) == 1:
                    other = next(iter(link_map[region]))
                    if merge_nuclei(nuclei, region, other):
                        print(f"[SINGLEBODY] merged {region} with {other}")
                        changed = True
                        break
    return nuclei


# ---------------------------
# BODY EXTRACTION
# ---------------------------
def extract_bodies(nuclei):
    bodies = []
    for n in nuclei:
        bodies.append(sorted(list(n)))
    return bodies


def print_bodies(bodies):
    print("\n===== FINAL BODIES =====")
    if not bodies:
        print("(no bodies detected)")
    for i, body in enumerate(bodies, 1):
        print(f"(BODY {i}: {body})")


# ---------------------------
# MAIN
# ---------------------------
def main():
    # Allow command-line argument: python3 scene_understanding.py one.json
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "cube.json"

    print(f"\n>>> Loading scene: {filename}")
    vertices, background = load_scene(filename)

    connected = get_connected_vertices(vertices)
    angles = get_edge_angles(vertices, connected)
    classifications = {v: classify_vertex(v, angles) for v in vertices}

    print("\nVertex classifications:")
    for v, t in classifications.items():
        print(f"  {v}: {t}")

    links = generate_links(vertices, classifications)
    print("\nGenerated links:", links)

    nuclei_global = run_GLOBAL(links, background)
    nuclei_final = run_SINGLEBODY(links, nuclei_global, background)
    bodies = extract_bodies(nuclei_final)
    print_bodies(bodies)


if __name__ == "__main__":
    main()
