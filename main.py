# this is fixed-database branch


# Import necessary libraries
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Import personalised modules
#from database import *
from vector_database import *
from utils import *
from optimised_manager import *

# Memory optimisation
from memory_profiler import profile

#===================================================================
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#===================================================================
"""
TO DO:
    - It runs now. The main problem is that I am at 125% memory quota. 
      That is around 625MB, while my limit is 500MB.
"""


# Initialize the FastAPI application
app = FastAPI()

# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware setup to allow requests from the specified origins
origins = [
    'http://localhost',
    'http://127.0.0.1:8000',
    'https://primal-hybrid-391911.ew.r.appspot.com', #New for google cloud
    'http://localhost:8080',
    'https://msi-app-b9364c344d37.herokuapp.com',  # Allow your local frontend to access the server
    'https://msi-webapp-7ba91279a938.herokuapp.com',
    uri, # add neo4j sandbox graph database uri
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Jinja2 templates with the "templates" directory
templates = Jinja2Templates(directory="templates")

# ...
font_embeddings_path = './data/embeddings/all_font_embeddings.npz'
font_embeddings_array = load_npz(file_path= font_embeddings_path)

dictionary_path = './data/embeddings/font_name_to_index.pickle'
dict_font_labels_to_indices= load_data_dict(dictionary_path)
dict_font_indices_to_labels = {v: k for k, v in dict_font_labels_to_indices.items()}


all_font_labels = [label for label, index in dict_font_labels_to_indices.items()]


metrics = ['euclidean']     #['angular', 'euclidean', 'manhattan', 'hamming', 'dot']

font_vector_db = MultiMetricDatabase(dimensions=font_embeddings_array.shape[1], metrics= metrics, n_trees=30)

# Add all fonts to vector database
font_vector_db.add_vectors(font_embeddings_array, dict_font_labels_to_indices)



# Instantiate and initialize necessary components for the application
data_path = './data/'
graph_manager = GraphManager(data_path)

map_drug_diffusion_labels_to_indices, map_drug_diffusion_indices_to_labels, map_indication_diffusion_labels_to_indices, map_indication_diffusion_indices_to_labels = load_dictionaries(data_path)


#===================================================================
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#===================================================================
def find_similar_fonts(chosen_font_label, distance_metric='euclidean'):
    
    # Translate indication name to index in indication diffusion profiles, to retrieve diffusion profile
    #chosen_font_label = graph_manager.mapping_indication_name_to_label[chosen_indication_name]
    chosen_font_index = dict_font_labels_to_indices[chosen_font_label]
    chosen_font_embedding = font_embeddings_array[chosen_font_index]

    #====================================
    # Querying Vector Database to return drug candidates
    #====================================
    num_recommendations = 10

    query = chosen_font_embedding

    font_candidates_indices = font_vector_db.nearest_neighbors(query, distance_metric, num_recommendations)

    font_candidates_labels = [dict_font_indices_to_labels[index] for index in font_candidates_indices]
    #drug_candidates_names = [graph_manager.mapping_drug_label_to_name[i] for i in font_candidates_labels]

    return font_candidates_labels # List


def print_types(data, level=0):
    if isinstance(data, dict):
        for key, value in data.items():
            print('  ' * level + f"{key}: {type(value)}")
            print_types(value, level + 1)
    elif isinstance(data, list):
        if data:
            print('  ' * level + f"0: {type(data[0])}")
            print_types(data[0], level + 1)


# Define a Pydantic model for diseases, drugs, and GraphRequest
class Font(BaseModel):
    value: int
    name: str

class SimilarFontsRequest(BaseModel):
    font_index: int

class InterpolationRequest(BaseModel):
    font_1_index: int
    font_2_index: int
    interpolation_fraction: float



class GraphRequest(BaseModel):
    disease_label: str
    drug_label: str
    k1: int
    k2: int

class Node(BaseModel):
    node_id: int = Field(..., alias="id")
    label: str
    color: str
    shape: str

class Edge(BaseModel):
    from_node: int = Field(..., alias="from")
    to: int
    arrows: str

class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

class GraphResponse(BaseModel):
    MOA_network: GraphData
    console_logging_status: str

#====================================================================================================================
# Define application routes
#====================================================================================================================

@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request):
    """Serve the index.html page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/fonts", response_model= List[Font])
async def get_fonts():
    """Return a list of fonts"""
    list_of_fonts = [
        {"value": dict_font_labels_to_indices[label], "name": label}
        for label in all_font_labels
    ]
    return list_of_fonts

@app.post("/similar_fonts", response_model= List[Font])
async def get_similar_fonts(similar_fonts_request: SimilarFontsRequest):
    """Return a list of drugs based on the selected disease"""

    assert type(similar_fonts_request.font_index) == int

    chosen_font_label = dict_font_indices_to_labels[similar_fonts_request.font_index]

    font_candidates = find_similar_fonts(chosen_font_label=chosen_font_label, distance_metric='euclidean')
    list_of_font_candidates = [
        {"value": dict_font_labels_to_indices[label], "name": label}
        for label in font_candidates
    ]
    return list_of_font_candidates


@app.post("/interpolation", response_class=JSONResponse)
async def get_interpolation_data(request: InterpolationRequest):
    # Extract parameters from request
    #font_1_label = request.font_1_label
    #font_2_label = request.font_2_label

    font_1_index = request.font_1_index
    font_2_index = request.font_2_index

    interpolation_fraction = request.interpolation_fraction

    #font_1_index = dict_font_labels_to_indices[font_1_label]
    #font_2_index = dict_font_labels_to_indices[font_2_label]

    # Generate interpolated images
    font_1_image_b64, font_2_image_b64, interpolated_image_b64 = vae.generate_interpolated_images_b64(font_1_index, font_2_index, interpolation_fraction)
    
    # Create the response
    response = {
        "font_1_image": font_1_image_b64,
        "interpolated_image": interpolated_image_b64,
        "font_2_image": font_2_image_b64
    }

    return response


#============================================================================
# Visualise MOA network using vis.js
#============================================================================

@app.post("/graph", response_model=GraphResponse)
async def get_graph_data(request: GraphRequest):
    # Extract parameters from request
    disease_label = request.disease_label
    drug_label = request.drug_label
    k1 = request.k1
    k2 = request.k2

    #print(f'disease_label: {disease_label}')
    #print(f'drug_label: {drug_label}')
    #print(f'k1: {k1}')
    #print(f'k2: {k2}')

    # Derpy fix changing drug_label (which is actually a name right now) back into a label.
    drug_label = graph_manager.mapping_all_names_to_labels[drug_label]

    
    # Convert graph data into a format that vis.js can handle
    graph_data = graph_manager.convert_networkx_to_vis_graph_data(graph=MOA_subgraph,
                                                                  node_colors=MOA_subgraph_node_colors, 
                                                                  node_shapes=MOA_subgraph_node_shapes)

    print_types(graph_data)

    print(f'graph_data: {graph_data}')

    e = 'successfully retrieved subgraph from database'
    # Create the response
    response = {
        "MOA_network": graph_data,
        "console_logging_status": f'{e}',
    }

    return response


