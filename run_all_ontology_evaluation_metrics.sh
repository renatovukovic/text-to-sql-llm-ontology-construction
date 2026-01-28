#!/bin/bash


config_name="multiwoz_test_prediction_config_default_prompt_with_DB_query_and_update_pipeline_return_column_values_and_dst_step_chatgpt_explanation_prompt_with_success"




# List of map strategies
map_strategies=("exact_match" "map_all" "map_highest" )

# Loop through each strategy
for map_strategy in "${map_strategies[@]}"; do
  echo "Running evaluation with mapping strategy: $map_strategy"
  
  poetry run python -m evaluation.ontology_aggregation_evaluation \
    --config_name "${config_name}" \
    --mapping_strategy "${map_strategy}" \
  
  echo "Finished evaluation with mapping strategy: $map_strategy"
done