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

import logging
import sentence_transformers
import torch
from sentence_transformers import SentenceTransformer
from collections import defaultdict

from sql_interpretation.sql_interpreter import execute_multiple_queries_with_errors, get_entire_database_structure, extract_sql_from_response, execute_multiple_queries_with_errors_with_concept_matching


def find_hierarchy_level(data, target=None):
    """
    Function to find the hierarchy level of a target value in a dictionary and 
    return all values from that level. If no target is given, return all values 
    from the lowest hierarchy level.

    Args:
        data (dict): The nested dictionary structure.
        target: The value to find in the hierarchy (optional).

    Returns:
        list: List of values at the target's hierarchy level or lowest hierarchy level.
    """
    def traverse_dict(d, level):
        """Helper function to traverse dictionary and build hierarchy levels."""
        nonlocal found_level
        for key, value in d.items():
            if isinstance(value, dict):
                traverse_dict(value, level + 1)
            elif isinstance(value, (set, list, tuple)):  # Handle collections
                levels[level].extend(value)
                if target in value:
                    found_level = level
            else:
                levels[level].append(value)
                if value == target:
                    found_level = level

    levels = {}
    found_level = None
    max_level = 0

    # Populate levels and find the level of the target if specified
    def init_levels(d, current_level=0):
        nonlocal max_level
        max_level = max(max_level, current_level)
        levels.setdefault(current_level, [])
        for k, v in d.items():
            if isinstance(v, dict):
                init_levels(v, current_level + 1)

    init_levels(data)
    traverse_dict(data, 0)

    # Return values based on the target presence
    if target is not None and found_level is not None:
        return levels[found_level]
    elif target is None:
        return levels[max_level]
    else:
        return []  # Target not found in the dictionary


def merge_dicts(dict1, dict2):
    """
    Recursively merge two dictionaries. For keys with:
    - dict values: merge recursively
    - set values: union the sets
    - list values: concatenate the lists
    """
    for key, value in dict2.items():
        if key not in dict1:
            dict1[key] = value
        else:
            if isinstance(value, dict) and isinstance(dict1[key], dict):
                merge_dicts(dict1[key], value)
            elif isinstance(value, set) and isinstance(dict1[key], set):
                dict1[key] = dict1[key].union(value)
            elif isinstance(value, list) and isinstance(dict1[key], list):
                dict1[key] = dict1[key] + value  # or use list(set(...)) to deduplicate
            else:
                raise ValueError(f"Incompatible types for key {key}: {type(dict1[key])} and {type(value)}")
    return dict1




def build_ontology_from_sql_queries(
		chat_gpt_response_dict: dict, 
		database_path: str,
        execute_matched_update_queries: bool = False,
        similarity_model: SentenceTransformer = SentenceTransformer('all-MiniLM-L6-v2')) -> tuple[dict, list[tuple]]:
	"""
	Function to build ontology from SQL query
	:param chat_gpt_response_dict: dictionary with the chat gpt responses
	:param database_path: path to the database file
    :param execute_matched_update_queries: flag to execute the matched update queries, i.e. use the execute function with concept matching
	:return: dictionary with the ontology, ontology db file is saved to the disk
	:return: list with the database update messages (errors or success messages) for each executed query with dialogue id
	"""

	all_update_messages = []	

	for split in chat_gpt_response_dict:
		for dial_id, response in chat_gpt_response_dict[split].items():
			if "response" in response: #this is the case for the db query and update pipeline
				response = response["response"]
			response_text = response.choices[0].message.content
			sql_queries = extract_sql_from_response(response_text)
			# execute the SQL queries
			for query in sql_queries:
				# execute the query
				if execute_matched_update_queries:
					update_messages = execute_multiple_queries_with_errors_with_concept_matching(database_path, query, similarity_model)
				else:
					update_messages = execute_multiple_queries_with_errors(database_path, query)
				for message in update_messages:
					all_update_messages.append((dial_id, message))

	
	ontology_dict = get_entire_database_structure(database_path)

	return ontology_dict, all_update_messages




# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def compute_semantic_similarity(
    gold_items, predicted_items, threshold, mapping_strategy, model, 
    gold_intent_keys=None, gold_action_keys=None
):
    """
    Compute semantic similarity between gold ontology and predicted ontology items.
    Additionally, classify non-mapped predicted items into 'domains', 'user intents', or 'system actions'
    if `gold_intent_keys` and `gold_action_keys` are provided.

    Args:
        gold_items (list): List of gold ontology items.
        predicted_items (list): List of predicted ontology items.
        threshold (float): Threshold for cosine similarity.
        mapping_strategy (str): Strategy to use for mapping.
        model (str): Sentence transformer model to use.
        gold_intent_keys (list): List of gold intent keys.
        gold_action_keys (list): List of gold action keys.

    Returns:
        tuple: Tuple containing the mapping and non-mapped items.
    """
    logging.debug(f"Computing semantic similarity for {len(gold_items)} gold items and {len(predicted_items)} predicted items.")
    
    mapping = {}
    non_mapped_gold = set(gold_items)
    non_mapped_predicted = set(predicted_items)

    #initialise the mapping with all gold items as keys and empty lists as values
    for gold_item in gold_items:
        mapping[gold_item] = []
    
    if len(predicted_items) == 0 or len(gold_items) == 0: #no predicted items were mapped or there are no gold items e.g. for a slot
        return mapping, non_mapped_gold, non_mapped_predicted

    if mapping_strategy == "exact match":
        logging.info("Using exact matching strategy.")
        for gold_item in gold_items:
            #also add the versions for exact matching with an s at the end
            with_trailing_s_gold_item = gold_item + "s"
            exact_matches = [predicted_item for predicted_item in predicted_items if gold_item == predicted_item or with_trailing_s_gold_item == predicted_item]
            if exact_matches:
                mapping[gold_item] = exact_matches
                non_mapped_gold.discard(gold_item)
                non_mapped_predicted.difference_update(exact_matches)
        logging.debug(f"Exact matches found: {len(mapping)}")
        
        # If additional keys are not provided, return the original structure
        if gold_intent_keys is None and gold_action_keys is None:
            return mapping, non_mapped_gold, non_mapped_predicted

    else:
        logging.info("Using semantic similarity strategy.")
        gold_embeddings = model.encode(gold_items, convert_to_tensor=True).to(torch.device("cpu"))
        predicted_embeddings = model.encode(predicted_items, convert_to_tensor=True).to(torch.device("cpu"))

        similarity_scores = sentence_transformers.util.pytorch_cos_sim(gold_embeddings, predicted_embeddings).numpy()

        for i, gold_item in enumerate(gold_items):
            best_match = None
            best_score = -10000
            mapped_items = []
            
            for j, predicted_item in enumerate(predicted_items):
                score = similarity_scores[i, j]
                if score >= threshold:
                    mapped_items.append(predicted_item)
                    if score > best_score:
                        best_match = predicted_item
                        best_score = score
            
            if mapping_strategy == "map highest":
                if best_match:
                    non_mapped_predicted.discard(best_match)
                    mapping[gold_item] = [best_match]
                    non_mapped_gold.discard(gold_item)
                    logging.debug(f"Mapped '{gold_item}' to '{best_match}' with score {best_score}.")
            elif mapping_strategy == "map all":
                if mapped_items:
                    non_mapped_predicted.difference_update(mapped_items)
                    mapping[gold_item] = mapped_items
                    non_mapped_gold.discard(gold_item)
                    logging.debug(f"Mapped '{gold_item}' to {mapped_items}.")

    # If no additional keys are provided, return the original structure
    if (gold_intent_keys is None and gold_action_keys is None) or non_mapped_predicted == set():
        return mapping, non_mapped_gold, non_mapped_predicted

    # Process non-mapped predicted items with additional intent/action classification
    logging.info("Classifying non-mapped predicted items.")
    additional_classification = {"domains": set(), "user intents": set(), "system actions": set()}

    if gold_intent_keys is not None:
        gold_intent_embeddings = model.encode(gold_intent_keys, convert_to_tensor=True).to(torch.device("cpu"))
    if gold_action_keys is not None:
        gold_action_embeddings = model.encode(gold_action_keys, convert_to_tensor=True).to(torch.device("cpu"))
    predicted_embeddings = model.encode(list(non_mapped_predicted), convert_to_tensor=True).to(torch.device("cpu"))

    # Compute similarity to intent keys, action keys, and all gold items
    if gold_intent_keys is not None:
        #remove the keys from the gold_items
        gold_items = [item for item in gold_items if item not in gold_intent_keys]
        intent_scores = sentence_transformers.util.pytorch_cos_sim(predicted_embeddings, gold_intent_embeddings).numpy()
    if gold_action_keys is not None:
        #remove the keys from the gold_items
        gold_items = [item for item in gold_items if item not in gold_action_keys]
        action_scores = sentence_transformers.util.pytorch_cos_sim(predicted_embeddings, gold_action_embeddings).numpy()

    all_gold_embeddings = model.encode(gold_items, convert_to_tensor=True).to(torch.device("cpu"))
    domain_scores = sentence_transformers.util.pytorch_cos_sim(predicted_embeddings, all_gold_embeddings).numpy()

    # Classify each non-mapped predicted item
    for idx, predicted_item in enumerate(non_mapped_predicted):
        closest_intent_score = max(intent_scores[idx]) if gold_intent_keys is not None else float("-inf")
        closest_action_score = max(action_scores[idx]) if gold_action_keys is not None else float("-inf")
        closest_domain_score = max(domain_scores[idx])

        if closest_intent_score > closest_action_score and closest_intent_score > closest_domain_score:
            additional_classification["user intents"].add(predicted_item)
        elif closest_action_score > closest_intent_score and closest_action_score > closest_domain_score:
            additional_classification["system actions"].add(predicted_item)
        else:
            additional_classification["domains"].add(predicted_item)

    logging.info("Completed classification of non-mapped predicted items.")
    return mapping, non_mapped_gold, additional_classification



def map_top_level_keys(gold_keys, predicted_keys, model, threshold, mapping_strategy, gold_intent_keys, gold_action_keys,):
    """
    Map predicted ontology's top-level keys (domains, intents, actions) to gold ontology keys.
    """
    logging.debug(f"Mapping top-level keys: {len(gold_keys)} gold keys to {len(predicted_keys)} predicted keys.")

    #distinguish between domain, intent, and action keys for evaluation of false positives aftwerwards


    return compute_semantic_similarity(gold_keys, predicted_keys, threshold, mapping_strategy, model, gold_intent_keys, gold_action_keys)


# Function to recursively flatten the dictionary
def flatten_dict(d, flattened=None):
    if flattened is None:
        flattened = []
    
    for key, value in d.items():
        flattened.append(key)  # Add the key
        if isinstance(value, dict):  # If the value is another dictionary, recurse
            flatten_dict(value, flattened)
        elif isinstance(value, (set, list, tuple)):  # If the value is a set, list, or tuple, unpack it
            flattened.extend(value)
        else:  # Otherwise, just append the value
            flattened.append(value)
    
    return flattened


def map_hierarchical_items(gold_items, flat_predicted_items_dict, model, threshold, mapping_strategy):
    """
    Map hierarchical items like user intents or system actions by recursively checking all levels.

    Args:
    gold_items: dict
        Gold items dictionary.
    flat_predicted_items_dict: dict
        Predicted items dictionary flattened, i.e. all mapped to top-level keys and then flattened from the second level.
    model: SentenceTransformer
        Sentence transformer model.
    threshold: float
        Threshold for semantic similarity.
    mapping_strategy: str
        Mapping strategy: 'map highest', 'map all' or 'exact match'.

    """
    logging.info("Mapping hierarchical items.")
    predicted_items = flatten_dict(flat_predicted_items_dict)

    return compute_semantic_similarity(gold_items, predicted_items, threshold, mapping_strategy, model)

def map_ontology(gold_ontology, 
                 predicted_ontology, 
                 threshold=0.7, 
                 mapping_strategy="map highest", 
                 model_name='all-MiniLM-L6-v2') -> tuple[dict, dict]:
    """
    Map the predicted ontology to the gold ontology based on semantic similarity.

    Args:
    gold_ontology: dict
        Gold ontology dictionary.
    predicted_ontology: dict
        Predicted ontology dictionary.
    threshold: float
        Threshold for semantic similarity.
    mapping_strategy: str
        Mapping strategy: 'map highest', 'map all' or 'exact match'.
    model_name: str
        Sentence transformer model name.

    Returns:
    tuple[dict, dict]: Mapped ontology and predicted concepts by class.
    """
    logging.info(f"Starting ontology mapping with threshold {threshold} and strategy '{mapping_strategy}'.")
    model = SentenceTransformer(model_name)
    logging.info(f"Using model: {model_name}")

    # Gold ontology keys
    gold_domain_keys = list(gold_ontology['domains'].keys())
    gold_intent_keys = ["user intents"]
    gold_action_keys = ["system actions"]
    all_toplevel_gold_keys = gold_domain_keys + gold_intent_keys + gold_action_keys


    #remove the key ids from all the predicted items in the second level of the hierarchy, as they do not need to be evaluated
    for key, value in predicted_ontology.items():
        if "id" in value:
            del value["id"]

    # Predicted ontology keys
    predicted_top_keys = list(predicted_ontology.keys())

    # Map predicted top-level keys to gold ontology keys
    logging.info("Mapping top-level keys.")
    key_mapping, non_mapped_groundtruth, non_mapped_predictions = map_top_level_keys(
        all_toplevel_gold_keys, 
        predicted_top_keys,
        model, threshold, mapping_strategy,
        gold_intent_keys, gold_action_keys,
    )
    logging.info(f"Top-level key mapping completed: {key_mapping}")

    # Separate predicted ontology components
    predicted_domains = {}
    predicted_intents = {}
    predicted_actions = {}

    for gold_key, predicted_mapped_keys in key_mapping.items():
        if gold_key in gold_domain_keys:
            for key in predicted_mapped_keys:
                 predicted_domains[key] = predicted_ontology[key]
        elif gold_key in gold_intent_keys:
            for key in predicted_mapped_keys:
                 predicted_intents[key] = predicted_ontology[key]
        elif gold_key in gold_action_keys:
            for key in predicted_mapped_keys:
                predicted_actions[key] =  predicted_ontology[key]   

    non_mapped_domains = {}
    non_mapped_intents = {}
    non_mapped_actions = {}

    if non_mapped_predictions:
        for domain_pred in non_mapped_predictions["domains"]:
            non_mapped_domains[domain_pred] = predicted_ontology[domain_pred]
        for intent_pred in non_mapped_predictions["user intents"]:
            non_mapped_intents[intent_pred] = predicted_ontology[intent_pred]
        for action_pred in non_mapped_predictions["system actions"]:
            non_mapped_actions[action_pred] = predicted_ontology[action_pred]


    # Prepare mapping result
    mapping_result = {
        'domains': {},
        'slots': {},
        'values': {},
        'user intents': {},
        'system actions': {}
    }


    # Map domains
    logging.info("Mapping domains.")
    mapping_result['domains'], _, _ = compute_semantic_similarity(
        list(gold_ontology['domains'].keys()),
        list(predicted_domains.keys()),
        threshold, mapping_strategy, model
    )
    logging.info("Domain mapping completed.")

    # Map slots
    logging.info("Mapping slots.")
    #only map the slots from domains that were mapped to a predicted domain and compare them, e.g. so that a slot is only correct if it was part of the correct domain
    #get the set of slots for each gold domain
    gold_slots = {domain: set(slot for slot in slots.keys()) for domain, slots in gold_ontology['domains'].items()}
    #get the set of slots for each predicted domain
    predicted_slots = {domain: set(slot for slot in slots.keys()) for domain, slots in predicted_domains.items()}
    #now for each gold domain, get the assigned predicted domain and compare the slots, if there are several predicted domains, then join the slots from all and compare
    mapping_results_per_domain = {}
    non_mapped_slots = set()
    for gold_domain, gold_slots_set in gold_slots.items():
        assigned_predicted_domains = mapping_result['domains'][gold_domain]
        predicted_slots_set = set()
        for predicted_domain in assigned_predicted_domains:
            predicted_slots_set.update(predicted_slots[predicted_domain])
        #now compare the slots
        mapping_results_per_domain[gold_domain], _, non_mapped_slots_domain = compute_semantic_similarity(
            list(gold_slots_set), list(predicted_slots_set), threshold, mapping_strategy, model
        )
        non_mapped_slots.update(non_mapped_slots_domain)
    
    #now put together the mappings for each domain to get a dict with gold slots as keys and all the predicted assigned slots as values
    mapping_result_for_slots = {}
    for gold_domain, slot_mapping in mapping_results_per_domain.items():
        for gold_slot, predicted_slots in slot_mapping.items():
            if gold_slot not in mapping_result_for_slots:
                mapping_result_for_slots[gold_slot] = set()
            mapping_result_for_slots[gold_slot].update(predicted_slots)
    
    mapping_result['slots'] = mapping_result_for_slots

    logging.info("Slot mapping completed.")

    # Map values
    logging.info("Mapping values.")
    #only map the values from the slots that were mapped to the groundtruth slot and compare them, e.g. so that a value is only correct if it was part of the correct slot
    #get the set of values for each gold slot
    gold_values = {}
    for domain, slots in gold_ontology['domains'].items():
        for slot, values in slots.items():
            if slot not in gold_values:
                gold_values[slot] = set()
            gold_values[slot].update(values)
    #get the set of values for each predicted slot
    predicted_values = {}
    for domain, slots in predicted_domains.items():
        for slot, values in slots.items():
            if slot not in predicted_values:
                predicted_values[slot] = set()
            predicted_values[slot].update(values)

    #now for each gold slot, get the assigned predicted slot and compare the values, if there are several predicted slots, then join the values from all and compare
    mapping_results_per_slot = {}
    non_mapped_values = set()
    for gold_slot, gold_values_set in gold_values.items():
        assigned_predicted_slots = mapping_result['slots'][gold_slot]
        predicted_values_set = set()
        for predicted_slot in assigned_predicted_slots:
            predicted_values_set.update(predicted_values[predicted_slot])
        #now compare the values
        mapping_results_per_slot[gold_slot], _, non_mapped_values_slot = compute_semantic_similarity(
            list(gold_values_set), list(predicted_values_set), threshold, mapping_strategy, model
        )
        non_mapped_values.update(non_mapped_values_slot)

    #now put together the mappings for each slot to get a dict with gold values as keys and all the predicted assigned values as values
    mapping_result_for_values = {}
    for gold_slot, value_mapping in mapping_results_per_slot.items():
        for gold_value, predicted_values in value_mapping.items():
            if gold_value not in mapping_result_for_values:
                mapping_result_for_values[gold_value] = set()
            mapping_result_for_values[gold_value].update(predicted_values)

    mapping_result['values'] = mapping_result_for_values

    logging.info("Value mapping completed.")

    # Map user intents
    #flatten the dict to get all items
    flat_predicted_intents = {k: flatten_dict(v) for k, v in predicted_intents.items()}
    logging.info("Mapping user intents.")
    mapping_result['user intents'], _, _ = map_hierarchical_items(
        list(gold_ontology['user intents']),
        flat_predicted_intents,
        model, threshold, mapping_strategy
    )
    logging.info("User intent mapping completed.")

    # Map system actions
    flat_predicted_actions = {k: flatten_dict(v) for k, v in predicted_actions.items()}
    logging.info("Mapping system actions.")
    mapping_result['system actions'], _, _ = map_hierarchical_items(
        list(gold_ontology['system actions']),
        flat_predicted_actions,
        model, threshold, mapping_strategy
    )
    logging.info("System action mapping completed.")

    logging.info("Ontology mapping completed.")

    logging.info("Get the predictions for each class for false positive computation.")

    #for the user intents and actions matched get the hierarchy level from which they are from in the intent predictions
    predicted_intents_from_relevant_hierarchy_levels = set()
    #track from which mapped user intents dict there were values mapped. If there are no values mapped for a user intent dict then add the lowest level of hierarchy for this dict to the predictions
    user_intent_dicts_with_mapped_values = set()
    for key, value in mapping_result['user intents'].items():
        if value:
            for val in value:
                for k, v in predicted_intents.items():
                    values_to_add = set()
                    if val in flat_predicted_intents[k]:
                        user_intent_dicts_with_mapped_values.add(k)
                        values_to_add = find_hierarchy_level(v, val)
                        #turn everything that are not strings to strings, since we only need the number to compute false positives
                        values_to_add = [str(x) for x in values_to_add]
                    
                    predicted_intents_from_relevant_hierarchy_levels.update(values_to_add)

    #if there are user intent dicts with no values mapped, add the lowest level of hierarchy for this dict to the predictions
    for k, v in predicted_intents.items():
        if k not in user_intent_dicts_with_mapped_values:
            values_to_add = find_hierarchy_level(v)
            values_to_add = [str(x) for x in values_to_add]
            predicted_intents_from_relevant_hierarchy_levels.update(values_to_add)

    #add the non mapped user intents to the predictions
    for k, v in non_mapped_intents.items():
        values_to_add = find_hierarchy_level(v)
        values_to_add = [str(x) for x in values_to_add]
        predicted_intents_from_relevant_hierarchy_levels.update(values_to_add)

    predicted_actions_from_relevant_hierarchy_levels = set()
    #track from which mapped system actions dict there were values mapped. If there are no values mapped for a system action dict then add the lowest level of hierarchy for this dict to the predictions
    system_action_dicts_with_mapped_values = set()
    for key, value in mapping_result['system actions'].items():
        if value:
            for val in value:
                for k, v in predicted_actions.items():
                    values_to_add = set()
                    if val in flat_predicted_actions[k]:
                        system_action_dicts_with_mapped_values.add(k)
                        values_to_add = find_hierarchy_level(v, val)
                        #turn everything that are not strings to strings, since we only need the number to compute false positives
                        values_to_add = [str(x) for x in values_to_add]
                    
                    predicted_actions_from_relevant_hierarchy_levels.update(values_to_add)

    #if there are system action dicts with no values mapped, add the lowest level of hierarchy for this dict to the predictions
    for k, v in predicted_actions.items():
        if k not in system_action_dicts_with_mapped_values:
            values_to_add = find_hierarchy_level(v)
            values_to_add = [str(x) for x in values_to_add]
            predicted_actions_from_relevant_hierarchy_levels.update(values_to_add)

    #add the non mapped system actions to the predictions
    for k, v in non_mapped_actions.items():
        values_to_add = find_hierarchy_level(v)
        values_to_add = [str(x) for x in values_to_add]
        predicted_actions_from_relevant_hierarchy_levels.update(values_to_add)


    #add the predictions that were not mapped
    all_predicted_domains = set(list(predicted_domains.keys()) + list(non_mapped_domains.keys()))
    non_mapped_slots.update(set([slot for domain in non_mapped_domains.values() for slot in domain.keys()]))
    all_predicted_slots = set(list(predicted_slots) + list(non_mapped_slots))
    non_mapped_values.update(set([value for domain in non_mapped_domains.values() for slot_values in domain.values() for value in slot_values]))
    all_predicted_values = set(list(predicted_values) + list(non_mapped_values))

    predictions_by_class = {
        'domains': all_predicted_domains,
        'slots': all_predicted_slots,
        'values': all_predicted_values,
        'user intents': predicted_intents_from_relevant_hierarchy_levels,
        'system actions': predicted_actions_from_relevant_hierarchy_levels
    }


    return mapping_result, predictions_by_class



def get_synonym_groups_with_defaults(synonym_groups, all_gold_values):
    """
    Add default synonym groups for values without a group.
    """
    synonym_groups_dict = {val: {val} for val in all_gold_values}  # Defaults: each value is its own group
    for group in synonym_groups:
        for value in group:
            synonym_groups_dict[value] = set(group)
    return synonym_groups_dict

def expand_synonym_groups(value_mapping, synonym_groups_dict):
    """
    Expand predicted values to account for synonym groups.
    """
    expanded_mapping = defaultdict(set)
    for gold_value, predictions in value_mapping.items():
        if gold_value in synonym_groups_dict:
            group = synonym_groups_dict[gold_value]
            for synonym in group:
                expanded_mapping[synonym].update(predictions)
        else:
            expanded_mapping[gold_value].update(predictions)
    return expanded_mapping

def calculate_class_metrics(predicted_mappings, predicted_items, synonym_groups_dict=None, map_to_value_groups=False):
    """
    Calculate precision, recall, and F1 score for a specific class.

    Args:
        predicted_mappings (dict): Mapping of predicted items to gold items for a class with each gold item having a list of mappings.
        predicted_ontology (list): List of all predicted items for a class.
        synonym_groups_dict (dict): Dictionary of synonym groups.
        map_to_value_groups (bool): Whether to map predicted values to value groups.

    Returns:
        dict: Precision, recall, and F1 score.
    """
    true_positives = set()
    false_positives = set()
    false_negatives = set()

    # Use synonym groups for values if enabled
    if map_to_value_groups and synonym_groups_dict:
        predicted_mappings = expand_synonym_groups(predicted_mappings, synonym_groups_dict)

    # Count true positives
    for gold_item, predictions in predicted_mappings.items():
        if len(predictions) == 0:  # No predictions mapped
            false_negatives.add(gold_item)
        else:
            true_positives.add(gold_item)

    # Count false positives
    all_mapped = set()
    for predictions in predicted_mappings.values():
        all_mapped.update(predictions)
    false_positives = predicted_items - all_mapped

    precision = (
        len(true_positives) / (len(true_positives) + len(false_positives))
        if len(true_positives) + len(false_positives) > 0
        else 0
    )
    recall = (
        len(true_positives) / (len(true_positives) + len(false_negatives))
        if len(true_positives) + len(false_negatives) > 0
        else 0
    )
    f1 = (
        (2 * precision * recall / (precision + recall))
        if precision + recall > 0
        else 0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def calculate_ontology_metrics(
    mapping_result, all_predictions_per_class, synonym_groups=None, map_to_value_groups=False
):
    """
    Calculate precision, recall, and F1 scores for each class (domains, slots, values, 
    user intents, and system actions) as well as macro and micro averages.

    Args:
        mapping_result (dict): Mapping result from map_ontology.
        all_predictions_per_class (dict): All predicted items for each class.
        synonym_groups (list): List of synonym value group sets.
        map_to_value_groups (bool): Whether to map predicted values to value groups with equivalent synonyms.

    Returns:
        dict: Metrics for each class and macro and micro averages.
        
    """
    metrics = {}
    all_true_positives = 0
    all_false_positives = 0
    all_false_negatives = 0


    # Extract synonym value groups if present and process gold values
    gold_values = list(mapping_result["values"].keys())
    synonym_groups_dict = get_synonym_groups_with_defaults(synonym_groups, gold_values) if map_to_value_groups else None

    for class_name in ["domains", "slots", "values", "user intents", "system actions"]:
        logging.info(f"Calculating metrics for {class_name}.")
        metrics[class_name] = calculate_class_metrics(
            mapping_result[class_name],
            all_predictions_per_class[class_name],
            synonym_groups_dict if class_name == "values" else None,
            map_to_value_groups,
        )

        # Accumulate for micro averages
        all_true_positives += len(metrics[class_name]["true_positives"])
        all_false_positives += len(metrics[class_name]["false_positives"])
        all_false_negatives += len(metrics[class_name]["false_negatives"])

    # Calculate macro averages
    macro_precision = sum(
        metrics[class_name]["precision"] for class_name in metrics
    ) / len(metrics)
    macro_recall = sum(metrics[class_name]["recall"] for class_name in metrics) / len(
        metrics
    )
    macro_f1 = sum(metrics[class_name]["f1"] for class_name in metrics) / len(metrics)

    # Calculate micro averages
    micro_precision = (
        all_true_positives / (all_true_positives + all_false_positives)
        if all_true_positives + all_false_positives > 0
        else 0
    )
    micro_recall = (
        all_true_positives / (all_true_positives + all_false_negatives)
        if all_true_positives + all_false_negatives > 0
        else 0
    )
    micro_f1 = (
        (2 * micro_precision * micro_recall / (micro_precision + micro_recall))
        if micro_precision + micro_recall > 0
        else 0
    )

    # Add macro and micro averages to the result
    metrics["macro"] = {"precision": macro_precision, "recall": macro_recall, "f1": macro_f1}
    metrics["micro"] = {"precision": micro_precision, "recall": micro_recall, "f1": micro_f1}


    #also get the macro average over domains/slots/values and user intents and system actions separately
    hierarchy_classes = ["domains", "slots", "values"]
    # Calculate macro averages
    macro_precision = sum(
        metrics[class_name]["precision"] for class_name in hierarchy_classes
    ) / len(hierarchy_classes)
    macro_recall = sum(metrics[class_name]["recall"] for class_name in hierarchy_classes) / len(
        hierarchy_classes
    )
    macro_f1 = sum(metrics[class_name]["f1"] for class_name in hierarchy_classes) / len(hierarchy_classes)

    metrics["domain slot value macro"] = {"precision": macro_precision, "recall": macro_recall, "f1": macro_f1}

    action_intent = ["user intents", "system actions"]
    # Calculate macro averages
    macro_precision = sum(
        metrics[class_name]["precision"] for class_name in action_intent
    ) / len(action_intent)
    macro_recall = sum(metrics[class_name]["recall"] for class_name in action_intent) / len(
        action_intent
    )
    macro_f1 = sum(metrics[class_name]["f1"] for class_name in action_intent) / len(action_intent)

    metrics["intent action macro"] = {"precision": macro_precision, "recall": macro_recall, "f1": macro_f1}

    return metrics
