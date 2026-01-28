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

import argparse
from pathlib import Path
import torch
import json
import sys
from sentence_transformers import SentenceTransformer

#local imports
from chatgpt_sql_query_generation.chatgpt_sql_inference_configs import get_config
from evaluation.ontology_evaluation_functions import build_ontology_from_sql_queries, map_ontology, calculate_ontology_metrics, merge_dicts
from sql_interpretation.sql_interpreter import get_entire_database_structure
from handle_logging_config import setup_logging



def main():
	#get the config
	parser = argparse.ArgumentParser()
	parser.add_argument("--config_name", type=str, default="multiwoz_test_prediction_config_default_prompt", help="Name of the config to use for prediction")
	parser.add_argument("--mapping_strategy", type=str, default="map all", help="The mapping strategy to use for the ontology mapping")
	#add map to synonyms which should store true if given
	parser.add_argument("--map_to_synonyms", action="store_true", help="If true, map the ontology to synonyms")
	args = parser.parse_args()

	#setup logging
	logger = setup_logging(f"ontology_aggregation_evaluation_{args.config_name}_{args.mapping_strategy}")

	if "GenDSI" in args.config_name:
		logger.info("Evaluationg GenDSI Ontology prediction")
		config = get_config(args.config_name)
	else:
		config = get_config(args.config_name)
	config_dict = config.to_dict()

	#check that mapping strategy is valid
	valid_mapping_strategies = ["map_all", "map_highest", "exact_match"]
	if args.mapping_strategy not in valid_mapping_strategies:
		raise ValueError(f"Invalid mapping strategy. Choose from {valid_mapping_strategies}")
	
	

	map_strategy = args.mapping_strategy.replace("_", " ")


	#read the ontology
	logger.info(f"Reading the ontology from data/groundtruth_ontologies/{config_dict['dataset']}_ontology.json")
	with Path(f"data/groundtruth_ontologies/{config_dict['dataset']}_ontology.json").open("r") as f:
		gold_ontology = json.load(f)

	#merge all the ontologies for the differnt splits from the gold ontology
	splits = config_dict["splits"]
	merged_gold_ontology = gold_ontology[splits[0]]
	for split in splits[1:]:
		merged_gold_ontology = merge_dicts(merged_gold_ontology, gold_ontology[split])

	gold_ontology = merged_gold_ontology

	cosine_threshold = 0.436 #based on Lo et al., 2024 End-to-End Ontology Learning with Large Language Models

	logger.info(f"Using cosine similarity threshold of {cosine_threshold}")


	database_directory = Path("sql_interpretation/databases/")
	database_name = args.config_name + "_database.db"
	database_path = database_directory / database_name



	if "GenDSI" in args.config_name:
		logger.info(f"Reading ontology for dataset {config.dataset}")
		predicted_ontology = torch.load(f"GenDSI_inference/ontology_hierarchy_dicts/{config.dataset}_genDSI_ontology_prediction.pt", weights_only=False)
	#check if the db file exists and if so then just run get_entire_database_structure on the path
	elif database_path.exists():
		#get the ontology from the database
		logger.info(f"Reading the ontology from the database at {database_path}")
		predicted_ontology = get_entire_database_structure(database_path)
	else:
		#build the ontology from the sql queries
		logger.info(f"Building the ontology from the SQL queries and writing it to {database_path}")
		#get the results filename and read it
		results_directory = Path("chatgpt_sql_query_generation/results")
		result_filename = f"{results_directory}/{args.config_name}_responses.pt"

		#read the results
		logger.info(f"Reading the results from {result_filename}")
		response_dict = torch.load(result_filename, weights_only=False)
		similarity_model = None
		if config.execute_matched_update_queries:
			similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
		predicted_ontology, update_messages = build_ontology_from_sql_queries(response_dict, database_path, similarity_model=similarity_model)

	#if there is the "sqlite_sequence" table in the ontology then remove it
	if "sqlite_sequence" in predicted_ontology:
		predicted_ontology.pop("sqlite_sequence")

	mapping_result, predictions_by_class = map_ontology(gold_ontology, predicted_ontology, threshold=cosine_threshold, mapping_strategy=map_strategy, model_name='all-MiniLM-L6-v2')

	#logger.debug(f"Mapping result for system actions: {mapping_result['system actions']}")

	# Using the map_to_value_groups flag to apply synonym value groups mapping
	map_to_synonyms_flag = ""
	if args.map_to_synonyms:
		groups = gold_ontology["synonym value groups"]
		result = calculate_ontology_metrics(mapping_result, predictions_by_class, synonym_groups=groups, map_to_value_groups=True)
		map_to_synonyms_flag = "_mapped_to_synonyms"
	else:
		result = calculate_ontology_metrics(mapping_result, predictions_by_class)

	only_successful_dialogues_flag = ""

	#save the result
	evaluation_directory = Path("evaluation/ontology_evaluation_results")
	evaluation_directory.mkdir(parents=True, exist_ok=True)
	evaluation_filename = f"{evaluation_directory}/{args.config_name}_ontology_evaluation_results_{args.mapping_strategy}{map_to_synonyms_flag}{only_successful_dialogues_flag}.pt"

	logger.info(f"Saving the evaluation results to {evaluation_filename}")

	torch.save(result, evaluation_filename)

	#for the result print only the metrics, not the true positives etc.
	logger.info("Ontology Evaluation Results:")
	for key, value in result.items():
		logger.info(key)
		logger.info(f"F1: {value['f1']}")
		logger.info(f"Precision: {value['precision']}")
		logger.info(f"Recall: {value['recall']}\n")




if __name__ == "__main__":
	main()
