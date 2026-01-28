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



import transformers as hf
from tqdm import tqdm
from pathlib import Path
#from convlab.util import load_dataset, load_ontology
import os
import argparse
import torch
import sys
import pprint

#local imports
from s2s_dsi import infer_state
sys.path.append("..")
from handle_logging_config import setup_logging

def main():
    
	device = 'cuda'

	dsi = hf.AutoModelForSeq2SeqLM.from_pretrained(
		'jdfinch/dialogue_state_generator'
	).to(device)

	tokenizer = hf.AutoTokenizer.from_pretrained('t5-base')

	#prepare the data

	dataset = "multiwoz21"

	logger = setup_logging("GenDSI_inference_" + dataset)

	splits = ["test"]
	
	dialogue_text = torch.load(f"data/{dataset}_genDSI_data.pt")

	logger.info(f"Data loaded: {dataset}")
	

	results_directory = Path("predictions")
	results_directory.mkdir(parents=True, exist_ok=True)
	result_filename = f"{results_directory}/{dataset}_GenDSI_slot_predictions.pt"

	#check whether a (unfinished) dictionary already exists, in case of exception during OpenAI query
	if Path(result_filename).is_file():
		prediction_dict = torch.load(result_filename)
		logger.info("Load existing prediction file.")
	else:
		#initialise the dialogue id, InstructGPT response dictionary
		prediction_dict = {}
		for split in splits:
			prediction_dict[split] = {}



	#run inference 
	response_count = 0
	logger.info(f"Start GenDSI inference on {dataset}")
	for split in splits:
		for dial_id, text in tqdm(dialogue_text[split].items()):
			if dial_id in prediction_dict[split]:
				continue

			#make predictions for all sets of two utterances
			all_predictions = []
			for i in range(2, len(text)+2, 2):

				current_index = min(len(text), i)
				current_turns = text[:current_index]
				prediction = infer_state(current_turns, dsi, tokenizer, device)
				all_predictions.append(prediction)
			
			
			prediction_dict[split][dial_id] = all_predictions

			response_count += 1

			if response_count < 5:
				logger.info(f"Dialogue input: \n\n{pprint.pformat(text)}")
				logger.info(f"GenDSI State prediction:\n\n{pprint.pformat(all_predictions)}")

			#every 50 dialogues save the responses checkpoint
			if response_count % 50 == 0:
				torch.save(prediction_dict, result_filename)
				logger.info(f"Responses saved under {result_filename} after {response_count} dialogues")
			
			
	#save the responses as torch file
	torch.save(prediction_dict, result_filename)

	logger.info(f"Program finished, responses saved under {result_filename}")



if __name__ == "__main__":
	main()