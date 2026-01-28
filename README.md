# TeQoDO: Text-to-SQL Dialogue Ontology Construction

This is the code for the paper Text-to-SQL Dialogue Ontology Construction

## Data
We use the [Multi-WOZ 2.1 Data-set](https://github.com/budzianowski/multiwoz) 
and the [Schema-Guided Dialogue data-set](https://github.com/google-research-datasets/dstc8-schema-guided-dialogue). 

See the data folder for the Multi-WOZ and SGD dialogue text data and the ontologies in JSON files.

## Installation

Install [poetry](https://python-poetry.org).
Run the following command to install the dependencies:

```
poetry install
```

See the pyproject.toml file for the needed packages and versions.

## Inference

Run inference with the run script run_chatgpt_inference.sh.
```
./run_chatgpt_inference.sh
```

IMPORTANT: You need a .env file in the top level directory that stores your OpenAI API key under the name "OPENAI_PROJECT_API_KEY", your OpenAI organisation ID under "OPENAI_ORGANISATION_ID" and the project ID under "OPENAI_PROJECT_ID".

The config_name can be updated in the script. A list of all the configs is found in chatgpt_sql_query_generation/chatgpt_sql_inference_configs.py.

See the folder chatgpt_sql_query_generation for all the relevant code and prompts for inference. Also the responses for each dialogue for all the experimental setups can be found in the results folder. The SQLite interpretation code and the generated DB files from the experimental setups can be found in the sql_interpretation folder.

## Evaluation

Evaluate with the script run_all_ontology_evaluation_metrics.sh:
```
run_all_ontology_evaluation_metrics.sh
```
The config_name can be updated in the script. A list of all the configs is found in chatgpt_sql_query_generation/chatgpt_sql_inference_configs.py. The script produces a dictionary with all the metrics.

See the folder evaluation for all the code that is used for evaluation. The resulting file with evaluation results can be loaded using torch and contains keys describing the method for averaging (e.g. macro, micro or average over domains only), which contain three keys and values for f1, recall and precision, respectively.

See the GenDSI_inference folder for running inference with GenDSI and respective predictions for both datasets in GenDSI_inference/predictions folder. The inference is based on the [GenDSI repository](https://github.com/emorynlp/GenDSI/tree/main).


## OLLM Dataset Inference and Evaluation

To run the OLLM inference and evaluation first make sure to get the code from their [git repository](https://github.com/andylolu2/ollm) and follow the instructions for downloading the linearised data and the test graphs. You can then run the inference with the run_chatgpt_inference.sh script. Make sure to update the linearised_dataset_path variable in the chatgpt_sql_query_generation/chatgpt_sql_query_inference.py script to the path of the linearised OLLM data on your system.
For evaluation go through the OLLM_data_evaluation/evaluation_notebook.ipynb and follow it. Make sure to update the path to the respective test graphs. The code for the evaluation is taken entirely from the official OLLM repository, we only put together the evaluation functions and removed motif distance because of compatibility issues. Our added evaluation function all_evaluations can be found in OLLM_data_evaluation/eval/graph_metrics.py.


## Citation

```
TBA
```

## License
This project is licensed under the Apache License, Version 2.0 (the "License");
you may not use the files except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0