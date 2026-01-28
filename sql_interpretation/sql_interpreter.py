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

import sqlite3
import sqlglot
import re
import sentence_transformers
from sentence_transformers import SentenceTransformer
import numpy as np
import random


def extract_sql_from_response(response: str) -> list[str]:
    """
    Extract the SQL queries from the response and remove newlines from them.

    Input:
        response: str: the response from the model that contains SQL queries

    Output:
        list[str]: the SQL queries extracted from the response with no newlines
    """
    # Capture all SQL queries (multi-line enabled)
    sql_queries = re.findall(r"```sql(.*?)```", response, re.DOTALL)

    return sql_queries

def execute_query(database_name: str, query: str) -> str or list:
    """
    Executes one SQL query on a given SQLite database.
    
    Parameters:
        database_name (str): The name of the SQLite database file.
        query (str): The SQL query to execute.
        
    Returns:
        str or list: The result of the query (for SELECT) or a confirmation message (for INSERT/UPDATE).
    """
    try:
        # Connect to the specified SQLite database (creates it if it doesn't exist)
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        
        # Execute the query
        cursor.execute(query)
        
        # Commit if the query modifies data (e.g., INSERT, UPDATE, DELETE)
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
            connection.commit()
            result = "Update completed and saved successfully."
        else:
            # Fetch data if it's a SELECT query
            result = cursor.fetchall()
        
        # Close the connection
        connection.close()
        
        # Return the result
        return result
    
    except sqlite3.Error as e:
        # Catch any SQL errors and return the error message
        return f"An error occurred: {e}"

# Example usage
# database_name = 'employees.db'
# query = "SELECT * FROM employees WHERE salary > 50000;"  # Example query; replace with any SQL command
# result = execute_query(database_name, query)
# print(result)


def execute_queries(database_name: str, queries: str) -> str or list:
    """
    Executes multiple SQL queries in a straing on a given SQLite database with the execute script function from sqlite. Can only return the result of a SELECT query if it was the last query.
    
    Parameters:
        database_name (str): The name of the SQLite database file.
        queries (str): A string containing multiple SQL queries, separated by semicolons.
        
    Returns:
        str or list: The result of the last SELECT query, or a confirmation message for updates. 
                     Returns error message if any query fails.
    """
    try:
        # Connect to the specified SQLite database (creates it if it doesn't exist)
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        
        # Use executescript to run multiple queries in one call
        cursor.executescript(queries)
        
        # If the last query is a SELECT, fetch and return its results
        # We'll split the queries and check if the last one is a SELECT
        last_query = queries.strip().split(';')[-2].strip()  # Get the last SQL query without trailing semicolons
        
        if last_query.upper().startswith("SELECT"):
            cursor.execute(last_query)
            result = cursor.fetchall()
        else:
            # Commit if there were any INSERT, UPDATE, DELETE, etc., statements
            connection.commit()
            result = "Update completed and saved successfully."

        # Close the connection
        connection.close()
        
        # Return the result
        return result
    
    except sqlite3.Error as e:
        # Catch any SQL errors and return the error message
        return f"An error occurred: {e}"

# Example usage
# database_name = 'employees.db'
# queries = """
# CREATE TABLE IF NOT EXISTS employees (
#     id INTEGER PRIMARY KEY,
#     name TEXT,
#     position TEXT,
#     salary REAL
# );
# INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 60000);
# INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Manager', 80000);
# SELECT * FROM employees;
# """

# result = execute_queries(database_name, queries)
# print(result)


def execute_multiple_queries(database_name: str, queries: str):
    """
    Executes multiple SQL queries on a given SQLite database, ignoring comments and 
    correcting escaped single quotes.
    
    Parameters:
        database_name (str): The name of the SQLite database file.
        queries (str): A string containing multiple SQL queries, separated by semicolons.
                       Can contain SQL comments (line and block comments).
        
    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
                        - For successful SELECT queries: (query, result)
                        - For non-SELECT updates: (query, "Update completed")
                        - For errors: (query, error message)
    """
    try:
        # Connect to the specified SQLite database
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        
        # Remove comments and fix single quotes in the SQL string
        def preprocess_sql(sql):
            # Remove block comments (/* ... */)
            sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
            # Remove single-line comments (--) and any whitespace after them
            sql = re.sub(r'--.*', '', sql)
            # Replace escaped single quotes (\') with SQLite-compatible ('' for single quote)
            sql = sql.replace("\\'", "''")
            return sql
        
        # Preprocess the queries string to remove comments and fix single quotes
        queries = preprocess_sql(queries)
        
        # Split the cleaned string into individual SQL statements
        query_list = [query.strip() for query in queries.strip().split(';') if query.strip()]
        
        # Initialize an empty list to store (query, result) for each query
        results = []
        
        # Execute each query individually
        for query in query_list:
            try:
                if query.upper().startswith("SELECT"):
                    # Execute SELECT query and store the (query, result) tuple
                    cursor.execute(query)
                    results.append((query, cursor.fetchall()))
                else:
                    # Execute non-SELECT query, commit changes, and store update confirmation
                    cursor.execute(query)
                    connection.commit()
                    results.append((query, "Update completed"))
            except sqlite3.Error as e:
                # Append the error message if an error occurs with the current query
                results.append((query, f"Error: {e}"))
        
        # Close the connection
        connection.close()
        
        # Return the list of (query, result or error message) tuples
        return results
    
    except sqlite3.Error as e:
        # Catch any SQL errors during connection setup or closure and return the error message
        return f"An error occurred with the database connection: {e}"

# # Example usage
# database_name = 'employees.db'
# queries = """
# -- This is a line comment
# CREATE TABLE IF NOT EXISTS employees (
#     id INTEGER PRIMARY KEY,
#     name TEXT,
#     position TEXT,
#     salary REAL
# );
# /* Insert some test data */
# INSERT INTO employees (name, position, salary) VALUES ('Alice', 'Engineer', 60000);
# INSERT INTO employees (name, position, salary) VALUES ('Bob', 'Manager', 80000);
# INSERT INTO employees (name, position, salary) VALUES ('Saint John''s', 'Teacher', 55000);
# SELECT * FROM employees; -- Select all employees
# """

# result = execute_multiple_queries(database_name, queries)
# for query, output in result:
#     print(f"Query: {query}\nOutput: {output}\n")




def execute_multiple_queries_with_errors(database_name: str, 
                                         queries: str,
                                         use_concept_matching: bool = False,
                                         do_not_execute_update_queries: bool = False) -> list[tuple]:
    """
    Executes multiple SQL queries on a given SQLite database, ignoring comments, 
    correcting escaped single quotes, and attempting to fix common errors.
    
    Parameters:
        database_name (str): The name of the SQLite database file.
        queries (str): A string containing multiple SQL queries, separated by semicolons.
                       Can contain SQL comments (line and block comments).
        use_concept_matching (bool): Whether to use concept matching to find predicted concepts that are not matching exactly but are similar to the concepts in the DB
        do_not_execute_update_queries (bool): Whether to execute non-SELECT queries (e.g., INSERT, UPDATE, DELETE) or just return them as is, since they should only be generated in the last step, in the prior steps they will not be executed, since they are falsely generated, there should only be select and pragma queries in these steps.
        
    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
                        - For successful SELECT queries: (query, result)
                        - For non-SELECT updates: (query, "Update completed")
                        - For errors: (query, error message)
    """
    try:
        # Connect to the specified SQLite database
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        
        # Remove comments and fix single quotes in the SQL string
        def preprocess_sql(sql):
            # Remove block comments (/* ... */)
            sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
            # Remove single-line comments (--) and any whitespace after them
            sql = re.sub(r'--.*', '', sql)
            # Replace escaped single quotes (\') with SQLite-compatible ('' for single quote)
            sql = sql.replace("\\'", "''")
            return sql
        
        # Preprocess the queries string to remove comments and fix single quotes
        queries = preprocess_sql(queries)
        
        # Split the cleaned string into individual SQL statements
        query_list = [query.strip() for query in queries.strip().split(';') if query.strip()]
        
        # Initialize an empty list to store (query, result) for each query
        results = []
        
        # Execute each query individually
        for query in query_list:
            try:
                if query.upper().startswith("SELECT") or query.upper().startswith("PRAGMA"):
                    # Execute SELECT query and store the (query, result) tuple
                    cursor.execute(query)
                    query_result = cursor.fetchall()
                    results.append((query, query_result))
                else:
                    # Execute non-SELECT query, commit changes, and store update confirmation
                    cursor.execute(query)
                    if do_not_execute_update_queries:
                        results.append((query, "Update query not executed yet."))
                    else:
                        connection.commit()
                        results.append((query, "Update completed"))
            except sqlite3.Error as e:
                # Handle common errors and attempt to fix the query
                fixed_query = handle_sqlite_errors(query, e)
                
                if fixed_query != query:
                    # If the query was modified, re-execute the fixed query
                    try:
                        cursor.execute(fixed_query)
                        if do_not_execute_update_queries:
                            results.append((query, "fixed Update query not executed yet."))
                        else:
                            connection.commit()
                            results.append((query, "Update completed with fixed query above"))
                    except sqlite3.Error as fixed_error:
                        results.append((fixed_query, f"Error after fixing: {fixed_error}"))
                else:
                    results.append((query, f"Error: {e}"))
        
        # Close the connection
        connection.close()
        
        # Return the list of (query, result or error message) tuples
        return results
    
    except sqlite3.Error as e:
        # Catch any SQL errors during connection setup or closure and return the error message
        return f"An error occurred with the database connection: {e}"

def handle_sqlite_errors(query, error):
    """
    Attempts to fix common SQLite errors in the query by removing the problematic part.
    It only executes the part of the query before the error.

    Parameters:
        query (str): The SQL query that caused the error.
        error (sqlite3.Error): The error object raised during the query execution.

    Returns:
        str: The fixed query (if applicable) or the original query if no fix is applied.
    """
    # Example: If the query contains 'ON DUPLICATE KEY UPDATE', remove that part
    if "ON DUPLICATE KEY UPDATE" in query:
        # Strip everything after 'ON DUPLICATE KEY UPDATE'
        fixed_query = query.split("ON DUPLICATE KEY UPDATE")[0]
        return fixed_query
    
    # Example: If ON CONFLICT is used improperly, remove that part
    if "ON CONFLICT" in query:
        # Strip everything after 'ON CONFLICT'
        fixed_query = query.split("ON CONFLICT")[0]
        return fixed_query
    
    if "AUTO_INCREMENT" in query: #remove it as it is not supported in SQLite
        fixed_query = query.replace("AUTO_INCREMENT", "")
        return fixed_query
    
    # Add more error handling cases as needed

    # If no fix is applied, return the original query
    return query


def get_entire_database_structure(database_name: str) -> dict:
    """
    Fetches the structure of the entire SQLite database as a dictionary, where:
    - Each table is a top-level key.
    - Each column within a table is a second-level key.
    - The values are sets containing all unique non-None values for each column.
    - Columns with None values will exist but will be empty if all values are None.

    Parameters:
        database_name (str): The SQLite database file name.

    Returns:
        dict: A dictionary representing the structure of the entire database.
    """

    # Initialize the dictionary to store the entire database structure
    database_structure = {}
    
    # Connect to the SQLite database
    connection = sqlite3.connect(database_name)
    cursor = connection.cursor()

    # Get all table names in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    

    for table in tables:
        table_name = table[0].lower()
        # Initialize a dictionary for each table
        database_structure[table_name] = {}

        # Get all column names for the current table
        try:
            cursor.execute(f'PRAGMA table_info("{table_name}");')
            columns = cursor.fetchall()
        except sqlite3.Error as e:
            # Handle any errors that occur during the database operations
            print(f'Error accessing the database: {e}\nQuery was PRAGMA table_info("{table_name}");')
            continue
        
        # For each column, initialize a set to store its unique non-None values
        for column in columns:
            column_name = column[1].lower()
            database_structure[table_name][column_name] = set()

        # Now fetch all rows for the current table
        try:
            cursor.execute(f'SELECT * FROM "{table_name}";')
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            # Handle any errors that occur during the database operations
            print(f'Error accessing the database: {e}\nQuery was SELECT * FROM "{table_name}";')
            continue

        # Populate the sets with unique non-None values from the rows
        for row in rows:
            for idx, value in enumerate(row):
                column_name = columns[idx][1].lower()
                if value is not None:  # Exclude None values
                    value = str(value)
                    value = value.lower()
                    database_structure[table_name][column_name].add(value)

        # Ensure that columns with only None values are empty sets
        for column in columns:
            column_name = column[1].lower()
            if not database_structure[table_name][column_name]:
                # Leave the column as an empty set if it contains no non-None values
                database_structure[table_name][column_name] = set()

    # Close the connection
    connection.close()

    return database_structure

    # except sqlite3.Error as e:
    #     # Handle any errors that occur during the database operations
    #     print(f"Error accessing the database: {e}")
    #     connection.close()
    #     return database_structure




###################### functions for extracting table names, column names and values from SQL queries ######################
def extract_table_names(sql_query, dialect="sqlite"):
    """
    Extracts table names from an SQL query using sqlglot, with optional dialect specification.
    Handles PRAGMA, CREATE, INSERT, UPDATE, ALTER, and other common SQL queries.

    Parameters:
        sql_query (str): The SQL query string.
        dialect (str): The SQL dialect to use for parsing (default is "sqlite").

    Returns:
        list: A list of table names found in the query.
    """
    try:
        # First, check for PRAGMA queries and extract the table name from them
        pragma_match = re.match(r"PRAGMA\s+table_info\((\w+)\)", sql_query.strip(), re.IGNORECASE)
        if pragma_match:
            return [pragma_match.group(1)]
        
        # Check for CREATE TABLE queries and extract the table name
        create_match = re.match(r"CREATE\s+TABLE\s+(\w+)", sql_query.strip(), re.IGNORECASE)
        if create_match:
            return [create_match.group(1)]
        
        # Check for INSERT INTO queries and extract the table name
        insert_match = re.match(r"INSERT\s+INTO\s+(\w+)", sql_query.strip(), re.IGNORECASE)
        if insert_match:
            return [insert_match.group(1)]
        
        # Check for UPDATE queries and extract the table name
        update_match = re.match(r"UPDATE\s+(\w+)", sql_query.strip(), re.IGNORECASE)
        if update_match:
            return [update_match.group(1)]
        
        # Check for ALTER TABLE queries and extract the table name
        alter_match = re.match(r"ALTER\s+TABLE\s+(\w+)", sql_query.strip(), re.IGNORECASE)
        if alter_match:
            return [alter_match.group(1)]
        
        # Otherwise, parse the SQL query using sqlglot for general SQL queries
        parsed = sqlglot.parse_one(sql_query, read=dialect)
        
        # Extract the table names from the parsed AST
        table_names = [table.name for table in parsed.find_all(sqlglot.expressions.Table)]
        
        return table_names
    except Exception as e:
        raise(e)


def extract_column_names(sql_query, dialect="sqlite"):
    """
    Extracts column names from an SQL query using sqlglot, with optional dialect specification.
    Handles PRAGMA, CREATE, INSERT, UPDATE, ALTER, SELECT (with WHERE clause), and other common SQL queries.

    Parameters:
        sql_query (str): The SQL query string.
        dialect (str): The SQL dialect to use for parsing (default is "sqlite").

    Returns:
        list: A list of column names found in the query.
    """
    try:
        column_names = []
        
        # Check for PRAGMA table_info query
        pragma_match = re.match(r"PRAGMA\s+table_info\((\w+)\)", sql_query.strip(), re.IGNORECASE)
        if pragma_match:
            # For PRAGMA table_info, return an empty list since no columns are actually mentioned in the query
            return []

        # Check for CREATE TABLE queries and extract column names
        create_match = re.match(r"CREATE\s+TABLE\s+\w+\s*\((.*)\)", sql_query.strip(), re.IGNORECASE)
        if create_match:
            column_definitions = create_match.group(1)
            column_names = [col.strip().split()[0] for col in column_definitions.split(",") if col.strip()]
            return column_names
        
        # Check for INSERT INTO queries and extract column names
        insert_match = re.match(r"INSERT\s+INTO\s+\w+\s*\((.*)\)", sql_query.strip(), re.IGNORECASE)
        if insert_match:
            insert_match_group = insert_match.group(1)
            #only take everything up to the first closing bracket, which highlights the column names
            insert_match_group = insert_match_group.split(")")[0]
            column_names = [col.strip() for col in insert_match_group.split(",")]
            return column_names
        
        # Check for UPDATE queries and extract column names
        update_match = re.match(r"UPDATE\s+\w+\s+SET\s+(.*)", sql_query.strip(), re.IGNORECASE)
        if update_match:
            set_clause = update_match.group(1)
            column_names = [item.split('=')[0].strip() for item in set_clause.split(",")]
            return column_names
        
        # Check for ALTER TABLE queries and extract column names
        alter_match = re.match(r"ALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+(\w+)", sql_query.strip(), re.IGNORECASE)
        if alter_match:
            return [alter_match.group(1)]
        
        # Check for SELECT queries and extract column names (including WHERE clause)
        select_match = re.match(r"SELECT\s+(.*?)\s+FROM", sql_query.strip(), re.IGNORECASE)
        if select_match:
            select_clause = select_match.group(1).strip()
            # If '*' is present, exclude it (we want actual column names)
            if select_clause != "*":
                # Split the columns by commas, ignoring functions or aliases
                columns = [col.split()[0] for col in select_clause.split(",") if col.strip() != "*"]
                return columns
        
        # Otherwise, parse the SQL query using sqlglot for general SQL queries
        parsed = sqlglot.parse_one(sql_query, read=dialect)
        
        # Extract column names from the parsed AST (if available)
        columns = parsed.find_all(sqlglot.expressions.Column)
        column_names = [column.name for column in columns]
        
        return column_names
    
    except Exception as e:
        raise(e)



def extract_column_value_mapping(sql_query, dialect="sqlite"):
    """
    Extracts values mentioned in an SQL query and maps them to corresponding column names.
    Handles PRAGMA, CREATE, INSERT, UPDATE, ALTER, SELECT, and other common SQL queries.

    Parameters:
        sql_query (str): The SQL query string.
        dialect (str): The SQL dialect to use for parsing (default is "sqlite").

    Returns:
        dict: A dictionary mapping column names to the corresponding values.
    """
    try:
        column_value_mapping = {}

        # Check for PRAGMA table_info query (no column values here)
        pragma_match = re.match(r"PRAGMA\s+table_info\((\w+)\)", sql_query.strip(), re.IGNORECASE)
        if pragma_match:
            return column_value_mapping  # No values to extract from PRAGMA

        # Check for CREATE TABLE queries (no values in the CREATE statement)
        create_match = re.match(r"CREATE\s+TABLE\s+\w+\s*\((.*)\)", sql_query.strip(), re.IGNORECASE)
        if create_match:
            return column_value_mapping  # CREATE TABLE does not have values

        # Check for INSERT INTO queries and extract values
        insert_match = re.match(r"INSERT\s+INTO\s+\w+\s*\((.*)\)\s+VALUES\s*\((.*)\)", sql_query.strip(), re.IGNORECASE)
        if insert_match:
            columns = [col.strip() for col in insert_match.group(1).split(",")]
            values = [val.strip().replace("'", "") for val in insert_match.group(2).split(",")]
            # Map columns to their corresponding values
            column_value_mapping = dict(zip(columns, values))
            return column_value_mapping

        # Check for UPDATE queries and extract values
        update_match = re.match(r"UPDATE\s+\w+\s+SET\s+(.*)", sql_query.strip(), re.IGNORECASE)
        if update_match:
            set_clause = update_match.group(1)
            # Extract column-value pairs from SET clause
            set_pairs = [item.split('=') for item in set_clause.split(",")]
            for pair in set_pairs:
                if len(pair) == 2:
                    column_value_mapping[pair[0].strip()] = pair[1].strip().replace("'", "")
        
        # Extract WHERE clause values for UPDATE, SELECT queries
        where_match = re.search(r"WHERE\s+(.*)", sql_query.strip(), re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1)
            # Split conditions in WHERE clause (supports AND conditions)
            conditions = re.split(r'\s+AND\s+|\s+OR\s+', where_clause, flags=re.IGNORECASE)
            for condition in conditions:
                if '=' in condition:  # Only handle simple column = value for now
                    col, val = condition.split('=', 1)
                    column_value_mapping[col.strip()] = val.strip().replace("'", "")
                elif '>' in condition or '<' in condition:
                    # Handle column > value or column < value
                    operator_match = re.search(r'(.*?)([><]=?|=)(.*)', condition)
                    if operator_match:
                        col = operator_match.group(1).strip()
                        val = operator_match.group(3).strip()
                        column_value_mapping[col] = val.replace("'", "")

        # Check for ALTER TABLE queries (no values in definitions)
        if "ALTER TABLE" in sql_query.upper():
            return column_value_mapping  # No data values expected here

        # Parse using sqlglot for general SQL handling
        parsed = sqlglot.parse_one(sql_query, read=dialect)

        # Extract column names and corresponding values from the parsed AST
        columns = parsed.find_all(sqlglot.expressions.Column)
        literals = parsed.find_all(sqlglot.expressions.Literal)

        # Map each column to its corresponding literal value
        for column, literal in zip(columns, literals):
            if hasattr(literal, 'value'):
                column_value_mapping[column.name] = literal.value.replace("'", "")
            else:
                column_value_mapping[column.name] = str(literal).replace("'", "")  # Fallback to string representation

        return column_value_mapping
    
    except Exception as e:
        raise(e)
        #return f"Error parsing SQL query: {e}"
    


def analyse_sql_query(sql_query, dialect="sqlite"):
    """
    Analyses an SQL query and extracts table names, column names, and column-value mappings.

    Parameters:
        sql_query (str): The SQL query string.
        dialect (str): The SQL dialect to use for parsing (default is "sqlite").

    Returns:
        dict: A dictionary containing table names, column names, and column-value mappings.
    """
    # Check if the input is valid
    if not isinstance(sql_query, str) or not sql_query.strip():
        raise ValueError("The SQL query must be a non-empty string.")
    
    try:
        # Extract table names
        table_names = extract_table_names(sql_query, dialect=dialect)
        
        # Extract column names
        column_names = extract_column_names(sql_query, dialect=dialect)
        
        # Extract column-value mapping
        column_value_mapping = extract_column_value_mapping(sql_query, dialect=dialect)

        # Combine results into a dictionary
        analysis_result = {
            "table_names": table_names,
            "column_names": column_names,
            "column_value_mapping": column_value_mapping
        }
        
        return analysis_result

    except ValueError as ve:
        # Likely caused by invalid or unexpected query input
        raise ValueError(f"ValueError while analyzing SQL query: {ve}")
    
    except sqlglot.errors.ParseError as pe:
        # Handle SQL parsing errors specifically
        raise ValueError(f"ParseError: Unable to parse the SQL query. Details: {pe}")
    
    except Exception as e:
        # Catch-all for unexpected errors (should rarely happen)
        raise RuntimeError(f"Unexpected error occurred: {e}")
    



############ functions for execution with semantic similarity based concept matching #############


def get_updated_query_with_most_similar_table(query: str,
                                              tables: list[str],
                                              table_embeddings: np.ndarray,
                                              connection: sqlite3.Connection,
                                              cursor: sqlite3.Cursor,
                                                embedding_model: SentenceTransformer,
                                                n_tables: int = 1,
                                                threshold: float = None,
                                                do_not_execute_update_queries: bool = False) -> list[tuple[str, str]]:
    
    """
    Get the n_tables most similar table names from the database to the one in the query and execute the query with the updated table name.

    Parameters:
        query (str): The SQL query to be executed.
        tables (list[str]): A list of table names in the database.
        table_embeddings (np.ndarray): An array of embeddings for the table names in the database.
        connection (sqlite3.Connection): A connection object to the SQLite database.
        cursor (sqlite3.Cursor): A cursor object to execute the SQL queries.
        embedding_model (SentenceTransformer): A SentenceTransformer model for embedding queries and database entries for semantic similarity.
        n_tables (int): The number of most similar table names to retrieve from the database.
        threshold (float): The minimum similarity score required to consider a table name as similar to the one in the query.
        do_not_execute_update_queries (bool): A flag to indicate whether to execute the adapted update queries or not, i.e. to enable requerying the LLM with them to make it decide whether to execute them or not

    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
    """
    updated_queries = []
    try:
        analysis_dict = analyse_sql_query(query)
    except Exception as e:
        return updated_queries
    if not tables: #in that case there are no tables in the database yet
        return updated_queries
    if analysis_dict["table_names"]:
        table_in_query = analysis_dict["table_names"][0]
        table_in_query_embedding = embedding_model.encode(table_in_query, show_progress_bar = False)
        #calculate the similarity between the table in the query and the tables in the database
        similarities = sentence_transformers.util.pytorch_cos_sim(table_in_query_embedding, table_embeddings)
        #get the most similar tables
        most_similar_tables = np.argsort(similarities[0])[-n_tables:]
        #turn the indices around to be in descending order
        most_similar_tables = [most_similar_tables[i] for i in range(len(most_similar_tables)-1, -1, -1)]
        for table_index in most_similar_tables:
            if threshold and similarities[0][table_index] < threshold:
                break #if the similarity is below the threshold, break the loop since the following tables will be even less similar
            most_similar_table = tables[table_index]
            if most_similar_table == table_in_query: #if the most similar table is the same as the one in the query, return since the query is correct
                continue
            #adapt the query to the most similar table
            updated_query = query.replace(table_in_query, most_similar_table)
            #execute the adapted query
            try:
                cursor.execute(updated_query)
                if not (updated_query.upper().startswith("SELECT") or updated_query.upper().startswith("PRAGMA")):
                    if do_not_execute_update_queries:
                        updated_query_result = "Update query not executed yet."
                    else:
                        connection.commit()
                        updated_query_result = "Update completed with semantically similar table from the DB."
                else:
                    updated_query_result = cursor.fetchall()
            except sqlite3.Error as e:
                updated_query_result = f"An error occurred with the updated query: {e}"
            #put the adapted query and result in the query_result as a tuple
            query_result = (f"Result for updated query with semantically similar table name '{most_similar_table}' replacing '{table_in_query}': {updated_query}", updated_query_result)
            updated_queries.append(query_result)
        

    return updated_queries


def get_updated_query_with_most_similar_column(query: str,
                                               problem_column: str,
                                               columns: list[str],
                                                  column_embeddings: np.ndarray,
                                                  connection: sqlite3.Connection,
                                                    cursor: sqlite3.Cursor,
                                                    embedding_model: SentenceTransformer,
                                                    n_columns: int = 1,
                                                    threshold: float = None,
                                                    do_not_execute_update_queries: bool = False) -> list[tuple[str, str]]:
    """
    Get the n_columns most similar column names from the database to the one in the query and execute the query with the updated column name.

    Parameters:
        query (str): The SQL query to be executed.
        problem_column (str): The column name in the query that needs to be updated.
        columns (list[str]): A list of column names in the database.
        column_embeddings (np.ndarray): An array of embeddings for the column names in the database.
        connection (sqlite3.Connection): A connection object to the SQLite database.
        cursor (sqlite3.Cursor): A cursor object to execute the SQL queries.
        embedding_model (SentenceTransformer): A SentenceTransformer model for embedding queries and database entries for semantic similarity.
        n_columns (int): The number of most similar column names to retrieve from the database.
        threshold (float): The minimum similarity score required to consider a column name as similar to the one in the query.
        do_not_execute_update_queries (bool): A flag to indicate whether to execute the adapted update queries or not, i.e. to enable requerying the LLM with them to make it decide whether to execute them or not

    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
    """

    updated_queries = []
    if not columns: #in that case there are no columns in the database yet
        return updated_queries
    try:
        analysis_dict = analyse_sql_query(query)
    except Exception as e:
        return updated_queries
    if analysis_dict["column_names"]:
        column_in_query = problem_column
        column_in_query_embedding = embedding_model.encode(column_in_query, show_progress_bar = False)
        #calculate the similarity between the column in the query and the columns in the database
        similarities = sentence_transformers.util.pytorch_cos_sim(column_in_query_embedding, column_embeddings)
        #get the most similar columns
        most_similar_columns = np.argsort(similarities[0])[-n_columns:]
        #turn the around to be descending
        most_similar_columns = [most_similar_columns[i] for i in range(len(most_similar_columns)-1, -1, -1)]
        for column_index in most_similar_columns:
            if threshold and similarities[0][column_index] < threshold:
                break #if the similarity is below the threshold, break the loop since the following columns will be even less similar
            most_similar_column = columns[column_index]
            if most_similar_column == column_in_query:
                continue
            #adapt the query to the most similar column
            updated_query = query.replace(column_in_query, most_similar_column)
            #execute the adapted query
            try:
                cursor.execute(updated_query)
                if not (updated_query.upper().startswith("SELECT") or updated_query.upper().startswith("PRAGMA")):
                    if do_not_execute_update_queries:
                        updated_query_result = "Update query not executed yet."
                    else:
                        connection.commit()
                        updated_query_result = "Update completed with semantically similar column from the DB."
                else:
                    updated_query_result = cursor.fetchall()
            except sqlite3.Error as e:
                updated_query_result = f"An error occurred with the updated query: {e}"
            #put the adapted query and result in the query_result as a tuple
            query_result = (f"Result for updated query with semantically similar column name '{most_similar_column}' replacing '{column_in_query}': {updated_query}", updated_query_result)
            updated_queries.append(query_result)


    return updated_queries


def get_updated_query_with_most_similar_value(query: str,
                                              values: dict[str, list[str]],
                                                value_embeddings: dict[str, np.ndarray],
                                                connection: sqlite3.Connection,
                                                cursor: sqlite3.Cursor,
                                                embedding_model: SentenceTransformer,
                                                n_values: int = 1,
                                                threshold: float = None,
                                                do_not_execute_update_queries: bool = False) -> list[tuple[str, str]]:
    """
    Get the n_values most similar values from the database to those in the query and execute the query with the updated value.

    Parameters:
        query (str): The SQL query to be executed.
        values (dict[str, list[str]]): A dictionary where the keys are column names and the values are lists of values in the database.
        value_embeddings (dict[str, np.ndarray]): A dictionary where the keys are column names and the values are arrays of embeddings for the values in the database.
        connection (sqlite3.Connection): A connection object to the SQLite database.
        cursor (sqlite3.Cursor): A cursor object to execute the SQL queries.
        embedding_model (SentenceTransformer): A SentenceTransformer model for embedding queries and database entries for semantic similarity.
        n_values (int): The number of most similar values to retrieve from the database.
        threshold (float): The minimum similarity score required to consider a value as similar to the one in the query.
        do_not_execute_update_queries (bool): A flag to indicate whether to execute the adapted update queries or not, i.e. to enable requerying the LLM with them to make it decide whether to execute them or not


    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
    """

    updated_queries = []
    try:
        analysis_dict = analyse_sql_query(query)
    except Exception as e:
        return updated_queries
    if not values: #in that case there are no values in the database yet
        return updated_queries
    if analysis_dict["column_value_mapping"]:
        #have a list of updated values for each similarity rank, i.e. n_values
        updated_values = []
        for i in range(n_values):
            updated_values.append([])
        for column, value in analysis_dict["column_value_mapping"].items():
            value_in_query = value
            value_in_query_embedding = embedding_model.encode(value_in_query, show_progress_bar = False)
            if column not in values:
                continue
            if not values[column]: #there are no values in the table for this column yet
                continue
            #calculate the similarity between the value in the query and the values in the database
            similarities = sentence_transformers.util.pytorch_cos_sim(value_in_query_embedding, value_embeddings[column])
            #get the most similar values
            most_similar_values = np.argsort(similarities[0])[-n_values:]
            #turn the order of the values to be descending
            most_similar_values = [most_similar_values[i] for i in range(len(most_similar_values)-1, -1, -1)]
            for i, value_index in enumerate(most_similar_values):
                updated_query = query
                if threshold and similarities[0][value_index] < threshold:
                    break #if the similarity is below the threshold, break the loop since the following values will be even less similar
                most_similar_value = values[column][value_index]
                if most_similar_value == value_in_query:
                    continue #this value does not have to be replaced, as it is present in the DB already
                updated_values[i].append((value_in_query, most_similar_value))
                #adapt the query to the most similar value
                updated_query = updated_query.replace(value_in_query, most_similar_value)
                #execute the adapted query
                if updated_query == query:
                    continue
                try:
                    cursor.execute(updated_query)
                    if not (updated_query.upper().startswith("SELECT") or updated_query.upper().startswith("PRAGMA")):
                        if do_not_execute_update_queries:
                            updated_query_result = "Update query not executed yet."
                        else:
                            connection.commit()
                            updated_query_result = "Update completed with semantically similar value from the DB."
                    else:
                        updated_query_result = cursor.fetchall()
                except sqlite3.Error as e:
                    updated_query_result = f"An error occurred with the updated query: {e}"
                
                #put the adapted query and result in the query_result as a tuple
                query_result = (f"Result for updated query with semantically similar value '{most_similar_value}' replacing '{value_in_query}': {updated_query}", updated_query_result)
                updated_queries.append(query_result)



        #now generate a query where all the values are replaced by the most similar ones and execute it
        for i, updated_values_rank in enumerate(updated_values):
            #if there was only 1 value replaced, that should already be in the list of updated queries
            if len(updated_values_rank) == 1:
                continue
            updated_query = query
            for value_tuple in updated_values_rank:
                updated_query = updated_query.replace(value_tuple[0], value_tuple[1])
            if updated_query == query:
                continue
            try:
                cursor.execute(updated_query)
                if not (updated_query.upper().startswith("SELECT") or updated_query.upper().startswith("PRAGMA")):
                    if do_not_execute_update_queries:
                        updated_query_result = "Update query not executed yet."
                    else:
                        connection.commit()
                        updated_query_result = "Update completed with semantically similar values from the DB."
                else:
                    updated_query_result = cursor.fetchall()
            except sqlite3.Error as e:
                updated_query_result = f"An error occurred with the updated query: {e}"

            #put the adapted query and result in the query_result as a tuple
            value_that_were_replaced = [value_tuple[0] for value_tuple in updated_values_rank]
            values_that_replaced_them = [value_tuple[1] for value_tuple in updated_values_rank]
            query_result = (f"Result for updated query with semantically similar values {values_that_replaced_them} replacing {value_that_were_replaced}: {updated_query}", updated_query_result)
            updated_queries.append(query_result)

        #also flatten all the updated values and just execute the first ones for each word
        updated_values_flat = [value_tuple for updated_values_rank in updated_values for value_tuple in updated_values_rank]
        updated_values_flat = list(set(updated_values_flat))
        if len(updated_values_flat) == 1:
            return updated_queries
        updated_query = query
        for value_tuple in updated_values_flat:
            updated_query = updated_query.replace(value_tuple[0], value_tuple[1])
        if updated_query == query:
            return updated_queries
        try:
            cursor.execute(updated_query)
            if not (updated_query.upper().startswith("SELECT") or updated_query.upper().startswith("PRAGMA")):
                if do_not_execute_update_queries:
                    updated_query_result = "Update query not executed yet."
                else:
                    connection.commit()
                    updated_query_result = "Update completed with semantically similar values from the DB."
            else:
                updated_query_result = cursor.fetchall()

        except sqlite3.Error as e:
            updated_query_result = f"An error occurred with the updated query: {e}"

        #put the adapted query and result in the query_result as a tuple
        values_that_were_replaced = []
        values_that_replaced_them = []
        for value_tuple in updated_values_flat:
            if value_tuple[0] not in values_that_were_replaced:
                values_that_were_replaced.append(value_tuple[0])
                values_that_replaced_them.append(value_tuple[1])

        query_result = (f"Result for updated query with semantically similar values {values_that_replaced_them} replacing {values_that_were_replaced}: {updated_query}", updated_query_result)
        updated_queries.append(query_result)




    return updated_queries

    



def execute_multiple_queries_with_errors_with_concept_matching(database_name: str, 
                                         queries: str, 
                                         embedding_model: SentenceTransformer,
                                         n_similar_entries: int = 5,
                                         similarity_threshold_for_select: float = 0.436,  ##based on Lo et al., 2024 End-to-End Ontology Learning with Large Language Models
                                         similarity_threshold_for_updates: float = 0.8,
                                         do_not_execute_matched_update_queries: bool = False,
                                         do_not_execute_all_update_queries: bool = False,
                                         maximum_values_to_choose_from: int = 100,) -> list[tuple]:
    """
    Executes multiple SQL queries on a given SQLite database, ignoring comments, 
    correcting escaped single quotes, and attempting to fix common errors.
    For creation and insertion queries check whether there are already some similar entries in the database based on semantic similarity. For select queries if they do not yield a result because of an error or no result is found, check whether there are similar entries for tables, columns or values in the database based on semantic similarity. Adapt the query accordingly. If there are too many values, sample the maximum number.
    
    Parameters:
        database_name (str): The name of the SQLite database file.
        queries (str): A string containing multiple SQL queries, separated by semicolons.
                       Can contain SQL comments (line and block comments).
        embedding_model (SentenceTransformer): A SentenceTransformer model for embedding queries and database entries for semantic similarity.
        n_similar_entries (int): The number of most similar entries to retrieve from the database for each query
        similarity_threshold_for_select (float): The minimum similarity score required to consider a value as similar to the one in the query for select queries
        similarity_threshold_for_updates (float): The minimum similarity score required to consider a value as similar to the one in the query for update queries, e.g. insert, alter, update, create table
        the latter should be higher than the former because update queries change the DB
        do_not_execute_matched_update_queries (bool): A flag to indicate whether to execute the adapted update queries or not
        do_not_execute_all_update_queries (bool): A flag to indicate whether to execute the adapted update queries or not, i.e. to enable requerying the LLM with them to make it decide
        maximum_values_to_choose_from (int): maximum number of values to consider in a concept matching step
        
    Returns:
        list of tuples: A list where each tuple contains a query and its result or error message.
                        - For successful SELECT queries: (query, result)
                        - For non-SELECT updates: (query, "Update completed")
                        - For errors: (query, error message)
                        - For queries with similarity updated queries or results: (query, updated query or result), as a test also return the queries with similar entries
    """

    #if no update query is to be executed then set the threshold for update to that of select
    if do_not_execute_all_update_queries or do_not_execute_matched_update_queries:
        similarity_threshold_for_updates = similarity_threshold_for_select


    try:
        # Connect to the specified SQLite database
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        
        # Remove comments and fix single quotes in the SQL string
        def preprocess_sql(sql):
            # Remove block comments (/* ... */)
            sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
            # Remove single-line comments (--) and any whitespace after them
            sql = re.sub(r'--.*', '', sql)
            # Replace escaped single quotes (\') with SQLite-compatible ('' for single quote)
            sql = sql.replace("\\'", "''")
            return sql
        
        # Preprocess the queries string to remove comments and fix single quotes
        queries = preprocess_sql(queries)
        
        # Split the cleaned string into individual SQL statements
        query_list = [query.strip() for query in queries.strip().split(';') if query.strip()]
        
        # Initialize an empty list to store (query, result) for each query
        results = []

        #get the list of tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        tables = [table[0] for table in tables]
        #embed the tables using the embedding model
        
        table_embeddings = embedding_model.encode(tables if len(tables) <= maximum_values_to_choose_from else random.sample(tables, maximum_values_to_choose_from), show_progress_bar = False)
        
        # Execute each query individually
        for query in query_list:
            try:
                if query.upper().startswith("SELECT") or query.upper().startswith("PRAGMA"):
                    # Execute SELECT query and store the (query, result) tuple
                    try:
                        cursor.execute(query)
                        query_result = cursor.fetchall()
                        results.append((query, query_result))
                    except sqlite3.Error as e:
                        query_result = f"An error occurred: {e}"
                        results.append((query, query_result))
                    #check for each query whether for a semantically similar table, column or value there is a result
                    if query.upper().startswith("PRAGMA"): #only for PRAGMA queries since they do not return an error if the table does not exist, but an empty result, for select queries the result is only empty if the value is wrong, for columns and tables the query would return an error
                        query_result = get_updated_query_with_most_similar_table(query, tables, table_embeddings, connection, cursor, embedding_model, n_tables=n_similar_entries, threshold=similarity_threshold_for_select)
                        if query_result:
                            results.extend(query_result)
                    else: #for select queries the mentioned values will have to be checked
                        try:
                            analysis_dict = analyse_sql_query(query)
                        except Exception as e:
                            continue
                        if not analysis_dict["table_names"]:
                            continue
                        table_name = analysis_dict["table_names"][0]
                        column_value_dict = {}
                        for column, value in analysis_dict["column_value_mapping"].items():
                            get_all_values_for_column_query = f"SELECT {column} FROM {table_name};"
                            cursor.execute(get_all_values_for_column_query)
                            values = cursor.fetchall()
                            values = set([value[0] for value in values])
                            #remove none values from values
                            values = set([value for value in values if value is not None])
                            #turn the remaining values to string
                            values = set([str(value) for value in values])
                            column_value_dict[column] = list(values)
                        column_value_embedding_dict = {}
                        for column, values in column_value_dict.items():
                            column_value_embedding_dict[column] = embedding_model.encode(values if len(values) <= maximum_values_to_choose_from else random.sample(values, maximum_values_to_choose_from), show_progress_bar = False)
                        query_result = get_updated_query_with_most_similar_value(query, column_value_dict, column_value_embedding_dict, connection, cursor, embedding_model, n_values=n_similar_entries, threshold=similarity_threshold_for_select)
                        #print(f"query result from empty select query: {query_result}")
                        if query_result:
                            results.extend(query_result)
                            


                #handle CREATE, INSERT, UPDATE, ALTER queries where if there is a similar table name, column name or value then the query should be adapted that should also be executed or only the updated query will be executed
                elif query.upper().startswith("CREATE") or query.upper().startswith("INSERT") or query.upper().startswith("ALTER") or query.upper().startswith("UPDATE"):
                    #execute the query
                    cursor.execute(query)
                    if do_not_execute_all_update_queries:
                        results.append((query, "Update query not executed yet."))
                    else:
                        connection.commit()
                        results.append((query, "Update completed"))


                    #analyse the query and check whether there are similar tables, columns or values in the database already that could be used
                    try:
                        analysis_dict = analyse_sql_query(query)
                    except Exception as e:
                        continue
                    #first check the tables
                    if not analysis_dict["table_names"]:
                        continue
                    table_name = analysis_dict["table_names"][0]
                    query_result = get_updated_query_with_most_similar_table(query, tables, table_embeddings, connection, cursor, embedding_model, n_tables=n_similar_entries, threshold=similarity_threshold_for_updates, do_not_execute_update_queries=do_not_execute_matched_update_queries)
                    if query_result:
                        results.extend(query_result)
                    #now check the columns 
                    columns_in_query = analysis_dict["column_names"]
                    #get the column names from the table mentioned
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    columns = [column[1] for column in columns]
                    #embed the columns using the embedding model
                    column_embeddings = embedding_model.encode(columns if len(columns) <= maximum_values_to_choose_from else random.sample(columns, maximum_values_to_choose_from), show_progress_bar = False)
                    for column in columns_in_query:
                        query_result = get_updated_query_with_most_similar_column(query, column, columns, column_embeddings, connection, cursor, embedding_model, n_columns=n_similar_entries, threshold=similarity_threshold_for_updates, do_not_execute_update_queries=do_not_execute_matched_update_queries)
                        if query_result:
                            results.extend(query_result)
                            query = query_result[0][0].split(":")[1].strip() #update the query with the updated columns so that in the end all columns are updated

                    #now check the values
                    column_value_dict = {}
                    for column, value in analysis_dict["column_value_mapping"].items():
                        get_all_values_for_column_query = f"SELECT {column} FROM {table_name};"
                        cursor.execute(get_all_values_for_column_query)
                        values = cursor.fetchall()
                        values = set([value[0] for value in values])
                        #remove none values from values
                        values = set([value for value in values if value is not None])
                        #turn the remaining values to string
                        values = set([str(value) for value in values])
                        column_value_dict[column] = list(values)
                    column_value_embedding_dict = {}
                    for column, values in column_value_dict.items():
                        if values:
                            column_value_embedding_dict[column] = embedding_model.encode(values if len(values) <= maximum_values_to_choose_from else random.sample(values, maximum_values_to_choose_from), show_progress_bar=False)
                        else: 
                            column_value_embedding_dict[column] = []
                    query_result = get_updated_query_with_most_similar_value(query, column_value_dict, column_value_embedding_dict, connection, cursor, embedding_model, n_values=n_similar_entries, threshold=similarity_threshold_for_updates, do_not_execute_update_queries=do_not_execute_matched_update_queries)
                    if query_result:
                        results.extend(query_result)

                else:
                    # Execute non-SELECT query, commit changes, and store update confirmation
                    cursor.execute(query)
                    if do_not_execute_all_update_queries:
                        results.append((query, "Update query not executed yet."))
                    else:
                        connection.commit()
                        results.append((query, "Update completed"))
            except sqlite3.Error as e:
                
                # Handle common errors and attempt to fix the query
                fixed_query = handle_sqlite_errors(query, e)

                if fixed_query != query:
                    # If the query was modified, re-execute the fixed query
                    try:
                        cursor.execute(fixed_query)
                        if do_not_execute_all_update_queries:
                            results.append((fixed_query, "Update query not executed yet."))
                        else:
                            connection.commit()
                            results.append((fixed_query, "Update completed with fixed query above"))
                    except sqlite3.Error as fixed_error:
                        results.append((fixed_query, f"Error after fixing: {fixed_error}"))
                else:
                    results.append((query, f"Error: {e}"))
                    if "no such table" in str(e):
                        if query.upper().startswith("CREATE") or query.upper().startswith("INSERT") or query.upper().startswith("UPDATE") or query.upper().startswith("ALTER"):
                            query_result = get_updated_query_with_most_similar_table(query, tables, table_embeddings, connection, cursor, embedding_model, n_tables=n_similar_entries, threshold=similarity_threshold_for_updates, do_not_execute_update_queries=do_not_execute_matched_update_queries)
                            results.extend(query_result)
                        else:
                            query_result = get_updated_query_with_most_similar_table(query, tables, table_embeddings, connection, cursor, embedding_model, n_tables=n_similar_entries, threshold=similarity_threshold_for_select)
                            results.extend(query_result)
                            #now for the first fixed query from the results check the values to get results for variations here as well
                            if not query_result:
                                continue
                            fixed_query = query_result[0][0].split(":")[1].strip()
                            try:
                                analysis_dict = analyse_sql_query(fixed_query)
                            except Exception as e:
                                continue
                            if not analysis_dict["table_names"]:
                                continue
                            table_name = analysis_dict["table_names"][0]
                            column_value_dict = {}
                            for column, value in analysis_dict["column_value_mapping"].items():
                                get_all_values_for_column_query = f"SELECT {column} FROM {table_name};"
                                try:
                                    cursor.execute(get_all_values_for_column_query)
                                    values = cursor.fetchall()
                                except sqlite3.Error as e:
                                    continue
                                values = set([value[0] for value in values])
                                #remove none values from values
                                values = set([value for value in values if value is not None])
                                #turn the remaining values to string
                                values = set([str(value) for value in values])
                                column_value_dict[column] = list(values)
                            column_value_embedding_dict = {}
                            for column, values in column_value_dict.items():
                                if values:
                                    column_value_embedding_dict[column] = embedding_model.encode(values if len(values) <= maximum_values_to_choose_from else random.sample(values, maximum_values_to_choose_from), show_progress_bar = False)
                                else:
                                    column_value_embedding_dict[column] = []
                            query_result = get_updated_query_with_most_similar_value(fixed_query, column_value_dict, column_value_embedding_dict, connection, cursor, embedding_model, n_values=n_similar_entries, threshold=similarity_threshold_for_select)
                            if query_result:
                                results.extend(query_result)
                            


                    elif "no such column" in str(e):
                        problem_column = str(e).split(":")[1].strip()
                        #get the column names for the table in the query
                        try:
                            analysis_dict = analyse_sql_query(query)
                        except Exception as e:
                            continue
                        if not analysis_dict["table_names"]:
                            continue
                        table_name = analysis_dict["table_names"][0]
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        columns = [column[1] for column in columns]
                        #embed the columns using the embedding model
                        if columns:
                            column_embeddings = embedding_model.encode(columns if len(columns) <= maximum_values_to_choose_from else random.sample(columns, maximum_values_to_choose_from), show_progress_bar = False)
                        else:
                            column_embeddings = []
                        if query.upper().startswith("CREATE") or query.upper().startswith("INSERT") or query.upper().startswith("UPDATE") or query.upper().startswith("ALTER"):
                            query_result = get_updated_query_with_most_similar_column(query, problem_column, columns, column_embeddings, connection, cursor, embedding_model, n_columns=n_similar_entries, threshold=similarity_threshold_for_updates, do_not_execute_update_queries=do_not_execute_matched_update_queries)
                            results.extend(query_result)
                        else:
                            query_result = get_updated_query_with_most_similar_column(query, problem_column, columns, column_embeddings, connection, cursor, embedding_model, n_columns=n_similar_entries, threshold=similarity_threshold_for_select)
                            results.extend(query_result)
                            #now for the first fixed query from the results check the values to get results for variations here as well
                            if not query_result:
                                continue
                            fixed_query = query_result[0][0].split(":")[1].strip()
                            try:
                                analysis_dict = analyse_sql_query(fixed_query)
                            except Exception as e:
                                continue
                            table_name = analysis_dict["table_names"][0]
                            column_value_dict = {}
                            for column, value in analysis_dict["column_value_mapping"].items():
                                get_all_values_for_column_query = f"SELECT {column} FROM {table_name};"
                                try:
                                    cursor.execute(get_all_values_for_column_query)
                                    values = cursor.fetchall()
                                except sqlite3.Error as e:
                                    continue
                                values = set([value[0] for value in values])
                                #remove none values from values
                                values = set([value for value in values if value is not None])
                                #turn the remaining values to string
                                values = set([str(value) for value in values])
                                column_value_dict[column] = list(values)
                            column_value_embedding_dict = {}
                            for column, values in column_value_dict.items():
                                if values:
                                    column_value_embedding_dict[column] = embedding_model.encode(values if len(values) <= maximum_values_to_choose_from else random.sample(values, maximum_values_to_choose_from), show_progress_bar = False)
                                else:
                                    column_value_embedding_dict[column] = []
                            query_result = get_updated_query_with_most_similar_value(fixed_query, column_value_dict, column_value_embedding_dict, connection, cursor, embedding_model, n_values=n_similar_entries, threshold=similarity_threshold_for_select)
                            if query_result:
                                results.extend(query_result)
        
        # Close the connection
        connection.close()
        
        # Return the list of (query, result or error message) tuples
        return results
    
    except sqlite3.Error as e:
        # Catch any SQL errors during connection setup or closure and return the error message
        connection.close()
        print(f"results so far: {results}")
        return f"An error occurred with the database query: {e}"