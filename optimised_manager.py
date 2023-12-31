import pandas as pd
import numpy as np
import networkx as nx

from memory_profiler import profile

import pickle
import gzip




class GraphManager:
    #@profile
    def __init__(self, data_path):

        self.data_path = data_path

        font_embeddings_path = f'{data_path}/embeddings/all_font_embeddings.npz'
        self.font_embeddings_array = self.load_npz(font_embeddings_path)

        dict_font_labels_to_indices_path= f'{data_path}/embeddings/font_name_to_index.pickle'
        self.dict_font_labels_to_indices= self.load_data_dict(dict_font_labels_to_indices_path)
        self.dict_font_indices_to_labels = self.invert_dict(self.dict_font_labels_to_indices)

    def font_index_to_image_path(self, font_index, image_folder_path):

        font_label = self.dict_font_indices_to_labels[font_index]

        image_file_name = f'{font_label}_Aa.png'

        font_image_path = f'{image_folder_path}/{image_file_name}'

        return font_image_path

    def invert_dict(self, dictionary):
        return {v: k for k, v in dictionary.items()}
    
    def load_data_dict(self, file_path):
        with open(file_path, 'rb') as handle:
            loaded_dict = pickle.load(handle)
        return loaded_dict
    
    def load_npz(self, file_path):
        with np.load(file_path) as data:
            numpy_array = data['array']

        return numpy_array

    #@profile
    def load_dicts(self, data_path):
        dict_names = ["font_name_to_index", ""]

        for name in dict_names:
            with gzip.open(f'{data_path}{name}.pkl.gz', 'rb') as f:
                setattr(self, name, pickle.load(f))

    def load_list_of_lists(self, filepath, filename):
        with open(filepath + filename, 'rb') as f:
            return pickle.load(f)


    def convert_numpy_to_visjs_format(self, list_of_font_indices, reduced_data, image_folder_path):
        """
        This function converts the reduced dimensional data and corresponding labels into a format suitable for Vis.js.

        Parameters:
        reduced_data (numpy.ndarray): The reduced dimensional data obtained from t-SNE or another dimensionality reduction method.
        Each row is a sample and each column is a dimension (2D or 3D).

        labels_dict (dict): A dictionary mapping the label names to their corresponding indices in the reduced_data array.

        images_dict (dict): A dictionary mapping the label names to their corresponding image paths.
        Each key is a label and each value is a string representing the path to the image file corresponding to that label.

        Returns:
        nodes (list): A list of dictionaries where each dictionary represents a node for Vis.js.
        Each node dictionary contains the following key-value pairs:
        - 'id': the index of the sample
        - 'label': the label of the sample
        - 'shape': the shape of the node, here set as 'circularImage' for image representation
        - 'image': the path to the image file for the node
        - 'x' and 'y': the x and y coordinates of the node in the 2D plot
        - 'fixed': a dictionary specifying whether the x and y coordinates of the node are fixed. Here, both are set to True.
        """
        coordinate_distance_multiplier = 300

        nodes = []
        for font_index, coordinates in zip(list_of_font_indices, reduced_data):
            nodes.append({
                "id": font_index, 
                "label": self.dict_font_indices_to_labels[font_index],  # Fetch the label corresponding to the index
                "shape": "circularImage",  # Specify the shape of the node as a circular image
                "image": self.font_index_to_image_path(font_index, image_folder_path),  # Fetch the image path for the label
                "x": float(coordinates[0])*coordinate_distance_multiplier,  # Specify the x-coordinate of the node
                "y": float(coordinates[1])*coordinate_distance_multiplier,  # Specify the y-coordinate of the node
                "fixed": {"x": True, "y": True},  # Set the x and y coordinates as fixed
            })

        
        return nodes
    

