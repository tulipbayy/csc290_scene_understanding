import json
import math
import sys
from collections import defaultdict


# ---------------------------
# Load scene
# ---------------------------
def load_scene(filename):
    """
    Load the scene JSON file.
    """
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
# Geometry helpers (sector angles from KIND lists)
# ---------------------------
def estimate_for_T(angle):
    """
    Return True if a sector angle is approximately a straight continuation (T).
    """
    return 175 <= angle <= 185


def angle_between(p1, p2, p3):
    """
    Compute the counterclockwise angle at p2 between vectors p2->p1 and p2->p3.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    deg1 = (360 + math.degrees(math.atan2(x1 - x2, y1 - y2))) % 360
    deg2 = (360 + math.degrees(math.atan2(x3 - x2, y3 - y2))) % 360
    return deg2 - deg1 if deg1 <= deg2 else 360 - (deg1 - deg2)


def get_sector_angles(vertices):
    """
    For each vertex, compute sector angles from its KIND list.

    The KIND list alternates vertex and region entries and is circular, e.g.:
        [v0, r1, v1, r2, v2, r3, v0]
    - Each region entry sits in a "sector" bounded by the previous and next vertices.
    - For three-neighbor vertices (common in these scenes), there are exactly three
      sectors (and thus three sector angles).
    - For 'L' vertices (two-neighbor), there are no sectors to analyze; we return [].
    """
    angles_map = {}

    for v_id, v in vertices.items():
        origin = vertices[v_id]["coords"]
        kl = v["kind_list"]

        # Collect adjacent vertex coordinates in KIND-list order.
        # We ignore region entries and the final repeated start vertex.
        adj_coors = [origin]
        for i in range(0, len(kl) - 1, 2):
            adj_vertex = kl[i]
            adj_coors.append(vertices[adj_vertex]["coords"])

        # L case: only two neighbors -> no sector analysis
        if len(adj_coors) == 3:
            angles_map[v_id] = []
            continue

        # Three neighbors (length 4 list including origin) -> three sectors.
        # The order matches the working reference so the Arrow mapping is correct.
        angle_1 = angle_between(adj_coors[1], adj_coors[0], adj_coors[2])
        angle_2 = angle_between(adj_coors[2], adj_coors[0], adj_coors[3])
        angle_3 = angle_between(adj_coors[3], adj_coors[0], adj_coors[1])

        # Robustness: ensure they sum to ~360. If not, try alternate wrap order.
        if round(angle_1 + angle_2 + angle_3) != 360:
            angle_1 = angle_between(adj_coors[2], adj_coors[0], adj_coors[1])
            angle_2 = angle_between(adj_coors[3], adj_coors[0], adj_coors[2])
            angle_3 = angle_between(adj_coors[1], adj_coors[0], adj_coors[3])

        assert round(angle_1 + angle_2 + angle_3) == 360, f"Angles do not sum to 360 at vertex {v_id}"

        angles_map[v_id] = [angle_1, angle_2, angle_3]

    return angles_map


# ---------------------------
# Classification
# ---------------------------
def classify_vertex(v_id, angles_map):
    """
    Classify a vertex using its sector angles.

    Rules:
    - L: len(angles) == 0 (only two neighbors)
    - T: any sector approximately 180 degrees
    - FORK: all three sectors < 180
    - ARROW: any sector > 180
    - MULTI: fallback (not expected for these inputs)
    """
    a = angles_map.get(v_id, [])
    if len(a) == 0:
        return "L"
    if any(estimate_for_T(x) for x in a):
        return "T"
    if all(x < 180 for x in a):
        return "FORK"
    if any(x > 180 for x in a):
        return "ARROW"
    return "MULTI"


# ---------------------------
# Link generation
# ---------------------------
def add_link(links, r1, r2):
    """
    Append a region-to-region link, ignoring self-links.
    """
    if r1 != r2:
        links.append((r1, r2))


def generate_links(vertices, classifications, angles_map):
    """
    Create strong links between regions based on vertex classification and sector angles.
    """
    links = []

    for v_id, v in vertices.items():
        vtype = classifications[v_id]
        kl = v["kind_list"]

        # Collect the regions at this vertex in KIND-list order: [r1, r2, r3]
        regions = []
        for i in range(1, len(kl) - 1, 2):
            regions.append(kl[i])

        # Need at least two regions to form any link
        if len(regions) < 2:
            continue

        if vtype == "FORK" and len(regions) == 3:
            # One link for each pair
            add_link(links, regions[0], regions[1])
            print(f"[FORK] {v_id}: linked {regions[0]} - {regions[1]}")
            add_link(links, regions[1], regions[2])
            print(f"[FORK] {v_id}: linked {regions[1]} - {regions[2]}")
            add_link(links, regions[0], regions[2])
            print(f"[FORK] {v_id}: linked {regions[0]} - {regions[2]}")

        elif vtype == "ARROW":
            a = angles_map.get(v_id, [])
            if len(a) == 3 and len(regions) == 3:
                # Map the >180 sector to the two regions that should be linked
                if a[0] > 180:
                    add_link(links, regions[1], regions[2])
                    print(f"[ARROW] {v_id}: linked {regions[1]} - {regions[2]}")
                elif a[1] > 180:
                    add_link(links, regions[0], regions[2])
                    print(f"[ARROW] {v_id}: linked {regions[0]} - {regions[2]}")
                else:
                    add_link(links, regions[0], regions[1])
                    print(f"[ARROW] {v_id}: linked {regions[0]} - {regions[1]}")
            elif len(regions) >= 2:
                # Fallback: if somehow not a 3-region vertex, link first two
                add_link(links, regions[0], regions[1])
                print(f"[ARROW] {v_id}: linked {regions[0]} - {regions[1]}")

        # L, T, MULTI -> no links

    return links


# ---------------------------
# Grouping (GLOBAL and SINGLEBODY)
# ---------------------------
def collect_all_regions(vertices):
    """
    Gather every region id present in any vertex KIND list.

    This ensures each (non-background) region starts in its own nucleus,
    even if it didn't participate in any link.
    """
    regions = set()
    for v in vertices.values():
        for item in v["kind_list"]:
            if isinstance(item, int):
                regions.add(item)
    return regions


def initialize_nuclei_all_regions(vertices, background):
    """
    Initialize the nuclei list: one singleton nucleus per region,
    excluding the background region.
    """
    regions = collect_all_regions(vertices)
    return [{r} for r in sorted(regions) if r != background]


def merge_nuclei(nuclei, a, b):
    """
    Merge the two nuclei that contain regions a and b, if they are different.

    Returns:
        True if a merge occurred, else False.
    """
    for n1 in nuclei:
        if a in n1:
            for n2 in nuclei:
                if b in n2 and n1 is not n2:
                    n1.update(n2)
                    nuclei.remove(n2)
                    return True
    return False


def run_GLOBAL(links, vertices, background):
    """
    GLOBAL (strong-evidence) grouping:
    - Count links between region pairs (ignore background).
    - Initialize one nucleus per non-background region.
    - Repeatedly merge any two nuclei that have 2 or more links between them.
    """
    # Count links per unordered region pair, excluding background
    link_counts = defaultdict(int)
    for a, b in links:
        if background not in (a, b):
            link_counts[tuple(sorted((a, b)))] += 1

    # Start each region in its own nucleus
    nuclei = initialize_nuclei_all_regions(vertices, background)

    # Merge while possible
    changed = True
    while changed:
        changed = False
        for (a, b), n in list(link_counts.items()):
            if n >= 2 and merge_nuclei(nuclei, a, b):
                print(f"[GLOBAL] merged {a}, {b}")
                changed = True
    return nuclei


def run_SINGLEBODY(links, nuclei, background):
    """
    SINGLEBODY (weaker-evidence) grouping:
    If a single-region nucleus has exactly one neighbor nucleus via any links,
    and that neighbor nucleus has multiple regions, merge t
    """
    # Build an undirected adjacency map of regions (ignoring background)
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
                # exactly one neighbor region in the graph
                if len(link_map[region]) == 1:
                    other = next(iter(link_map[region]))
                    if merge_nuclei(nuclei, region, other):
                        print(f"[SINGLEBODY] merged {region} with {other}")
                        changed = True
                        break
    return nuclei


# ---------------------------
# Output helpers
# ---------------------------
def extract_bodies(nuclei):
    """
    Convert nuclei (sets of regions) into a sorted list of region lists for printing.
    """
    bodies = []
    for n in nuclei:
        bodies.append(sorted(list(n)))
    return bodies


def print_bodies(bodies):
    """
    Pretty-print the final bodies.
    """
    print("\n===== FINAL BODIES =====")
    if not bodies:
        print("(no bodies detected)")
    for i, body in enumerate(bodies, 1):
        print(f"(BODY {i}: {body})")


# ---------------------------
# Main
# ---------------------------
def main():
    """
    Entry point. Run as:
        python3 Main.py cube.json
    or
        python3 Main.py one.json
    If no filename provided, defaults to one.json.
    """
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "one.json"

    print(f"\n>>> Loading scene: {filename}")
    vertices, background = load_scene(filename)

    # Compute sector angles from KIND lists, then classify vertices
    angles_map = get_sector_angles(vertices)
    classifications = {v: classify_vertex(v, angles_map) for v in vertices}

    print("\nVertex classifications:")
    for v, t in classifications.items():
        print(f"  {v}: {t}")

    # Generate strong links based on classifications
    links = generate_links(vertices, classifications, angles_map)
    print("\nGenerated links:", links)

    # GLOBAL + SINGLEBODY grouping
    nuclei_global = run_GLOBAL(links, vertices, background)
    nuclei_final = run_SINGLEBODY(links, nuclei_global, background)

    # Output bodies
    bodies = extract_bodies(nuclei_final)
    print_bodies(bodies)


if __name__ == "__main__":
    main()