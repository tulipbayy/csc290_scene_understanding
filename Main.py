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
