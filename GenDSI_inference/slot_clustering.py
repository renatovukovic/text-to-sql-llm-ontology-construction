### based https://github.com/emorynlp/GenDSI/blob/main/dsi/s2s_dsi.py

# coding=utf-8
#
# Copyright 2024
# Heinrich Heine University Dusseldorf,
# Faculty of Mathematics and Natural Sciences,
# Computer Science Department
#
# Authors:
# Renato Vukovic (renato.vukovic@hhu.de)
#
# This code was generated with the help of AI writing assistants
# including GitHub Copilot, ChatGPT, Bing Chat.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from pathlib import Path
from sentence_transformers import SentenceTransformer
import torch
from tqdm import tqdm
import os
from collections import defaultdict
import random

import hdbscan

def flatten_key_value_pairs(dict_list):
    result = []
    for d in dict_list:
        for key, value in d.items():
            result.append(f"{key}: {value}")
    return result

def save_cluster_data(all_predictions_list, labels, dataset_name):
	assert len(all_predictions_list) == len(labels), "Mismatch between predictions and labels"

	# Create clusters directory if it doesn't exist
	os.makedirs("clusters", exist_ok=True)

	# File paths
	base_path = os.path.join("clusters", dataset_name)
	predictions_path = base_path + "_predictions.pt"
	labels_path = base_path + "_labels.pt"
	cluster_lists_path = base_path + "_clusters.pt"

	# Save predictions and labels
	torch.save(all_predictions_list, predictions_path)
	torch.save(labels, labels_path)

	# Build cluster -> list of predictions
	cluster_dict = defaultdict(list)
	noise_slotvalue_predictions = []
	for pred, label in zip(all_predictions_list, labels):
		if label != -1:  # Skip noise
			cluster_dict[label].append(pred)
		else:
			noise_slotvalue_predictions

	# Convert to sorted list of lists
	cluster_lists = [cluster_dict[k] for k in sorted(cluster_dict)]

	# Save cluster lists
	torch.save(cluster_lists, cluster_lists_path)

	print(f"Saved predictions, labels, and {len(cluster_lists)} clusters to 'clusters/'")

	print(f"There are {len(noise_slotvalue_predictions)} slotvalue predictions filtered, e.g. \n{random.sample(noise_slotvalue_predictions, min(10, len(noise_slotvalue_predictions)))}")

	return cluster_lists

def main():
    


	#load the state generator predictions
	dataset = "multiwoz21"

	results_directory = Path("predictions")
	result_filename = f"{results_directory}/{dataset}_GenDSI_slot_predictions.pt"

	state_generator_prediction_dict = torch.load(result_filename, weights_only=False)

	#put all the predictions into one set
	all_predictions_set = set()
	for split in state_generator_prediction_dict:
		for dial_id, prediction_list in tqdm(state_generator_prediction_dict[split].items()):
			flattened_prediction = flatten_key_value_pairs(prediction_list)
			#print(flattened_prediction)
			all_predictions_set.update(flattened_prediction)

	

	all_predictions_list = list(all_predictions_set)

	print(len(all_predictions_list))
	print(all_predictions_list[:20])
			

	

	
	#embed with sentence transformer
	embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
	print("embed the slot value predictions")
	embedded_slot_value_predictions = embedding_model.encode(all_predictions_list, show_progress_bar=True, convert_to_tensor=True)

	# Convert tensor to numpy array if needed
	embedding_array_cpu = embedded_slot_value_predictions.cpu().numpy()

	# Run HDBSCAN
	clusterer_cpu = hdbscan.HDBSCAN(
		min_samples=5,
		min_cluster_size=25,
		cluster_selection_epsilon=0.3
	)
        
	print("start hdbscan clustering")
	cluster_labels_cpu = clusterer_cpu.fit_predict(embedding_array_cpu)
        
	
	print("save the predictions")
	cluster_lists = save_cluster_data(all_predictions_list, cluster_labels_cpu, dataset)
	print("cluster predictions saved")

	#print some examples of clusters
	print(f"cluster examples for the {len(cluster_lists)} slot clusters")
	for cluster in cluster_lists:
		print(random.sample(cluster, min(5, len(cluster))))
		print()

	print(f"{len(cluster_lists)} slot clusters")


if __name__=="__main__":
	main()