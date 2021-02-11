# Whittler

## About

This utility is designed to consume large datasets of results of some sort, and let you qualitatively or quantitatively rule out certain results as irrelevant. It splits the data into intuitive categories and lets you interact with the dataset, marking results as relevant or irrelevant as desired. It also has the capability to use a combination of string-similarity algorithms to make "fuzzy groups" of elements that are similar in some way or another, and mark those as relevant or irrelevant.

Whittler was designed to deal with the output of security tools that return thousands of results, many of which are false-positives. However, it could be used to categorize and explore any type of dataset. Whittler uses modules to import the data in a given dataset, and making modules is easy, only requiring basic Python knowledge (see the "Making new modules" section below).

## Quickstart

Install with:

```
> pip install Whittler
```

Then Whittler can be run with:

```
> Whittler

OR

> python -m Whittler

OR

> python ./Whittler/Whittler.py
```

The first usage syntax is the most elegant, but may not work if you have multiple Python interpreters installed. The second two usage syntaxes allow you to explicitly specify your Python interpreter.

## Sample Usage

```
(base) PS C:\Scripts\Whittler> Whittler --help
usage: Whittler.py [-h] --config {bandit,pssa_csv,sarif,trufflehog}
                   [--file FILE [FILE ...]] [--dir DIR [DIR ...]]
                   [--import_whittler_output FILE_OR_DIR [FILE_OR_DIR ...]] [--log_output [FILENAME]]
                   [--log_command_history [FILENAME]] [--script SCRIPT_STRING] [--scriptfile SCRIPT_FILE]

An interactive script to whittle down large datasets

optional arguments:
  -h, --help            show this help message and exit

basic arguments:
  --config {bandit,pssa_csv,sarif,trufflehog}
                        the module to use to parse the specified tool output files.

data ingestion arguments:
  --file FILE [FILE ...]
                        the tool output file to be parsed
  --dir DIR [DIR ...]   the directory containing tool output files to be parsed
  --import_whittler_output FILE_OR_DIR [FILE_OR_DIR ...]
                        consume and continue working with one or more files that were outputted by Whittler's
                        "export" command

output control arguments:
  --log_output [FILENAME]
                        a file to which all output in this session will be logged (default: a new file in the
                        .whittler folder in your home directory)
  --log_command_history [FILENAME]
                        a file in which to record the command history of this session, in a format that can
                        be imported and re-run by the --scriptfile flag (default: a new file in the .whittler
                        folder in your home directory)

scripting arguments:
  --script SCRIPT_STRING
                        run a script specified with a string on the command line, with each command separated
                        by semicolons (backslash-escape for a literal semicolon)
  --scriptfile SCRIPT_FILE
                        run a script provided in a file, with one command per line
(base) PS C:\Scripts\Whittler> Whittler --config trufflehog --file "C:\trufflehog_output.json" --log_command_history --log_output

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
|   quiet [[attr]]             :  Suppress an attribute from being displayed when printing out raw
|                                 result data
|   unquiet [[attr]]           :  Undo the suppression from an earlier quiet command
|   solo [[attr]]              :  Print only a single attribute's value when printing out raw result
|                                 data
|   SOLO [[attr]]              :  Print ONLY a single attribute's value when printing out raw result
|                                 data, with no context IDs or attribute value names
|   unsolo                     :  Disable solo mode. Note that this retains any attributes
|                                 suppressed using the "quiet" command.
|   sort [colname]             :  Sorts the displayed results by the value in the specified column.
|                                 Use quotes if the column name has a space in it.
|   sortn [colname]            :  Sorts the displayed results numerically by the value in the
|                                 specified column. Use quotes if the column name has a space in it.
|   rsort [colname]            :  Reverse-sorts the displayed results by the value in the specified
|                                 column. Use quotes if the column name has a space in it.
|   rsortn [colname]           :  Reverse-sorts the displayed results numerically by the value in
|                                 the specified column. Use quotes if the column name has a space in
|                                 it.
|   history                    :  Print all commands that have been run in this session so far
|   width [numchars]           :  Modify the maxiumum terminal width, in characters, that all output
|                                 will be formatted to
|   exportjson [fname] [[id]]  :  Export all relevant results in JSON form at into the file [fname].
|                                 Optionally, limit the output to the result set as referenced by
|                                 [id].
|   export [fname] [[id]]      :  Export all relevant results in Python Pickle (serialized binary)
|                                 form at into the file [fname]. Optionally, limit the output to the
|                                 result set as referenced by [id].

NOTE: This shell supports quoted arguments and redirecting command output to a file using the ">" operator.

Whittler > 
```

## Prerequisites

This shell has been tested on Python >= 3.8 .

Whittler is written with mostly standard libraries, plus numpy. The only (optional) nonstandard library used in this project is [pyxDamerauLevenshtein](https://github.com/gfairchild/pyxDamerauLevenshtein), which is used to improve its ability to predict fuzzy groups of results for bulk categorization. It can be installed via the following command:

```
pip install pyxDamerauLevenshtein
```

Or, alternatively:

```
python -m pip install pyxDamerauLevenshtein
```

## Installation

### Installing with pip

```
pip install Whittler
```

### Running from source

1. Ensure that Python >=3.8 is installed, and double-check in a console window with `python --version`
2. Download or clone this repo, and navigate to the Whittler subfolder of the repo
3. `python .\Whittler.py --help`

## Output

By default, Whittler will just output to the console. However, if the `--log_command_history` or `--log_output` flags are specified, Whittler will output the full transcript of your session and/or a full list of the commands you ran into a .whittler folder that is created in your user profile's home directory. (Both of these parameters can optionally take filenames that will be used for output instead of the default files in the .whittler folder.) To recreate an entire Whittler session (given the same input file corpus), the command history can simply be copy-pasted into the Whittler shell - all the data structures used by Whittler are ordered and sorted to enable recreating sessions accurately.

## Game mode

Whittler features a "game mode" that can be entered using the "game" command. In this mode, the results in Whittler's database will be displayed one-by-one, and Whittler will ask whether the result is relevant to you or not. Based on your response, it will gather information on exactly why the result was irrelevant, and optionally use data science algorithms to deduce other results that you may also find similar to the current result. It will show you results you haven't categorized as relevant/irrelevant until you've worked through the entire database, or decide to exit the game. In my experience, this tends to be the quickest way to whittle through huge datasets :)

## Making new modules

Whittler can ingest any data source. Just copy modules/_sample_module.py to a new file in the modules/ directory and work from there. The sample module has documentation to help you craft your new data ingestion module. (Just make sure that your new module's filename does not start with an underscore - module filenames starting with underscores are ignored.)