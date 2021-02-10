from classes.ResultDatabase import ResultDatabase
from classes.Result import Result, RelevanceFilteredResultList
from classes.input_utils import *
import importlib
import sys
import os
import datetime
import argparse
from pathlib import Path
import json
import pickle


def main_loop(resultdb):
    global redirect_file, global_redirect_file, cached_commands
    sort_by = None
    sort_numeric = False
    sort_reverse = False
    while True:
        if not redirect_file is None:
            redirect_file.close()
            redirect_file = None
        resultdb.update_current_view(sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
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

        if verb == "help":
            print_help()
            continue


        ########################
        #  Navigation commands
        #

        elif verb == "show":
            limit = get_int_from_args(args)
            limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
            wprint(resultdb.construct_view(limit=limit, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)[0])
            continue
        elif verb == "showall":
            limit = get_int_from_args(args)
            limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
            wprint(resultdb.construct_view(limit=limit, show_irrelevant=True, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)[0])
            continue
        elif verb == "dig":
            ptr = get_ptr_from_id_arg(resultdb, args)
            if ptr is False:
                wprint("no [attr] specified, no digging performed.")
                continue
            if ptr is None:
                continue
            sort_by = None
            sort_numeric = False
            sort_reverse = False
            resultdb.navigate_view(ptr)
            continue
        elif verb == "up":
            if resultdb.current_pointer.is_base_pointer():
                wprint("Already at root context.\n")
                continue
            sort_by = None
            sort_numeric = False
            sort_reverse = False
            resultdb.current_pointer.go_up_level()
            # We want to pop out from the categorized_results or grouped_results contexts implicitly.
            if len(resultdb.current_pointer.path) == 1:
                resultdb.current_pointer.go_up_level()
            continue
        elif verb == "top":
            while not resultdb.current_pointer.is_base_pointer():
                resultdb.current_pointer.go_up_level()
            sort_by = None
            sort_numeric = False
            sort_reverse = False
            continue
        elif verb == "dump":
            limit = get_int_from_args(args)
            limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
            wprint(resultdb.results.show_view(limit=limit)[0])
        elif verb == "dumpall":
            limit = get_int_from_args(args)
            limit = limit if limit else None # get_int_from_args returns False if no value was supplied for the arg
            # todo
            wprint(resultdb.results.show_view(limit=limit)[0])
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
            continue
        elif verb == "relevant":
            ptr = get_ptr_from_id_arg(resultdb, args)
            if ptr is False:
                ptr = resultdb.current_pointer
            elif ptr is None:
                continue
            obj = ptr.give_pointed_object()
            obj.mark_relevant()
            continue
        elif verb == "group":
            ptr = get_ptr_from_id_arg(resultdb, args)
            if ptr is False:
                wprint("need to specify an [id], the value of which to group by.")
                continue
            if ptr is None:
                continue
            obj = ptr.give_pointed_object()
            if isinstance(obj, resultdb.result_class):
                groupattr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
                if groupattr is False:
                    groupattr = select_attribute(resultdb, "Which attribute of this result would you like to group by? ")
                elif groupattr is None:
                    continue
                groupval = obj[groupattr]
            elif isinstance(obj, RelevanceFilteredResultList):
                groupval = ptr.go_up_level().value
                groupattr = ptr.go_up_level().value
            else:
                raise NotImplementedError()
            group_interactive(resultdb, groupattr, groupval)
            continue
        elif verb == "game":
            ptr = get_ptr_from_id_arg(resultdb, args)
            if ptr is False:
                obj = resultdb.results
            elif ptr is None:
                continue
            else:
                obj = ptr.give_pointed_object()
            play_elimination_game(resultdb, obj)
            continue
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
            do_inverse = winput("Mark all matches as irrelevant (Y)? Or mark all non-matches as irrelevant (n)? ")
            if not do_inverse.strip() or do_inverse.lower() == "y":
                do_inverse = False
            else:
                do_inverse = True
            ct = 0
            for result in resultdb.results:
                if not do_inverse:
                    result_matches = filter_str.lower() in result[filtered_attr].lower()
                else:
                    result_matches = filter_str.lower() not in result[filtered_attr].lower()
                if result_matches:
                    result.mark_irrelevant()
                    ct += 1
            wprint(f"Marked {ct} results as irrelevant using the filter.")
            continue

        
        
        #####################
        #  Output commands
        #
        
        elif verb == "quiet":
            quieted_attr = get_attrname_from_attribute_arg(resultdb, args)
            if quieted_attr is False:
                quieted_attr = select_attribute(resultdb, "Which attribute would you like to suppress in output? ")
            elif quieted_attr is None:
                continue
            resultdb.result_class.SILENCED_ATTRIBUTES.add(quieted_attr)
            continue
        elif verb == "unquiet":
            attrs = list(resultdb.result_class.SILENCED_ATTRIBUTES)
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
            resultdb.result_class.SILENCED_ATTRIBUTES.remove(quieted_attr)
            continue
        elif verb == "solo":
            solo_attr = get_attrname_from_attribute_arg(resultdb, args)
            if solo_attr is False:
                solo_attr = select_attribute(resultdb, "Which attribute would you like to print exclusively in output? ")
            elif solo_attr is None:
                continue
            resultdb.result_class.SOLO_ATTRIBUTE = solo_attr
            continue
        elif verb == "SOLO":
            solo_attr = get_attrname_from_attribute_arg(resultdb, args)
            if solo_attr is False:
                solo_attr = select_attribute(resultdb, "Which attribute would you like to print exclusively in output? ")
            elif solo_attr is None:
                continue
            resultdb.result_class.SUPER_SOLO_ATTRIBUTE = solo_attr
            continue
        elif verb == "unsolo":
            resultdb.result_class.SOLO_ATTRIBUTE = None
            resultdb.result_class.SUPER_SOLO_ATTRIBUTE = None
            continue
        elif verb == "sort":
            if not len(args):
                wprint("Need a column name or attribute value to sort by.")
            sort_by = args[0]
            sort_numeric = False
            sort_reverse = False
            continue
        elif verb == "sortn":
            if not len(args):
                wprint("Need a column name or attribute value to sort by.")
            sort_by = args[0]
            sort_numeric = True
            sort_reverse = False
            continue
        elif verb == "rsort":
            if not len(args):
                wprint("Need a column name or attribute value to sort by.")
            sort_by = args[0]
            sort_numeric = False
            sort_reverse = True
            continue
        elif verb == "rsortn":
            if not len(args):
                wprint("Need a column name or attribute value to sort by.")
            sort_by = args[0]
            sort_numeric = True
            sort_reverse = True
            continue
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
            continue
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
                resultlist = obj.export()
                try:
                    if os.path.isfile(fname):
                        answer = winput("WARNING: file already exists. Override? (N/y) ").strip().lower()
                        if not (answer == "y" or answer == "yes"):
                            wprint("Aborting export, no files written.")
                            continue
                        wprint("Overwriting file...")
                    with open(fname,"w", encoding="utf-8") as f:
                        for chunk in json.JSONEncoder().iterencode(resultlist):
                            f.write(chunk)
                    wprint(f"Export success, JSON output written to {fname}.")
                except PermissionError:
                    wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")
                continue
            except Exception as e:
                wprint(f"Exception encountered while exporting: {e}")
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
                resultlist = obj.all_result_objects()
                try:
                    if os.path.isfile(fname):
                        answer = winput("WARNING: file already exists. Override? (N/y) ").strip().lower()
                        if not (answer == "y" or answer == "yes"):
                            wprint("Aborting export, no files written.")
                            continue
                        wprint("Overwriting file...")
                    with open(fname,"wb") as f:
                        pickle.dump(resultlist, f)
                    wprint(f"Export success, serialized output written to {fname}.")
                except PermissionError:
                    wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")
                continue
            except Exception as e:
                wprint(f"Exception encountered while exporting: {e}")

        else:
            wprint("Unrecognized command.\n")
            continue

        
HOME_DIRECTORY = str(Path.home())
WHITTLER_DIRECTORY = HOME_DIRECTORY+"/.whittler"
if not os.path.isdir(WHITTLER_DIRECTORY):
    os.mkdir(WHITTLER_DIRECTORY,mode=0o770)

result_classes = {}
for fname in filter(lambda s: not s.startswith("_") , os.listdir(os.path.dirname(os.path.realpath(__file__))+"/modules")):
    module = importlib.import_module(f"modules.{fname[:fname.index('.')]}")
    for clsname in dir(module):
        if clsname.startswith("__"):
            continue
        cls = getattr(module, clsname)
        if isinstance(cls, type) and issubclass(cls, Result) and not cls is Result:
            result_classes[cls.FRIENDLY_NAME] = cls
            break

parser = argparse.ArgumentParser(description="An interactive script to whittle down large datasets")

# Required args
bargs = parser.add_argument_group("basic arguments")
bargs.add_argument('--config',
                   help='the module to use to parse the specified tool output files.',
                   type=str, nargs=1, choices=list(result_classes.keys()), default=None, required=True)

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


# to be populated if the --script or --scriptfile flags are specified
cached_commands = []

if __name__ == "__main__":
    args = parser.parse_args()
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
    if args.config is None:
        parser.print_help()
        sys.exit(1)
    try:
        resultdb = ResultDatabase(result_classes[args.config[0]])
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
        if args.dir:
            wprint("Parsing provided files...")
            wprint()
            resultdb.parse_from_directory(args.dir[0])
        if args.file:
            wprint("Parsing provided file...")
            wprint()
            resultdb.parse_from_file(args.file[0])
        if args.import_whittler_output:
            wprint("Importing provided files...")
            wprint()
            import_target = args.import_whittler_output[0]
            if os.path.isdir(import_target):
                import_target = [import_target+"/"+fname for fname in os.listdir(import_target)]
            else:
                import_target = [import_target]
            for fname in import_target:
                resultdb.parse_from_export(fname)
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
        

