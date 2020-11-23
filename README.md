# Whittler

## About

This utility is designed to consume large datasets of results of some sort, and let you qualitatively or quantitatively rule out certain results as irrelevant. In the future I hope to add some sample usage here, but for now, just use the --help command on Whittler.py, and the "help" command in the shell, combined with some trial and error :)

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
4. `python -m pip install pyxDamerauLevenshtein`
5. Navigate to the root directory of this repo (the one with Whittler.py)
6. `python .\Whittler.py --help`

At this point, you should see something like the following:

```
(base) PS C:\Scripts\Whittler> python .\Whittler.py --help
 
usage: Whittler.py [-h] [--config {trufflehog}] [--file FILE] [--dir DIR]
                   [--log_output LOG_OUTPUT]
                   [--log_command_history LOG_COMMAND_HISTORY]
                   [--import_whittler_output IMPORT_WHITTLER_OUTPUT]

An interactive script to whittle down false-positive trufflehog findings

optional arguments:
  -h, --help            show this help message and exit
  --config {trufflehog}
                        the module to use to parse the specified tool output
                        files.
  --file FILE           the tool output file to be parsed
  --dir DIR             the directory containing tool output files to be
                        parsed
  --log_output LOG_OUTPUT
                        a file to which all output in this session will be
                        logged
  --log_command_history LOG_COMMAND_HISTORY
                        a file in which to record the command history of this
                        session
  --import_whittler_output IMPORT_WHITTLER_OUTPUT
                        consume and continue working with a file that was
                        outputted by Whittler's "export" command"
(base) PS C:\Scripts\Whittler> python .\Whittler.py --config trufflehog --file "C:\trufflehog_output.json" --log_command_history "C:\whittler_commands.txt" --log_output "C:\whittler_output.txt"

Welcome to the Whittler shell. Type "help" for a list of commands.

Parsing provided files...

Done.

Whittler > help

navigation:
|   show [[limit]]  :  Show the current data context, up to [limit] entries (shows all entries by default)
|   dig [attr]      :  Dig into a specific data grouping category, either by attribute name, or by attribute id
|   up              :  Dig up a level into the broader data grouping category
|   top             :  Dig up to the top level
|   exit            :  Gracefully exit the program

data model interaction:
|   irrelevant [[id]]      :  Mark all elements in the current context, or those referenced by [id], as irrelevant
|                             results
|   relevant [[id]]        :  Mark all elements in the current context, or those referenced by [id], as relevant results
|   group [id] [[attr]]    :  Using data science, group all results in the database by similarity to the attribute
|                             referenced by [id]. Or, if [id] points to a specific result, group by similarity to a
|                             specific attribute of the result referenced by [id].
|   game [[id]]            :  Play a game where individual results are presented one-by-one, and the user is asked
|                             whether the result is relevant or not and why. Using this information, other similar
|                             results are also eliminated in bulk. If [id] is specified, then the results presented are
|                             limited to the result group represented by the specified [id].
|   filter [str] [[attr]]  :  Mark all results containing [str] in a particular attribute as irrelevant (case-
|                             insensitive)

output:
|   quiet [[attr]]         :  Suppress an attribute from being displayed when printing out raw result data
|   unquiet [[attr]]       :  Undo the suppression from an earlier quiet command
|   solo [[attr]]          :  Print only a single attribute's value when printing out raw result data
|   SOLO [[attr]]          :  Print ONLY a single attribute's value when printing out raw result data, with no context
|                             IDs or attribute value names
|   unsolo                 :  Disable solo mode. Note that this retains any attributes suppressed using the "quiet"
|                             command.
|   history                :  Print all commands that have been run in this session so far
|   export [fname] [[id]]  :  Export all relevant results in JSON form at into the file [fname]. Optionally, limit the
|                             output to the result set as referenced by [id].

NOTE: This shell supports quoted arguments and redirecting command outout to a file using the ">" operator.

Whittler > 
```