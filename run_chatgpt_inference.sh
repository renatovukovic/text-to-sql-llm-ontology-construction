#!/bin/bash

config_name="multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt_with_success"

poetry run python -u -m chatgpt_sql_query_generation.chatgpt_sql_query_inference \
	--config_name ${config_name}


