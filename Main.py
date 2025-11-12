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
