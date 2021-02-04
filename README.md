# Whittler

## About

This utility is designed to consume large datasets of results of some sort, and let you qualitatively or quantitatively rule out certain results as irrelevant. It splits the data into intuitive categories and lets you interact with the dataset, marking results as relevant or irrelevant as desired. It also has the capability to use a combination of string-similarity algorithms to make "fuzzy groups" of elements that are similar in some way or another, and mark those as relevant or irrelevant.

Whittler was designed to deal with the output of security tools that return thousands of results, many of which are false-positives. However, it could be used to categorize and explore any type of dataset. Whittler uses modules to import the data in a given dataset, and making modules is easy, only requiring basic Python knowledge (see the "Making new modules" section below).

## Quickstart

```
(base) PS C:\Users\v-bei\Desktop\Whittler> python.exe .\Whittler.py --help
usage: Whittler.py [-h] [--config {bandit,pssa_csv,sarif,trufflehog}] [--file FILE]
                   [--dir DIR] [--log_output [LOG_OUTPUT]]
                   [--log_command_history [LOG_COMMAND_HISTORY]]
                   [--import_whittler_output IMPORT_WHITTLER_OUTPUT]

An interactive script to whittle down false-positive trufflehog findings

optional arguments:
  -h, --help            show this help message and exit
  --config {bandit,pssa_csv,sarif,trufflehog}
                        the module to use to parse the specified tool output files.
  --file FILE           the tool output file to be parsed
  --dir DIR             the directory containing tool output files to be parsed
  --log_output [LOG_OUTPUT]
                        a file to which all output in this session will be logged
                        (default: a new file in the .whittler folder in your home
                        directory)
  --log_command_history [LOG_COMMAND_HISTORY]
                        a file in which to record the command history of this session
                        (default: a new file in the .whittler folder in your home
                        directory)
  --import_whittler_output IMPORT_WHITTLER_OUTPUT
                        consume and continue working with a file that was outputted by
                        Whittler's "export" command"
(base) PS C:\Scripts\Whittler> python .\Whittler.py --config trufflehog --file "C:\trufflehog_output.json" --log_command_history "C:\whittler_commands.txt" --log_output "C:\whittler_output.txt"

Welcome to the Whittler shell. Type "help" for a list of commands.

Parsing provided files...

Done.

Whittler > help

navigation:
|   show [[limit]]     :  Show the current data context, up to [limit] entries (shows all entries by
|                         default). Mutes results or table entries with 0 relevant results.
|   showall [[limit]]  :  Show the current data context, up to [limit] entries (shows all entries by
|                         default). Includes results or table entries with 0 relevant results.
|   dig [attr]         :  Dig into a specific data grouping category, either by attribute name, or
|                         by attribute id
|   up                 :  Dig up a level into the broader data grouping category
|   top                :  Dig up to the top level
|   dump [[limit]]     :  Display every relevant result in every category, up to [limit] entries
|                         (shows all by default)
|   dumpall [[limit]]  :  Display every result, both relevant and irrelevant, in every category, up
|                         to [limit] entries (shows all by default)
|   exit               :  Gracefully exit the program

data model interaction:
|   irrelevant [[id]]      :  Mark all elements in the current context, or those referenced by [id],
|                             as irrelevant results
|   relevant [[id]]        :  Mark all elements in the current context, or those referenced by [id],
|                             as relevant results
|   group [id] [[attr]]    :  Using data science, group all results in the database by similarity to
|                             the attribute referenced by [id]. Or, if [id] points to a specific
|                             result, group by similarity to a specific attribute of the result
|                             referenced by [id].
|   game [[id]]            :  Play a game where individual results are presented one-by-one, and the
|                             user is asked whether the result is relevant or not and why. Using
|                             this information, other similar results are also eliminated in bulk.
|                             If [id] is specified, then the results presented are limited to the
|                             result group represented by the specified [id].
|   filter [str] [[attr]]  :  Mark all results containing [str] in a particular attribute as
|                             irrelevant (case-insensitive)

output:
|   quiet [[attr]]         :  Suppress an attribute from being displayed when printing out raw
|                             result data
|   unquiet [[attr]]       :  Undo the suppression from an earlier quiet command
|   solo [[attr]]          :  Print only a single attribute's value when printing out raw result
|                             data
|   SOLO [[attr]]          :  Print ONLY a single attribute's value when printing out raw result
|                             data, with no context IDs or attribute value names
|   unsolo                 :  Disable solo mode. Note that this retains any attributes suppressed
|                             using the "quiet" command.
|   sort [colname]         :  Sorts the displayed results by column name. Use quotes if the column
|                             name has a space in it.
|   history                :  Print all commands that have been run in this session so far
|   export [fname] [[id]]  :  Export all relevant results in JSON form at into the file [fname].
|                             Optionally, limit the output to the result set as referenced by [id].

NOTE: This shell supports quoted arguments and redirecting command output to a file using the ">" operator.

Whittler > 
```

## Prerequisites

This shell has been tested on Python >= 3.6 .

Whittler will work fine with only standard libraries. The only nonstandard library used in this project is [pyxDamerauLevenshtein](https://github.com/gfairchild/pyxDamerauLevenshtein), which is used to improve its ability to predict fuzzy groups of results for bulk categorization. It can be installed via the following command:

```
pip install pyxDamerauLevenshtein
```

Or, alternatively:

```
python -m pip install pyxDamerauLevenshtein
```

## Installation

This *should* be a foolproof way to get this project working on Windows:

1. [Install Anaconda with Python 3.x](https://www.anaconda.com/products/individual)
2. Open the Anaconda Command Prompt (search for it in the start menu, start as Administrator to be safe)
3. Ensure that we're using Python 3: `python --version`
4. `python -m pip install pyxDamerauLevenshtein` (optional, but helps with data mining functionality)
5. Navigate to the root directory of this repo (the one with Whittler.py)
6. `python .\Whittler.py --help`

## Output

By default, Whittler will just output to the console. However, if the `--log_command_history` or `--log_output` flags are specified, Whittler will output the full transcript of your session and/or a full list of the commands you ran into a .whittler folder that is created in your user profile's home directory. (Both of these parameters can optionally take filenames that will be used for output instead of the default files in the .whittler folder.) To recreate an entire Whittler session (given the same input file corpus), the command history can simply be copy-pasted into the Whittler shell - all the data structures used by Whittler are ordered and sorted to enable recreating sessions accurately.

## Game mode

Whittler features a "game mode" that can be entered using the "game" command. In this mode, the results in Whittler's database will be displayed one-by-one, and Whittler will ask whether the result is relevant to you or not. Based on your response, it will gather information on exactly why the result was irrelevant, and optionally use data science algorithms to deduce other results that you may also find similar to the current result. It will show you results you haven't categorized as relevant/irrelevant until you've worked through the entire database, or decide to exit the game. In my experience, this tends to be the quickest way to whittle through huge datasets :)

## Making new modules

Whittler can ingest literally any data source. Just copy modules/_sample_module.py to a new file in the modules/ directory and work from there. The sample module has documentation to help you craft your new data ingestion module. (Just make sure that your new module's filename does not start with an underscore - module filenames starting with underscores are ignored.)