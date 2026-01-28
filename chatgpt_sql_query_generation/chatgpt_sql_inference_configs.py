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
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from chatgpt_sql_query_generation.chatgpt_sql_query_config_class import chatgpt_sql_prediction_config


def get_config(config_name):
	#return config based on string name
	if config_name not in globals():
		raise ValueError(f"Config name {config_name} not found")
	return globals()[config_name]


##### multiwoz test prediction configs #####

### prompts rephrased by chatgpt understanding explanation ablations ###
#baseline
multiwoz_test_prediction_config_default_prompt_with_actions_and_intents_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="zeroshot_default_with_action_intent_chatgpt_explanation_rephrased"
)

#with DB query and update pipeline
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated"
)

#with select query concept matching
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_with_concept_matching_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated",
	use_concept_matching=True
)

### with DST step ###
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_and_dst_step_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
)

#similarity + DST
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_with_concept_matching_and_dst_step_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	use_concept_matching=True,
)

### with returning of possible values for columns in pragma queries ###
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated",
	return_column_values=True,
)

#column value examples + DST
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	return_column_values=True,
)

### with success mentioned in update prompt
multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt_with_success = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_with_success_policy_chatgpt_explanation_updated",
	return_column_values=True,
)

#gendsi config
multiwoz_test_GenDSI_config = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "multiwoz21",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_with_success_policy_chatgpt_explanation_updated",
)


##### sgd test prediction configs #####


### prompts rephrased by chatgpt understanding explanation ablations ###
#baseline
sgd_test_prediction_config_default_prompt_with_actions_and_intents_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="zeroshot_default_with_action_intent_chatgpt_explanation_rephrased"
)

#with DB query and update pipeline
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated"
)

#with select query concept matching
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_with_concept_matching_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated",
	use_concept_matching=True
)

### with DST step ###
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_and_dst_step_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
)

#concept matching + DST
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_with_concept_matching_and_dst_step_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	use_concept_matching=True,
)

### with returning of possible values for columns in pragma queries ###
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_chatgpt_explanation_updated = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_and_update_pipeline_chatgpt_explanation_updated",
	return_column_values=True,
)

#column value examples + DST
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	return_column_values=True,
)

### with success mentioned in update prompt
sgd_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt_with_success = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_with_success_policy_chatgpt_explanation_updated",
	return_column_values=True,
)


#gendsi config
sgd_test_GenDSI_config = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "sgd",
	splits = ["test"],
	prompt_name="DB_select_DST_update_pipeline_with_success_policy_chatgpt_explanation_updated",
)


### config for ArXiV dataset

arxiv_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_updated_prompt = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "arxiv",
	splits = ["test"],
	prompt_name="OLLM_dataset_prompts/DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	batch_size = 5,
	return_column_values=True,
)

### config for Wikipedia dataset

wikipedia_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_updated_prompt = chatgpt_sql_prediction_config(
	model_name = "gpt-4o-mini-2024-07-18",
	dataset = "wikipedia",
	splits = ["test"],
	prompt_name="OLLM_dataset_prompts/DB_select_DST_update_pipeline_chatgpt_explanation_updated",
	batch_size = 200,
	return_column_values=True,
)


