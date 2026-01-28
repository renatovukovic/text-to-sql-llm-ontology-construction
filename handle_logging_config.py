# coding=utf-8
#
# Copyright 2023
# Heinrich Heine University Dusseldorf,
# Faculty of Mathematics and Natural Sciences,
# Computer Science Department
#
# Authors:
# Benjamin Ruppik (ruppik@hhu.de)
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
# START Imports

# System imports
from datetime import datetime
import logging
import os
import pathlib
import sys

# Third-party imports
from git import Repo

# END Imports
# # # # # # # # # # # # # # # # # # # # # # # # # # # # #

#logging info in file logger.info(f"temp_desc:\n" f"{temp_desc}")
#call this file before


def get_git_info() -> str:
    """Get the git info of the current branch and commit hash"""
    repo = Repo(
        os.path.dirname(os.path.realpath(__file__)),
        search_parent_directories=True,
    )
    branch_name = repo.active_branch.name
    commit_hex = repo.head.object.hexsha

    info = f"{branch_name}/{commit_hex}"
    return info



def setup_logging(
    script_name: str,
) -> logging.Logger:
    """
    Sets up logging for a script.
    This will log to a file in the 'logs' directory and to stdout.

    Args:
        script_name (str):
            Name of the script to create a log file for.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Format the current date and time as a string
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Define log file path
    logfile_path = pathlib.Path(
        "logs",
        f"{script_name}_{timestamp}.log",
    )

    # Create log directory if it does not exist
    logfile_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Basic configuration for logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(logfile_path),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # Get logger
    logger = logging.getLogger(script_name)
    logger.info(
        f"Logger initialized for file logfile_path:\n" f"{logfile_path}\nand stdout"
    )

    # Log git info
    #logger.info(f"git_info:\n{get_git_info()}")

    return logger
