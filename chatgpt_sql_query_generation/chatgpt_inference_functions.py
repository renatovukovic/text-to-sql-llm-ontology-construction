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

import backoff
import openai
from sentence_transformers import SentenceTransformer
import logging
import tiktoken
import random

from sql_interpretation.sql_interpreter import execute_multiple_queries_with_errors, extract_sql_from_response, execute_multiple_queries_with_errors_with_concept_matching, analyse_sql_query

#exponential backoff
@backoff.on_exception(backoff.expo, openai.RateLimitError)
def chatcompletions_with_backoff(client, **kwargs):
    return client.chat.completions.create(**kwargs)


#completion with retries
def completion_with_retries(client: openai.Client, 
                            model_name: str, 
                            input_messages: list[dict[str, str]],
                            logger: logging.Logger,
                            retries: int = 100,
							temperature: float = 0) -> openai.ChatCompletion:
        
	"""
    Function to get a completion from the model with retries in case of an exception.
    Returns the chatcompletion if it was successful, otherwise returns the exception as a string.
    
    Parameters:
    client: openai.Client
		The openai client object.
	model_name: str
		The name of the model to be used.
	input_prompt: str
		The input prompt for the model.
	logger: logging.Logger
		The logger object for logging.
	retries: int
		The number of retries in case of an exception.
	temperature: float
		temperature to be used by the model
    
      """

	#pprint.pprint(input_messages)

	#retry 100 times if an exception occurs, as the server is overloaded quite often, retry could solve this
	for i in range(retries):
	#catch any exception and save the responses so far
		try: 
			response = chatcompletions_with_backoff(
				client=client,
				model=model_name,
				messages=truncate_messages(input_messages, max_tokens=120000), #truncate messages to fit gpt-4o-mini context window of 128k and allow for response
				temperature=temperature,
				seed=42,
			)       
		except KeyboardInterrupt as e: #catch keyboard interrupt if I want to stop program
			raise(e)
		except openai.APIError as e: #catch any exception like time out or rate limit error and save the responses so far
			if i < retries:
				logger.info("Exception occured, try again.")
				logger.info(e)
				continue #try again
			else:
				raise(e)

		
		break #stop the for loop if getting the response succeeded, i.e. no exception was raised

	return response

def truncate_messages(messages: list[dict[str, str]], max_tokens: int = 120000, model: str = "gpt-4o-mini") -> list[dict[str, str]]:
    """
    Truncates a list of chat messages to ensure the total token count does not exceed `max_tokens`.
    The system message (first message) is always preserved. If necessary, it trims tokens from
    the start of subsequent messages while maintaining as much content as possible.

    Args:
        messages (list[dict[str, str]]): list of chat messages, each containing 'role' and 'content'.
        max_tokens (int): Maximum allowed token count for the entire message history.
        model (str): The OpenAI model to use for tokenization.

    Returns:
        list[dict[str, str]]: The truncated list of messages that fits within `max_tokens`.
    """
    if not messages:
        return []

    enc = tiktoken.encoding_for_model(model)

    # Tokenize each message and store its length
    tokenized_messages = [
        {"role": msg["role"], "content": msg["content"], "tokens": enc.encode(msg["content"])}
        for msg in messages
    ]

    # If there's a system message, keep it separate
    system_message = tokenized_messages[0] if tokenized_messages[0]["role"] == "system" else None
    non_system_messages = tokenized_messages[1:] if system_message else tokenized_messages

    # Calculate total token count
    total_tokens = sum(len(msg["tokens"]) for msg in tokenized_messages)

    # If we exceed max_tokens, start truncating from the beginning of non-system messages
    while total_tokens > max_tokens and non_system_messages:
        first_msg = non_system_messages[0]
        excess_tokens = total_tokens - max_tokens

        if len(first_msg["tokens"]) <= excess_tokens:
            # If the first message is small enough, remove it completely
            total_tokens -= len(first_msg["tokens"])
            non_system_messages.pop(0)
        else:
            # Otherwise, trim only the necessary tokens from the start
            first_msg["tokens"] = first_msg["tokens"][excess_tokens:]
            first_msg["content"] = enc.decode(first_msg["tokens"])
            total_tokens = max_tokens  # Now within the limit

    # Reconstruct the messages list
    truncated_messages = [{"role": msg["role"], "content": msg["content"]} for msg in non_system_messages]

    # Ensure the system message is included at the start if it exists
    if system_message:
        truncated_messages.insert(0, {"role": system_message["role"], "content": system_message["content"]})

    return truncated_messages

def db_query_and_update(input_text: str, 
						prompt_dict: dict[str, str],
						database_path: str, 
						client: openai.Client, 
						logger: logging.Logger, 
						model_name: str = "gpt-4o-mini", 
						use_message_context: bool = True,
						max_db_results: int = 5,
						similarity_model: SentenceTransformer = None, 
						with_concept_matching: bool = False,
						do_not_execute_matched_update_queries: bool = True,
						do_not_execute_all_update_queries: bool = False,
						with_dst_step: bool = False,
						return_column_values: bool = False,
						dialogue_success_label: str = None) -> tuple[openai.ChatCompletion, object, dict]:
	"""
	Function to query the database and update the database with the given query.

	In the first step the current tables in the DB are queried.
	In the second step the model is prompted to generate SQL queries to get the column information from the relevan tables for the current input (PRAGMA table_info(table_name)). The list of table names is in the prompt for this step.
	In the third step the model should generate SELECT queries to get the relevant information from the tables based on the column information.
	In the fourth step the model should generate the query to update the database with the missing information based on the SELECT results: CREATE TABLE, INSERT INTO, UPDATE, DELETE, ALTER TABLE, DROP TABLE, etc.
	In the second step the input and the tables are the input, in the subsequent steps they are part of the context in the chat completion API.

	:param input_text: The input text that the database queries/updates are based on. e.g. dialogue
	:param prompt_dict: The dictionary containing the prompts for each step of the database query/update process.
	:param database_path: The path to the database that is queried and updated.
	:param client: The OpenAI client.
	:param model_name: The name of the model used for generating responses.
	:param max_db_results: The maximum number of database results to return for a select query
	:param use_message_context: Boolean flag. If True, builds the context using a `messages` dictionary structure.
	:param similarity_model: The SentenceTransformer model used for similarity matching.
	:param with_concept_matching: Boolean flag. If True, uses concept matching to match concepts (tables, columns, values) in a prediction to the concepts already in the DB if they do not match exactly.
	:param do_not_execute_matched_update_queries: Boolean flag. If True, does not execute the similarity matched update queries on the database.
	:param do_not_execute_all_update_queries: Boolean flag. If True, does not execute the update queries on the database.
	:param with_dst_step: Boolean flag. If True, includes the DST step in the process as the fourth step. In that case in the last step there is no additional DB result as input to the prompt, so the format db_results is not used.
	:param return_column_values: Boolean flag. If True, return the possible values in the pragma query results of the second step for each column
	:param dialogue_success_label: string that indicates whether the dialogue was successful or not, only used when set

	:return: The database updates (i.e. final response), the context (messages if the flag is True, otherwise a string), 
				and a dictionary containing token counts for input and output.
	"""

	#check that the similarity model is not none if concept matching is used
	if with_concept_matching and similarity_model is None:
		raise ValueError("Similarity model must be provided if concept matching is used.")
	# Initialize context and messages
	context = input_text
	messages = [{"role": "system", "content": "You are an expert in sqlite3 queries for python. You are a helpful assistant that gets dialogues as input and should fill a database using SQLite3 queries."}]
	final_prompt = input_text

	# Steps as per the docstring
	steps = list(prompt_dict.keys())


	#db_updates = ""  # To collect the final database update results
	total_input_tokens = 0
	total_output_tokens = 0

	response = None

	#step 1 that is done without LLM
	#get the list of current tables from the database
	table_name_query = "SELECT name FROM sqlite_master WHERE type='table';"
	table_names = execute_multiple_queries_with_errors(database_path, table_name_query)[0][1]
	table_names = [table_name[0] for table_name in table_names]
	#if table names are empty have a message that the DB is empty
	if not table_names:
		table_names = "There are no tables yet, since the database is empty."

	#if there is the table "sqlite_sequence" in the list of tables, remove it
	if "sqlite_sequence" in table_names:
		table_names.remove("sqlite_sequence")

	db_result = table_names

	do_not_execute_update_queries = True

	for step in steps:
		# Prepare the prompt for the current step
		if not (step == "step5" and with_dst_step): # if dst is used in the last step, there is no db result input, since DST does not yield a db result
			step_prompt = prompt_dict[step].replace("{db_result_input}", str(db_result))
		else:
			if dialogue_success_label:
				step_prompt = dialogue_success_label + "\n\n" + prompt_dict[step] 
			else:
				step_prompt = prompt_dict[step]
		if step == "step2": #add the input text, e.g. dialogue
			step_prompt += f"\n\n{input_text}"
		
		if use_message_context:
			# Add the user's input to the messages
			messages.append({"role": "user", "content": step_prompt})
		else:
			final_prompt += f"\n\n{step_prompt}"


		input_message = messages if use_message_context else [
				{"role": "system", "content": "You are an expert in sqlite3 queries for python. You are a helpful assistant that gets dialogues as input and should fill a database using SQLite3 queries."},
				{"role": "user", "content": final_prompt}
			]
		# Generate a response from ChatGPT
		try: 
			response = completion_with_retries(
				client,
				model_name,
				input_message,
				logger,
			)
		except KeyboardInterrupt as e:
			raise(e)
		except openai.APIError as e:
			raise(e)
		except openai.BadRequestError as e:
			raise(e)	

		# Extract the model's response
		try:
			response_text = response.choices[0].message.content
		except TypeError as e:
			raise(e)
		
		if use_message_context:
			# Add the system's response to the messages
			messages.append({"role": "assistant", "content": response_text})
		else:
			final_prompt += f"\n\n{response_text}"

		# Update token counts from the API response
		total_input_tokens += response.usage.prompt_tokens
		total_output_tokens += response.usage.completion_tokens
		
		# Extract SQL queries from the response
		sql_queries = extract_sql_from_response(response_text)
		
		if step == steps[-1] and not do_not_execute_all_update_queries: #now execute update queries
			do_not_execute_update_queries = False

		# Execute each SQL query and capture results or errors
		formatted_execution_results = ""
		for query in sql_queries:

			

			if with_concept_matching and step != "step5": #in the final step the LLM should decide which queries should be executed based on the concept matching before, so no additional concept matching is needed
				execution_results = execute_multiple_queries_with_errors_with_concept_matching(database_path, query, similarity_model, do_not_execute_matched_update_queries=do_not_execute_matched_update_queries, do_not_execute_all_update_queries=do_not_execute_update_queries, n_similar_entries=2)
			else:
				execution_results = execute_multiple_queries_with_errors(database_path, query, do_not_execute_update_queries=do_not_execute_update_queries)
			# Append execution results to the DB updates and context
			#db_updates += f"\n\n{execution_results}"
			#format the execution results in with query before the query and DB results before the update message
			if step == "step2":# format the pragma queries to only return the column name and data type
				for result in execution_results:
					query_string = f"Query: \n{result[0]}"
					db_result_list = result[1]
					result_string = "DB Result:"
					if "PRAGMA" in query_string and db_result_list and isinstance(db_result_list, list):
						for column in db_result_list:
							result_string += f"\n{column[1]}: {column[2]}"
							if return_column_values: #get some column values for each column
								try:
									analysis_dict = analyse_sql_query(result[0])
								except Exception as e:
									continue
								if not analysis_dict["table_names"]:
									continue
								table_name = analysis_dict["table_names"][0]
								get_all_values_for_column_query = f"SELECT {column[1]} FROM {table_name};"
								column_value_results = execute_multiple_queries_with_errors(database_path, get_all_values_for_column_query, do_not_execute_update_queries=do_not_execute_update_queries)
								column_values = column_value_results[0][1]
								column_values = list(set([val[0] for val in column_values])) #get rid of the tuples for the results and remove duplicates
								#if there are too many values, then truncate by choosing randomly
								sample_values_string = ""
								if len(column_values) > 30:
									column_values = random.sample(column_values, 30)
									sample_values_string = "sample of "
								#add the values to the results for each column
								if not column_values: #no values in this column yet so add a string describing that
									column_values = "No values in this column yet."
								result_string += f"\n{sample_values_string}possible values for this column: {column_values}"

					else:
						#check the length of the db result (if it is a list) and truncate it if there are more than max_db_results rows
						#if result is an empty list, turn it to a message string stating that there are no results
						if not db_result_list or not isinstance(db_result_list, list):
							db_result_list = "No results for this query."
						if type(db_result_list) == list and len(db_result_list) > max_db_results:
							db_result_list = db_result_list[:max_db_results]
							result_string += f"\n{db_result_list}\nResults truncated to the first {max_db_results} rows."
						else:
							result_string += f"\n{db_result_list}"

					formatted_execution_results += f"\n\n{query_string}\n{result_string}"

			else:
				#formatted_execution_results += "\n\n".join([f"Query: \n{feedback[0]}\nDB Result: \n{feedback[1]}\n" for feedback in execution_results])
				try:
					for query, db_result_list in execution_results:
						#if result is an empty list, turn it to a message string stating that there are no results
						if not db_result_list:
							db_result_list = "No results for this query."
						#truncate the db result if there are more than max_db_results rows, check if it is a list because it can also be an update message
						if type(db_result_list) == list and len(db_result_list) > max_db_results:
							db_result_list = db_result_list[:max_db_results]
							formatted_execution_results += f"\n\nQuery: \n{query}\nDB Result: \n{db_result_list}\nResults truncated to the first {max_db_results} rows."
						else:
							formatted_execution_results += f"\n\nQuery: \n{query}\nDB Result: \n{db_result_list}"
				except ValueError as e:
					print(f"execution_results: {execution_results}")
					raise(e)
		#set the db_result for the next step
		db_result = formatted_execution_results
			

		# Update the context for the next step
		context = messages if use_message_context else final_prompt

	# Return the database updates, final context, and token usage
	token_usage = {
		"prompt_tokens": total_input_tokens,
		"completion_tokens": total_output_tokens
	}

	final_response = response

	return final_response, context, token_usage







#function for parsing the prompt dict from the prompt txt file for the database query/update process
def parse_db_query_update_prompt_string(input_text: str, 
					requery_with_similar_update_queries: bool = False, 
					with_dst_step: bool = False,
					dst_annotation_step: bool = False) -> dict:
	"""
	Parses a string into a dictionary with keys for each step.

	Args:
		input_text (str): The input string containing the text.
		requery_with_similar_update_queries (bool): Whether to include the fifth step for requerying with similar update queries instead of executing them based on similarity threshold, i.e. LLM decides if true
		with_dst_steps (bool): Whether to include the DST steps in the pipeline after the select query generation as additional input for update query generation
		dst_annotation_step (bool): whether to do DST annotation step instead of updates

	Returns:
		dict: A dictionary with keys 'step_2', 'step_3', and 'step_4', and their respective text as values.
	"""

	if requery_with_similar_update_queries:
		steps = {
			"step2": "#### PRAGMA QUERIES STEP 2 ####",
			"step3": "#### SELECT QUERIES STEP 3 ####",
			"step4": "#### UPDATE QUERIES STEP 4 ####",
			"step5": "#### CHOOSE WHICH OF THE SIMILAR QUERIES TO EXECUTE STEP 5 ####"
		}
	elif dst_annotation_step:
		steps = {
			"step2": "#### PRAGMA QUERIES STEP 2 ####",
			"step3": "#### SELECT QUERIES STEP 3 ####",
			"step4": "#### DST ANNOTATION WITH DB RESULTS STEP 4 ####"
		}
	elif with_dst_step:
		steps = {
			"step2": "#### PRAGMA QUERIES STEP 2 ####",
			"step3": "#### SELECT QUERIES STEP 3 ####",
			"step4": "#### DST WITH DB RESULTS STEP 4 ####",
			"step5": "#### UPDATE QUERIES STEP 5 ####"
		}
	else:

		steps = {
			"step2": "#### PRAGMA QUERIES STEP 2 ####",
			"step3": "#### SELECT QUERIES STEP 3 ####",
			"step4": "#### UPDATE QUERIES STEP 4 ####"
		}

	parsed_data = {key: "" for key in steps.keys()}
	current_step = None

	# Split the input string into lines
	lines = input_text.splitlines()

	for line in lines:
		line = line.strip()  # Remove leading/trailing whitespace
		if line in steps.values():
			# Identify the current step
			current_step = next(key for key, value in steps.items() if value == line)
		elif current_step:
			# Append line to the current step's content
			parsed_data[current_step] += (line + "\n")

	# Strip the final trailing newline from each step's content
	for key in parsed_data:
		parsed_data[key] = parsed_data[key].strip()

	return parsed_data

	

def batch_dialogues(dialogues: list[dict[str, str]], batch_size: int) -> list[list[dict[str, str]]]:
	"""
	Groups dialogues into batches based on the specified criteria.

	Args:
		dialogues (list[dict[str, str]]): list of dialogues.
		batch_size (int): The size of each batch.

	Returns:
		list[list[dict[str, Any]]]: list of batches, where each batch is a list of dialogues.
	"""

	# Default: No specific mixing strategy, just split into batches
	batches = [dialogues[i:i + batch_size] for i in range(0, len(dialogues), batch_size)]

	return batches