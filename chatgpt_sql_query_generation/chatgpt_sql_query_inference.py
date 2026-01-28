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

import openai
from openai import OpenAI
from tqdm import tqdm
from pathlib import Path
import os
import argparse
from dotenv import load_dotenv
import torch
import pprint
from sentence_transformers import SentenceTransformer
import json
import pprint
import random

from chatgpt_sql_query_generation.chatgpt_sql_inference_configs import get_config
from chatgpt_sql_query_generation.chatgpt_inference_functions import completion_with_retries, db_query_and_update, parse_db_query_update_prompt_string, batch_dialogues
from handle_logging_config import setup_logging






def main():
	#get the config
	parser = argparse.ArgumentParser()
	parser.add_argument("--config_name", type=str, default="multiwoz_test_prediction_config_default_prompt", help="Name of the config to use for prediction")
	args = parser.parse_args()
	config = get_config(args.config_name)
	config_dict = config.to_dict()

	
	
	logger = setup_logging("chatgpt_sql_query_generation" + args.config_name)


	logger.info(f"Load dataset {config_dict['dataset']}")

	if config.dataset in ["multiwoz21", "sgd"]:

		with Path(f"data/dialogue_data/{config.dataset}_dialogues.json").open("r") as file:
			dialogue_text = json.load(file)
		logger.info("Data loaded")

		logger.info("Extract and preprocess dialogue text")


		for split in config_dict["splits"]:

			if config.batch_size == 1:
				if config.seed:
					dialogues = list(dialogue_text[split].items())
					random.seed(config.seed)
					random.shuffle(dialogues)
					shuffled_dialogues_dict = {}
					for dial_id, turn_text in dialogues:
						shuffled_dialogues_dict[dial_id] = turn_text
					dialogue_text[split] = shuffled_dialogues_dict


			else:
				dialogues = list(dialogue_text[split].items())
				#if there is a seed in the confige then randomly shuffle the dialogues based on the seed
				if config.seed:
					random.seed(config.seed)
					random.shuffle(dialogues)
					
				dialogues_in_batches = batch_dialogues(dialogues, config.batch_size)
				dialogue_text_batches = {}

				for batch in dialogues_in_batches:
					all_texts_in_batch = ""
					all_ids_in_batch = ""
					for entry in batch:
						all_ids_in_batch += f"| {entry[[0]]}"
						dialogue_text = entry[1]
						all_texts_in_batch += dialogue_text + "\n------------------------------\n"
					
					dialogue_text_batches[f"dialogues with ids: {all_ids_in_batch}"] = all_texts_in_batch

				dialogue_text[split] = dialogue_text_batches




	elif config.dataset in ["arxiv", "wikipedia"]: #load the OLLM linearised datasets
		linearised_dataset_path = f"../../../ollm/out/linearised_datasets/{config.dataset}/test_dataset.jsonl"
		with Path(linearised_dataset_path).open("r") as file:
			lineartestdata = [json.loads(line) for line in file]
		
		logger.info("Data loaded")


		logger.info(f"Prepare titles and abstracts with batch size {config.batch_size}")

		test_data_in_batches = [lineartestdata[i:i + config.batch_size] for i in range(0, len(lineartestdata), config.batch_size)]

		#go through it and gather the titles and abstracts
		dialogue_text = {"test": {}}
		for batch in test_data_in_batches:
			all_texts_in_batch = ""
			all_ids_in_batch = ""
			for entry in batch:
				entry_text = f"title: {entry['title']}\n\nabstract: \n{entry['abstract']}\n\n"
				all_texts_in_batch += entry_text
				all_ids_in_batch += f" | {entry['id']}"

			dialogue_text["test"][f"batch of articles with ids {all_ids_in_batch}"] = all_texts_in_batch

		
		
	#load openAI API key
	load_dotenv(Path(".env"))
	#client.api_key = os.getenv("OPENAI_API_KEY")
	client = OpenAI(
		organization=os.getenv("OPENAI_ORGANISATION_ID"),
		project=os.getenv("OPENAI_PROJECT_ID"),
		api_key = os.getenv("OPENAI_PROJECT_API_KEY"),
	)

	logger.info("Load prompt")
	prompt_name = config_dict["prompt_name"]
	with Path(f"chatgpt_sql_query_generation/prompts/{prompt_name}_prompt.txt").open("r") as promptfile:
		prompt = promptfile.read()

	use_db_query_pipeline_approach = True if "DB_select_and_update_pipeline" in prompt_name else False
	use_db_query_dst_pipeline_approach = True if "DB_select_DST_update_pipeline" in prompt_name else False

	database_path = ""
	prompt_dict = None


	if use_db_query_pipeline_approach or use_db_query_dst_pipeline_approach:
		database_directory = Path("sql_interpretation/databases/")
		database_name = args.config_name + "_database.db"
		database_path = database_directory / database_name
		logger.info(f"Use database in directory {database_directory} with name {database_name}")
	


	if use_db_query_pipeline_approach:
		logger.info("Use DB query pipeline approach")
		#prepare the prompt dict based on the input txt prompt file
		prompt_dict = parse_db_query_update_prompt_string(prompt)
		#check if there is a place holder for the batch size in the first step, then replace it with the actual batch size
		if "{X}" in prompt_dict["step2"]:
			prompt_dict["step2"] = prompt_dict["step2"].replace("{X}", str(config.batch_size))
		logger.info(f"Prompt dict: {pprint.pformat(prompt_dict)}")
	
	elif use_db_query_dst_pipeline_approach:
		logger.info("Use DB query DST pipeline approach")
		#prepare the prompt dict based on the input txt prompt file
		prompt_dict = parse_db_query_update_prompt_string(prompt, with_dst_step=True)
		#check if there is a place holder for the batch size in the first step, then replace it with the actual batch size
		if "{X}" in prompt_dict["step2"]:
			prompt_dict["step2"] = prompt_dict["step2"].replace("{X}", str(config.batch_size))
		logger.info(f"Prompt dict: {pprint.pformat(prompt_dict)}")


	logger.info(f"Concept matching for the queries is set to {config.use_concept_matching}")
	
	#if concept matching is used, load the sentence transformer model
	if config.use_concept_matching:
		logger.info("Load sentence transformer model")
		similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
		logger.info("Model loaded")

	else:
		similarity_model = None

	results_directory = Path("chatgpt_sql_query_generation/results")
	results_directory.mkdir(parents=True, exist_ok=True)
	result_filename = f"{results_directory}/{args.config_name}_responses.pt"
		
	#check whether a (unfinished) dictionary already exists, in case of exception during OpenAI query
	if Path(result_filename).is_file():
		response_per_dialogue = torch.load(result_filename, weights_only=False)
		logger.info("Loaded responses from file")
	else:
		#initialise the dialogue id, InstructGPT response dictionary
		response_per_dialogue = {}
		for split in config_dict["splits"]:
			response_per_dialogue[split] = {}

	logger.info("Start inference with OpenAI ChatGPT API")

	

	#count the total number of tokens as input and generated to estimate the cost
	total_prompt_tokens = 0
	total_completion_tokens = 0

	#print the first 2 responses
	response_count = 0
	for split in config_dict["splits"]:
		for dial_id, text in tqdm(dialogue_text[split].items()):
			#for wikipedia where batches of articles were input, check whether any id is already in the dial_id key, in the case the batch size was decreased afterwards
			all_ids_in_batch = dial_id.split("|")[1:]
			#check if any of the article ids was already part of an earlier query
			ids_already_in_batch = False
			for batch_key in response_per_dialogue[split].keys():
				if any(article_id in batch_key for article_id in all_ids_in_batch):
					ids_already_in_batch = True
					break
			if dial_id not in response_per_dialogue[split] and not ids_already_in_batch: #if there arise problems with connection or model only do the missing dialogues
				input_message = [{"role": "system", "content": "You are an expert in sqlite3 queries for python. You are a helpful assistant that gets dialogues as input and should fill a database using SQLite3 queries."}, {"role": "user", "content": prompt + "\n" + text}]
                

				try: 
					if use_db_query_pipeline_approach or use_db_query_dst_pipeline_approach:
						response_update, all_step_messages, token_usage = db_query_and_update(
							text, 
							prompt_dict, 
							database_path, 
							client, 
							logger, 
							model_name=config_dict["model_name"], 
							use_message_context=True,
							similarity_model=similarity_model,
							with_concept_matching=config.use_concept_matching,
							do_not_execute_matched_update_queries=not config.execute_matched_update_queries,
							do_not_execute_all_update_queries=config.requery_with_matched_update_queries,
							with_dst_step=use_db_query_dst_pipeline_approach,
							return_column_values=config.return_column_values)
						
						#save both the final response and all the messages in the pipeline
						response_per_dialogue[split][dial_id] = {"response": response_update, "all_step_messages": all_step_messages, "token_usage": token_usage}
						current_prompt_tokens =  token_usage["prompt_tokens"]
						current_completion_tokens =  token_usage["completion_tokens"]

						total_prompt_tokens += current_prompt_tokens
						total_completion_tokens += current_completion_tokens

						input_message = all_step_messages
						response = response_update
					else:
						response = completion_with_retries(
							client,
							config_dict["model_name"],
							input_message,
							logger,
						)

						response_per_dialogue[split][dial_id] = response

						#count the tokens
						current_prompt_tokens = response.usage.prompt_tokens
						current_completion_tokens = response.usage.completion_tokens

						total_prompt_tokens += current_prompt_tokens
						total_completion_tokens += current_completion_tokens

				except KeyboardInterrupt as e:
					torch.save(response_per_dialogue, result_filename)
					logger.info("Keyboard interrupt, the file was saved under",  result_filename)
					raise(e)
				except openai.APIError as e:
					torch.save(response_per_dialogue, result_filename)
					logger.info("An exception occured in 100 retries and the file was saved under",  result_filename)
					raise(e)
				
				except openai.BadRequestError as e:
					torch.save(response_per_dialogue, result_filename)
					logger.info("A different error occured and the file was saved under",  result_filename)
					raise(e)
				
				except TypeError as e:
					torch.save(response_per_dialogue, result_filename)
					logger.info("A Type Error occured and the file was saved under",  result_filename)
					raise(e)

				


				
				if response_count < 5:
					logger.info(f"Input at step {response_count} for dialogue {dial_id}: \n{pprint.pformat(input_message)}\n")
					#logger.info(f"Response at step {response_count} for dialogue {dial_id}: \n{response}\n")
					logger.info(f"Response at step {response_count} for dialogue {dial_id}: \n{response.choices[0].message.content}\n")
					logger.info(f"Prompt tokens: {current_prompt_tokens}, Completion tokens: {current_completion_tokens}\n")

				response_count += 1

				#every 50 dialogues save the responses checkpoint
				if response_count % 50 == 0:
					torch.save(response_per_dialogue, result_filename)
					logger.info(f"Responses saved under {result_filename} after {response_count} dialogues")
			
			
	#save the responses as torch file
	torch.save(response_per_dialogue, result_filename)
		
	logger.info(f"Program finished, responses saved under {result_filename}")

	#calculate the cost
	logger.info(f"Total prompt tokens: {total_prompt_tokens}, Total completion tokens: {total_completion_tokens}")
	#cost for gpt4o mini is $0.15 for one million input tokens and $0.6 for one million completion tokens
	cost = 0.15 * total_prompt_tokens / 1e6 + 0.6 * total_completion_tokens / 1e6
	logger.info(f"Estimated cost for model {config_dict['model_name']}: ${cost:.2f}")


if __name__ == "__main__":
	main()