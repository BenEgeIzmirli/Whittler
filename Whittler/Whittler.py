#!/usr/bin/env python

import os
import sys

WHITTLER_DIRNAME = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(WHITTLER_DIRNAME))
try:
    sys.path.remove(WHITTLER_DIRNAME)
except ValueError: # Already removed
    pass

from Whittler.classes.ResultDatabase import ResultDatabase
from Whittler.classes.Result import Result
from Whittler.classes.input_utils import *
from Whittler.classes.NestedObjectPointer import ObjectView
from Whittler.classes.RelevanceFilteredResultList import RelevanceFilteredResultList
import importlib
import importlib.machinery
from pathlib import Path
import datetime
import argparse
import json
import pickle
import gzip
import traceback

try:
    import IPython
    IPYTHON_INSTALLED = True
except ImportError:
    IPYTHON_INSTALLED = False


def main_loop(resultdb):
    global redirect_file, global_redirect_file, cached_commands
    current_view = None
    while True:
        try:
            if not redirect_file is None:
                redirect_file.close()
                redirect_file = None
            if current_view is None:
                current_view = resultdb.navigate_view()
            if len(cached_commands):
                user_input = cached_commands[0]
                cached_commands = cached_commands[1:]
                wprint(f"Whittler > {' '.join([user_input[0]]+user_input[1])}")
            else:
                user_input = parse_user_input(winput("Whittler > "))
                if user_input is None:
                    continue
                if len(user_input) > 1:
                    cached_commands = user_input[1:]
                user_input = user_input[0]
            if user_input is None:
                continue
            verb,args,redirect = user_input
            if verb.startswith("#"):
                continue

            if not redirect is None:
                try:
                    redirect_file = open(redirect, "w+", encoding="utf-8")
                except PermissionError:
                    wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")


            # In the following switch statement, "continue" to skip updating the current view,
            # otherwise, the view will be updated. Set the below navigate_ptr variable to the
            # pointer to which we want to navigate, and it will be reset on the next loop.
            navigate_ptr = None

            if verb == "help":
                print_help()
                continue
            elif verb == "shell":
                if IPYTHON_INSTALLED:
                    wprint("Welcome to the subshell, you can use the resultdb object to interact with the dataset.")
                    # with IPython.utils.io.capture_output() as output:
                    IPython.embed(colors="neutral")
                    # wprint(output.stdout,quiet=True)
                else:
                    wprint("No IPython package detected, falling back to basic eval() REPL.")
                    wprint("Type \"exit\" to exit back to the main Whittler shell.")
                    while True:
                        try:
                            cmd = winput("> ").strip()
                            if cmd == "exit":
                                break
                            wprint(eval(cmd, globals(), locals()))
                        except:
                            print(traceback.format_exc())
                    wprint("Exiting subshell.")


            ########################
            #  Navigation commands
            #

            elif verb == "show":
                limit = get_int_from_args(args)
                limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
                wprint(resultdb.construct_view(override_options={"limit":limit})[0])
                continue
            elif verb == "showall":
                limit = get_int_from_args(args)
                limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
                wprint(resultdb.construct_view(override_options={"limit":limit,"show_irrelevant":True})[0])
                continue
            elif verb == "dig":
                navigate_ptr = get_ptr_from_id_arg(resultdb, args)
                if navigate_ptr is False:
                    wprint("no [attr] specified, no digging performed.")
                    continue
                if navigate_ptr is None:
                    continue
            elif verb == "up":
                if resultdb.current_pointer.is_base_pointer():
                    wprint("Already at root context.\n")
                    continue
                resultdb.current_pointer.go_up_level()
                # We want to pop out from the categorized_results or grouped_results contexts implicitly.
                if len(resultdb.current_pointer.path) == 1:
                    resultdb.current_pointer.go_up_level()
            elif verb == "top":
                resultdb.navigate_view()
                continue
            elif verb == "dump":
                limit = get_int_from_args(args)
                limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
                wprint(resultdb.results.show_view(limit=limit)[0])
                continue
            elif verb == "exit":
                sys.exit(0)


            ####################################
            #  Data model interaction commands
            #
            
            elif verb == "irrelevant":
                ptr = get_ptr_from_id_arg(resultdb, args)
                if ptr is False:
                    ptr = resultdb.current_pointer
                elif ptr is None:
                    continue
                obj = ptr.give_pointed_object()
                obj.mark_irrelevant()
            elif verb == "relevant":
                ptr = get_ptr_from_id_arg(resultdb, args)
                if ptr is False:
                    ptr = resultdb.current_pointer
                elif ptr is None:
                    continue
                obj = ptr.give_pointed_object()
                obj.mark_relevant()
            elif verb == "fuzzygroup":
                ptr = get_ptr_from_id_arg(resultdb, args)
                if ptr is False:
                    wprint("need to specify an [id], the value of which to group by.")
                    continue
                if ptr is None:
                    wprint(f"couldn't find result object with id {args[1]}.")
                    continue
                obj = ptr.give_pointed_object()
                if isinstance(obj, resultdb.result_class):
                    groupattr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                    if groupattr is False:
                        groupattr = select_attribute(resultdb, "Which attribute of this result would you like to group by? ")
                    elif groupattr is None:
                        continue
                    groupval = obj[groupattr]
                else:
                    wprint("[attr] must point to a specific attribute name of this result.")
                    continue
                group_interactive(resultdb, groupattr, groupval)
            elif verb == "ungroup":
                ptr = get_ptr_from_id_arg(resultdb, args)
                if ptr is False:
                    wprint("need to specify an [id], the value of which to group by.")
                    continue
                if ptr is None:
                    wprint(f"couldn't find result object with id {args[1]}.")
                    continue
                group_ptr = resultdb.current_pointer
                if not any(vertex.value=="grouped_results" for vertex in group_ptr.path):
                    wprint("The current view must be of a result group to use the \"ungroup\" function.")
                    continue
                # We know that ptr points to an object in the current view context, since get_ptr_from_id_arg
                # retrieves the ptr by looking it up in the current view context.
                group = group_ptr.give_pointed_object()
                ungroup_obj_key = ptr.path[-1].value
                del group[ungroup_obj_key]
            elif verb == "find":
                if not len(args):
                    wprint("Need to provide a string to search by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                matches = RelevanceFilteredResultList(result for result in resultdb.results if filter_str in result[filtered_attr])
                wprint(matches.show_view()[0])
            elif verb == "invfind":
                if not len(args):
                    wprint("Need to provide a string to search by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                matches = RelevanceFilteredResultList(result for result in resultdb.results if filter_str not in result[filtered_attr])
                wprint(matches.show_view()[0])
            elif verb == "search":
                if not len(args):
                    wprint("Need to provide a string to search by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                matches = [result for result in resultdb.results if filter_str in result[filtered_attr]]
                resultdb.register_grouped_results(filtered_attr,filter_str,matches)
                wprint(f"Found {len(matches)} results, and saved them as a new result group.")
            elif verb == "invsearch":
                if not len(args):
                    wprint("Need to provide a string to search by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                matches = [result for result in resultdb.results if filter_str not in result[filtered_attr]]
                resultdb.register_grouped_results(filtered_attr,filter_str,matches)
                wprint(f"Found {len(matches)} results, and saved them as a new result group.")
            elif verb == "game":
                ptr = get_ptr_from_id_arg(resultdb, args)
                if ptr is False:
                    obj = resultdb.results
                elif ptr is None:
                    continue
                else:
                    obj = ptr.give_pointed_object()
                play_elimination_game(resultdb, obj)
            elif verb == "filter":
                if not len(args):
                    wprint("Need to provide a string to filter by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                ct = 0
                for result in resultdb.results:
                    if filter_str.lower() in result[filtered_attr].lower():
                        result.mark_irrelevant()
                        ct += 1
                wprint(f"Marked {ct} results as irrelevant using the filter.")
            elif verb == "invfilter":
                if not len(args):
                    wprint("Need to provide a string to filter by.")
                    continue
                filter_str = args[0]
                filtered_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if filtered_attr is False:
                    filtered_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
                elif filtered_attr is None:
                    continue
                ct = 0
                for result in resultdb.results:
                    if filter_str.lower() not in result[filtered_attr].lower():
                        result.mark_irrelevant()
                        ct += 1
                wprint(f"Marked {ct} results as irrelevant using the filter.")

            
            
            #####################
            #  Output commands
            #
            
            elif verb == "quiet":
                quieted_attr = get_attrname_from_attribute_arg(resultdb, args)
                if quieted_attr is False:
                    quieted_attr = select_attribute(resultdb, "Which attribute would you like to suppress in output? ")
                elif quieted_attr is None:
                    continue
                ObjectView.global_options["quiet"].append(quieted_attr)
            elif verb == "unquiet":
                attrs = ObjectView.global_options["quiet"]
                if not len(attrs):
                    wprint("No silenced attributes to unquiet.")
                    continue
                quieted_attr = get_attrname_from_attribute_arg(resultdb, args)
                if quieted_attr is False:
                    for i in range(len(attrs)):
                        wprint(f" {i} : {attrs[i]}")
                    wprint()
                    index = int(winput("Which attribute would you like to un-suppress in output? "))
                    quieted_attr = attrs[index]
                elif quieted_attr is None:
                    continue
                elif quieted_attr not in attrs:
                    wprint("That attribute was not silenced, no action taken.")
                    continue
                ObjectView.global_options["quiet"].remove(quieted_attr)
            elif verb == "solo":
                solo_attr = get_attrname_from_attribute_arg(resultdb, args)
                if solo_attr is False:
                    solo_attr = select_attribute(resultdb, "Which attribute would you like to print exclusively in output? ")
                elif solo_attr is None:
                    continue
                ObjectView.global_options["solo"] = solo_attr
            elif verb == "SOLO":
                solo_attr = get_attrname_from_attribute_arg(resultdb, args)
                if solo_attr is False:
                    solo_attr = select_attribute(resultdb, "Which attribute would you like to print exclusively in output? ")
                elif solo_attr is None:
                    continue
                ObjectView.global_options["SOLO"] = solo_attr
            elif verb == "unsolo":
                ObjectView.global_options["solo"] = None
                ObjectView.global_options["SOLO"] = None
            elif verb in ("sort","sortn","rsort","rsortn"):
                if not len(args):
                    wprint("Need a column name to sort by.")
                    continue
                objview = resultdb.current_pointer.give_pointed_object().objectview
                objview["sort_by"] = args[0]
                objview["sort_numeric"] = verb.endswith("n")
                objview["sort_reverse"] = verb.startswith("r")
            elif verb == "history":
                wprint()
                for cmd in command_history:
                    wprint(cmd)
                wprint()
                continue
            elif verb == "width":
                if not len(args):
                    wprint("Need a column name or attribute value to sort by.")
                try:
                    new_width = int(args[0])
                except:
                    wprint(f"Failed to parse {args[0]} as an integer.")
                    continue
                Config.MAX_OUTPUT_WIDTH = new_width
            elif verb == "exportjson":
                if not len(args):
                    wprint("Need a filename to export to.")
                    continue
                try:
                    fname = args[0]
                    ptr = get_ptr_from_id_arg(resultdb, args, id_arg_position=1)
                    if ptr is False:
                        obj = resultdb
                    elif ptr is None:
                        continue
                    else:
                        obj = ptr.give_pointed_object()
                    all_results_json_gen = obj.exportjson()
                    try:
                        if os.path.isfile(fname):
                            answer = winput("WARNING: file already exists. Override? (N/y) ").strip().lower()
                            if not (answer == "y" or answer == "yes"):
                                wprint("Aborting export, no files written.")
                                continue
                            wprint("Overwriting file...")
                        with gzip.GzipFile(fname,"wb") as f:
                            json_encoder = json.JSONEncoder()
                            for result_json in all_results_json_gen:
                                for chunk in json_encoder.iterencode(result_json):
                                    f.write(chunk.encode('utf-8'))
                        wprint(f"Export success, compressed JSON output written to {fname}.")
                    except PermissionError:
                        wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")
                    continue
                except Exception as e:
                    wprint(f"Exception encountered while exporting: {e}")
                    continue
            elif verb == "export":
                if not len(args):
                    wprint("Need a filename to export to.")
                    continue
                try:
                    fname = args[0]
                    ptr = get_ptr_from_id_arg(resultdb, args, id_arg_position=1)
                    if ptr is False:
                        # no specific object (result, or row, etc) was specified - export everything
                        obj = resultdb
                    elif ptr is None:
                        wprint("Couldn't find the specified result, no action taken.")
                        continue
                    else:
                        obj = ptr.give_pointed_object()
                    resultgen = obj.all_result_objects()
                    try:
                        if os.path.isfile(fname):
                            answer = winput("WARNING: file already exists. Override? (N/y) ").strip().lower()
                            if not (answer == "y" or answer == "yes"):
                                wprint("Aborting export, no files written.")
                                continue
                            wprint("Overwriting file...")
                        with gzip.GzipFile(fname,"wb") as f:
                            # pickle-dump the results one by one, allowing them to be loaded one-by-one when loading back.
                            # https://stackoverflow.com/questions/20716812/saving-and-loading-multiple-objects-in-pickle-file
                            for result in resultgen:
                                pickle.dump(result, f)
                        wprint(f"Export success, compressed serialized output written to {fname}.")
                    except PermissionError:
                        wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")
                    continue
                except Exception as e:
                    wprint(f"Exception encountered while exporting: {e}")
                    continue
            else:
                wprint("Unrecognized command.\n")
                continue
            
            if navigate_ptr:
                current_view = resultdb.navigate_view(navigate_ptr)
            else:
                current_view = resultdb.update_current_view()
        except KeyboardInterrupt:
            sys.exit(0)
        except SystemExit:
            raise
        except:
            print(traceback.format_exc())

        
HOME_DIRECTORY = str(Path.home())
WHITTLER_DIRECTORY = HOME_DIRECTORY+"/.whittler"
if not os.path.isdir(WHITTLER_DIRECTORY):
    os.mkdir(WHITTLER_DIRECTORY,mode=0o770)

result_classes = {}

def load_module(fname, in_default_module_directory):
    if in_default_module_directory:
        module = importlib.import_module(f"Whittler.modules.{fname[:fname.index('.')]}")
    else:
        modulepath = os.path.abspath(fname)
        folder, fname = os.path.split(modulepath)
        if not fname.endswith(".py"):
            raise Exception("Module names must end in .py")
        loader = importlib.machinery.SourceFileLoader(fname[:fname.index('.')], modulepath)
        module = loader.load_module()
    result_class = None
    for clsname in dir(module):
        if clsname.startswith("__"):
            continue
        cls = getattr(module, clsname)
        if isinstance(cls, type) and issubclass(cls, Result) and not cls is Result:
            result_classes[cls.FRIENDLY_NAME] = cls
            if not result_class is None:
                raise Exception(f"Multiple Result subclasses defined in the module loaded from {module.__file__}")
            result_class = cls
    if not result_class:
        raise Exception(f"Could not find any Result subclass in the module loaded from {module.__file__}")
    return result_class

# load default result classes
for fname in filter(lambda s: not s.startswith("_") , os.listdir(WHITTLER_DIRNAME+"/modules")):
    load_module(fname, True)

# This class is a hack for the choices= option of the --config argparse argument definition. I want the help
# message to enumerate the default modules in the Whittler/modules folder, but I also want the user to be able
# to specify a custom file to try to use as a module.
class ConfigChoices(list):
    def __contains__(self,value):
        return True

config_choices = ConfigChoices(list(result_classes.keys()))


# to be populated if the --script or --scriptfile flags are specified
cached_commands = []

def main():
    global cached_commands
    # This is a patch for running the script with "python -m Whittler" - without this modification the help messages
    # think the script is named "__main__.py".
    old_argv0 = sys.argv[0]
    sys.argv[0] = old_argv0.replace("__main__","Whittler")

    parser = argparse.ArgumentParser(description="An interactive script to whittle down large datasets")

    # Reset the script name back to the old value, just in case.
    sys.argv[0] = old_argv0

    # Required args
    bargs = parser.add_argument_group("basic arguments")
    bargs.add_argument('--config',
                    help='the module to use to parse the specified tool output files.',
                    type=str, nargs=1, choices=config_choices, default=None, required=True)

    # Data ingestion args
    diargs = parser.add_argument_group("data ingestion arguments")
    #diargs = diargs.add_mutually_exclusive_group(required=True)
    diargs.add_argument('--file',
                        help='the tool output file to be parsed',
                        type=str, nargs='+', default='')
    diargs.add_argument('--dir',
                        help='the directory containing tool output files to be parsed',
                        type=str, nargs='+', default='')
    diargs.add_argument('--import_whittler_output',
                        help='consume and continue working with one or more files that were outputted by Whittler\'s "export" command',
                        type=str, nargs='+', default=None, metavar="FILE_OR_DIR")
    diargs.add_argument('--memory_compression',
                        help='enable in-memory compression for working with very large datasets',
                        action='store_true')
    diargs.add_argument('--multiprocessing',
                        help='enable multiprocessing for working with very large datasets (in development, currently only '+\
                             'accelerates imports from directories with many files)',
                        action='store_true')

    # Output control args
    ocargs = parser.add_argument_group("output control arguments")
    ocargs.add_argument('--log_output',
                        help='a file to which all output in this session will be logged (default: a new file in the '+\
                            '.whittler folder in your home directory)',
                        type=str, nargs="?", default=None, metavar="FILENAME",
                        const=WHITTLER_DIRECTORY+'/{date:%Y-%m-%d_%H-%M-%S}_log.txt'.format( date=datetime.datetime.now() ) )
    ocargs.add_argument('--log_command_history',
                        help='a file in which to record the command history of this session, in a format that can be '+\
                            'imported and re-run by the --scriptfile flag (default: a new file in the .whittler folder in '+\
                            'your home directory)',
                        type=str, nargs="?", default=None, metavar="FILENAME",
                        const=WHITTLER_DIRECTORY+'/{date:%Y-%m-%d_%H-%M-%S}_command_log.txt'.format( date=datetime.datetime.now() ))

    # Scripting arguments
    sargs = parser.add_argument_group("scripting arguments")
    sargs.add_argument('--script',
                    help='run a script specified with a string on the command line, with each command separated by semicolons '+\
                            '(backslash-escape for a literal semicolon)',
                    type=str, nargs=1, default=None, metavar="SCRIPT_STRING")
    sargs.add_argument('--scriptfile',
                    help='run a script provided in a file, with one command per line',
                    type=str, nargs=1, default=None, metavar="SCRIPT_FILE")

    args = parser.parse_args()

    if args.memory_compression:
        Config.MEMORY_COMPRESSION = True
        Config.MemoryCompressor.COMPRESSION_ENABLED = True
    
    if args.multiprocessing:
        Config.MULTIPROCESSING = True
        Config.MemoryCompressor.MULTIPROCESSING = True

    if not args.log_output is None:
        logdir = args.log_output[0] if isinstance(args.log_output,list) else args.log_output
        try:
            set_global_redirect_file(open(logdir,"w+", encoding="utf-8"))
        except PermissionError:
            wprint("Lacking permissions to write to the specified all-output log file.")
            sys.exit(1)
        get_global_redirect_file().write(" ".join(sys.argv)+"\n\n")
    if not args.log_command_history is None:
        logcmddir = args.log_command_history[0] if isinstance(args.log_command_history,list) else args.log_command_history
        try:
            set_command_redirect_file(open(logcmddir,"w+", encoding="utf-8"))
        except PermissionError:
            wprint("Lacking permissions to write to the specified command history log file.")
            sys.exit(1)
    if not args.config or len(args.config) != 1:
        parser.print_help()
        sys.exit(1)
    try:
        config = args.config[0]
        if config in result_classes:
            resultdb = ResultDatabase(result_classes[config])
        else:
            resultdb = ResultDatabase(load_module(config, False))
        if not args.dir and not args.file and not args.import_whittler_output:
            parser.print_help()
            sys.exit(1)
        wprint("\nWelcome to the Whittler shell. Type \"help\" for a list of commands.\n")
        if args.script and args.scriptfile:
            wprint("Error: the --script and --scriptfile flags cannot both be specified at once.\n")
            parser.print_help()
            sys.exit(1)
        if args.script or args.scriptfile:
            if args.script:
                wprint(f"Using script from command line.")
                cached_commands = parse_user_input(args.script[0])
            else:
                wprint(f"Importing script from file {args.scriptfile[0]} .")
                with open(args.scriptfile[0],"r") as f:
                    cached_commands = parse_user_input(" ; ".join(f.readlines()))
        hash_cache = set()
        if args.dir:
            wprint("Parsing files from provided directories...")
            wprint()
            for d in args.dir:
                resultdb.parse_from_directory(d, hash_cache=hash_cache, multiprocessing_import=args.multiprocessing)
        if args.file:
            wprint("Parsing provided files...")
            wprint()
            for fname in args.file:
                resultdb.parse_from_file(fname, hash_cache=hash_cache)
        if args.import_whittler_output:
            wprint("Importing provided files...")
            wprint()
            for import_target in args.import_whittler_output:
                if os.path.isdir(import_target):
                    import_target = [import_target+"/"+fname for fname in os.listdir(import_target)]
                else:
                    import_target = [import_target]
                for fname in import_target:
                    resultdb.parse_from_export(fname, hash_cache=hash_cache)
        
        if Config.MEMORY_COMPRESSION and Config.MemoryCompressor.training_mode:
            Config.MemoryCompressor.disable_training_mode()

        wprint("Done.\n")
        main_loop(resultdb)
    except:
        raise
    finally:
        print()
        if not command_redirect_file is None:
            fname = command_redirect_file.name.replace('\\','/')
            wprint(f"Saving logged command history to {fname} ...")
            command_redirect_file.close()
        if not redirect_file is None:
            fname = redirect_file.name.replace('\\','/')
            wprint(f"Saving pipe output to {fname} ...")
            redirect_file.close()
        goodbye_said = False
        if not global_redirect_file is None:
            fname = global_redirect_file.name.replace('\\','/')
            wprint(f"Saving logged output to {fname} ...")
            wprint("\nGoodbye.\n")
            goodbye_said = True
            global_redirect_file.close()
        if not goodbye_said:
            print("\nGoodbye.\n")
        

if __name__ == "__main__":
    main()
