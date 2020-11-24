from classes.NestedObjectPointer import NestedObjectPointer
from classes.ResultDatabase import ResultDatabase
from classes.Result import Result, RelevanceFilteredResultList
import modules
import importlib
from config import Config
import sys
import os
import datetime
import argparse
from pathlib import Path
import textwrap
import json
import random
import time


actions = {
    "navigation" : {
        "show [[limit]]" : "Show the current data context, up to [limit] entries (shows all entries by default)",
        "dig [attr]" : "Dig into a specific data grouping category, either by attribute name, or by attribute id",
        "up" : "Dig up a level into the broader data grouping category",
        "top" : "Dig up to the top level",
        "dump" : "Display every relevant result in every category",
        "exit" : "Gracefully exit the program"
    },
    "data model interaction" : {
        "irrelevant [[id]]" : "Mark all elements in the current context, or those referenced by [id], as irrelevant results",
        "relevant [[id]]" : "Mark all elements in the current context, or those referenced by [id], as relevant results",
        "group [id] [[attr]]" : "Using data science, group all results in the database by similarity to the attribute referenced "+\
                       "by [id]. Or, if [id] points to a specific result, group by similarity to a specific attribute of "+\
                       "the result referenced by [id].",
        "game [[id]]" : "Play a game where individual results are presented one-by-one, and the user is asked whether "+\
                        "the result is relevant or not and why. Using this information, other similar results are also "+\
                        "eliminated in bulk. If [id] is specified, then the results presented are limited to the result "+\
                        "group represented by the specified [id].",
        "filter [str] [[attr]]" : "Mark all results containing [str] in a particular attribute as irrelevant (case-insensitive)"
    },
    "output" : {
        "quiet [[attr]]" : "Suppress an attribute from being displayed when printing out raw result data",
        "unquiet [[attr]]" : "Undo the suppression from an earlier quiet command",
        "solo [[attr]]" : "Print only a single attribute's value when printing out raw result data",
        "SOLO [[attr]]" : "Print ONLY a single attribute's value when printing out raw result data, with no context IDs or "+\
                 "attribute value names",
        "unsolo" : "Disable solo mode. Note that this retains any attributes suppressed using the \"quiet\" command.",
        # sort
        "history" : "Print all commands that have been run in this session so far",
        "export [fname] [[id]]" : "Export all relevant results in JSON form at into the file [fname]. Optionally, limit "+\
                                  "the output to the result set as referenced by [id]."
    }
}

command_history = []
command_redirect_file = None
global_redirect_file = None
redirect_file = None
class _NoInput:
    pass
def wprint(s=_NoInput):
    if s is _NoInput:
        s = ""
    if not redirect_file is None:
        redirect_file.write(str(s)+"\n")
    if not global_redirect_file is None:
        global_redirect_file.write(str(s)+"\n")
    print(s)

def winput(msg):
    user_input = input(msg)
    command_history.append(user_input)
    if not command_redirect_file is None:
        command_redirect_file.write(user_input+"\n")
    if not redirect_file is None:
        redirect_file.write(str(msg))
        redirect_file.write(user_input+"\n")
    if not global_redirect_file is None:
        global_redirect_file.write(str(msg))
        global_redirect_file.write(user_input+"\n")
    return user_input

def print_help():
    wprint()
    printstr = "|   {{:<{}}}  :  "
    for actioncategory, actiondict in actions.items():
        longest_action_name = max(len(action) for action in actiondict.keys())
        wprint(f"{actioncategory}:")
        for actionname, action_description in actiondict.items():
            prologue = printstr.format(longest_action_name).format(actionname)
            description = textwrap.wrap(action_description, Config.MAX_OUTPUT_WIDTH-len(prologue))
            for line in description:
                wprint(f"{prologue}{line}")
                prologue = "|" + " "*(len(prologue)-1)
        wprint()
    wprint("NOTE: This shell supports quoted arguments and redirecting command outout to a file using the \">\" operator.")
    wprint()

# False means no value was supplied for this arg position, None means failed to parse as int
def get_int_from_args(args, position=0):
    if not len(args) > position:
        return False
    else:
        try:
            argval = int(args[position])
        except ValueError:
            return None
    return argval

# False means no value was supplied for this arg position, None means failed to find corresponding context pointer
def get_ptr_from_id_arg(resultdb, args, id_arg_position=0):
    choice = get_int_from_args(args, position=id_arg_position)
    
    # No value was supplied for this arg position
    if choice is False:
        return False
    
    # we couldn't parse it as an int, so it must be a string literal attribute value
    if choice is None:
        choice = args[id_arg_position]
        for ptr in resultdb.context_pointers.values():
            # The attribute values will be the .value property of the Vertex object given by the last
            # get_by_index operation called on this pointer.
            if ptr.path[-1].value == choice:
                return ptr
        wprint(f"Could not recognize \"{choice}\" as one of the attributes of this dataset.\n")
        return None
    
    # The value supplied was an int, so should be looked up in the context_pointers dict
    if choice not in resultdb.context_pointers:
        wprint(f"Could not recognize {choice} as one of the IDs listed above.\n")
        return None
    return resultdb.context_pointers[choice]

# False means no value was supplied for this arg position, None means failed to find corresponding context pointer
def get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=0):
    ptr = get_ptr_from_id_arg(resultdb, args, id_arg_position=attr_arg_position)
    if ptr is False:
        return False
    attrname = args[attr_arg_position]
    if attrname not in resultdb.result_class.ATTRIBUTES:
        return None
    return attrname

def select_attribute(resultdb, msg):
    attrs = resultdb.result_class.ATTRIBUTES
    for i in range(len(attrs)):
        wprint(f" {i} : {attrs[i]}")
    wprint()
    index = int(winput(msg))
    return attrs[index]

def group_interactive(resultdb, groupattr, groupval):
    wprint("Creating a result group set based on this attribute value...")
    SIMILARITY_THRESHOLD = resultdb.Config.SIMILARITY_THRESHOLD
    while True:
        print(SIMILARITY_THRESHOLD)
        similar_results = resultdb.find_similar_results(groupattr, groupval, similarity_threshold=SIMILARITY_THRESHOLD)
        wprint()
        for val in sorted(set([res[groupattr] for res in similar_results])):
            wprint(f"   {val.strip()}")
        wprint()
        wprint(f"I found {len(similar_results)} similar results with {groupattr} values as shown above.")
        wprint("I want to create a result group set based on these findings, but I want to make sure it's OK.")
        while True:
            grouping_choice = winput("Is this grouping OK (1), too conservative (2), or too liberal (3)? Or, just abandon the group creation (4)? ")
            bad_input = False
            try:
                grouping_choice = int(grouping_choice)
                if grouping_choice not in [1,2,3,4]:
                    bad_input = True
            except:
                bad_input = True
            if bad_input:
                wprint("I didn't understand your input.")
                continue
            break
        if grouping_choice == 1:
            pass
        elif grouping_choice == 2:
            SIMILARITY_THRESHOLD -= SIMILARITY_THRESHOLD / Config.SIMILARITY_THRESHOLD_MODIFICATION_FACTOR
            continue
        elif grouping_choice == 3:
            SIMILARITY_THRESHOLD += (1 - SIMILARITY_THRESHOLD) / Config.SIMILARITY_THRESHOLD_MODIFICATION_FACTOR
            continue
        elif grouping_choice == 4:
            wprint("OK, abandoning group creation.")
            break
        resultdb.register_grouped_results(groupattr, groupval, similar_results)
        wprint("Created result set based on this entry.")
        ptr = NestedObjectPointer(resultdb)
        ptr.access_property("grouped_results")
        ptr.get_by_index(groupval)
        return ptr

def get_and_parse_user_input():
    user_input = winput("Whittler > ")
    if not user_input.strip():
        return None
    
    # Support strings with escaped quote characters
    user_input = user_input.replace("\\'","###_TRUFFLEHOG_SINGLE_QUOTE_###")
    user_input = user_input.replace("\\\"","###_TRUFFLEHOG_DOUBLE_QUOTE_###")

    # For now, just treat single and double quotes identically.
    user_input = user_input.replace("'","\"")

    if user_input.find("\"") == -1:
        verb,*args = list(filter(None,user_input.split(" ")))
    else:
        if user_input.count("\"") % 2:
            wprint("Failed to parse quoted input.")
            return None
        quote_regions = user_input.split("\"")
        # Obviously we're not going to support nested quotes, so every other quote_region will be
        # a string contained by quotes. Ideally I should be using the shlex library for this but
        # I'm too lazy.
        all_args = []
        for i in range(len(quote_regions)):
            if not i%2:
                all_args.extend(list(filter(None,quote_regions[i].split(" "))))
            else:
                all_args.append(quote_regions[i])
        verb,*args = all_args
    try:
        redirect_to_file_index = args.index(">")
        if redirect_to_file_index != len(args)-2:
            wprint("Specify only a single file to which to redirect command output! (Maybe try absolute paths; quotes are supported.)")
            return None
        redirect = args[-1]
        args = args[:-2]
    except ValueError:
        redirect = None
    
    for i in range(len(args)):
        args[i] = args[i].replace("###_TRUFFLEHOG_SINGLE_QUOTE_###","\\'")
        args[i] = args[i].replace("###_TRUFFLEHOG_DOUBLE_QUOTE_###","\\\"")
    return (verb,args,redirect)

irrelevance_filters = []
def play_elimination_game(resultdb, obj):
    global irrelevance_filters
    game_actions = {
        1 : "mark as relevant",
        2 : "mark as irrelevant",
        3 : "mark as ambiguous",
        4 : "quit game",
        5 : "clear relevancy filters"
    }
    def filterfunc(result):
        for attr, value in irrelevance_filters:
            if result[attr].strip() == value.strip():
                return False
        return True
    while True:
        results = list(filter(filterfunc, obj.all_result_objects()))
        if not len(results):
            wprint("All results accounted for - Game Over :)")
            break
        random_result = random.choice(results)
        wprint("\n".join(["| "+line for line in random_result.show_view()[0].splitlines()]))
        question = ""
        for action_id, action_description in game_actions.items():
            question += f" {action_id} : {action_description}\n"
        question += "\naction? "
        answer = winput(question)
        try:
            answer = int(answer)
            if not answer in game_actions.keys():
                wprint("Unrecognized choice.")
                continue
        except:
            wprint("\n > Failed to parse action.")
            continue
        if answer == 4:
            wprint("\n > Ending game, thanks for playing.")
            break
        elif answer == 3:
            wprint("\n > OK, taking no action.")
            continue
        elif answer == 1:
            wprint()
            relevant_attr = select_attribute(resultdb, "Which specific value makes this result definitely relevant? ")
            irrelevance_filters.append((relevant_attr,random_result[relevant_attr]))
            wprint("OK, I'll ignore results with that value for that attribute for the rest of the game.")
            continue
        elif answer == 5:
            wprint("Currently, you have relevancy filters on the following attributes:")
            for attr, value in irrelevance_filters:
                wprint(attr)
            confirm = winput("Are you sure you want to clear these relevancy filters? (Y/n) ")
            if confirm.lower() == "n":
                irrelevance_filters = []
                wprint("Cleared.")
                continue
        # answer must be 2 (irrelevant) past this point.
        wprint("\n > OK, this result will be marked as irrelevant.\n")
        random_result.mark_irrelevant()
        num_results_eliminated = 1
        problematic_attr = select_attribute(resultdb, "Which attribute's value makes this result irrelevant? ")
        specific_or_general = winput("Should I create a group based on this value (Y)? Or is it this specific value that makes it irrelevant (n)? ")
        make_group = specific_or_general.lower() != "n"
        if not make_group:
            irrelevant_resultlist = resultdb.categorized_results[problematic_attr][random_result[problematic_attr]]
            num_results_eliminated = len(irrelevant_resultlist)
            irrelevant_resultlist.mark_irrelevant()
        else:
            group_ptr = group_interactive(resultdb, problematic_attr, random_result[problematic_attr])
            if group_ptr is None:
                continue
            irrelevant_resultdict = group_ptr.give_pointed_object()
            num_results_eliminated = len(irrelevant_resultdict.all_result_objects())
            irrelevant_resultdict.mark_irrelevant()
        excitement = num_results_eliminated//100
        report = f"\n > Eliminating {num_results_eliminated} results{'.' if not excitement else ''}{'!'*excitement}\n"
        if excitement >= 3:
            report = report.upper()
        wprint(report)
        time.sleep(excitement+1 if excitement < 3 else 3)

def main_loop(resultdb):
    global redirect_file, global_redirect_file
    while True:
        if not redirect_file is None:
            redirect_file.close()
            redirect_file = None
        resultdb.update_current_view()
        user_input = get_and_parse_user_input()
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
            wprint(resultdb.construct_view(limit=limit)[0])
            continue
        elif verb == "dig":
            ptr = get_ptr_from_id_arg(resultdb, args)
            if ptr is False:
                wprint("no [attr] specified, no digging performed.")
                continue
            if ptr is None:
                continue
            resultdb.navigate_view(ptr)
            continue
        elif verb == "up":
            if resultdb.current_pointer.is_base_pointer():
                wprint("Already at root context.\n")
                continue
            resultdb.current_pointer.go_up_level()
            # We want to pop out from the categorized_results or grouped_results contexts implicitly.
            if len(resultdb.current_pointer.path) == 1:
                resultdb.current_pointer.go_up_level()
            continue
        elif verb == "top":
            while not resultdb.current_pointer.is_base_pointer():
                resultdb.current_pointer.go_up_level()
            continue
        elif verb == "dump":
            ptr = resultdb.root_pointer.copy()
            ptr.access_property("results")
            wprint(resultdb.results.show_view()[0])
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
            quieted_attr = get_attrname_from_attribute_arg(resultdb, args, attr_arg_position=1)
            if quieted_attr is False:
                quieted_attr = select_attribute(resultdb, "Which attribute would you like to filter by? ")
            elif quieted_attr is None:
                continue
            ct = 0
            for result in resultdb.results:
                if filter_str.lower() in result[quieted_attr].lower():
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
        elif verb == "history":
            wprint()
            for cmd in command_history:
                wprint(cmd)
            wprint()
            continue
        elif verb == "export":
            if not len(args):
                wprint("Need a filename to export to.")
                continue
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
                with open(fname,"w+", encoding="utf-8") as f:
                    f.write(json.dumps(resultlist, indent=4))
                wprint("Export success.")
            except PermissionError:
                wprint("Failed to open the specified file, maybe try an absolute path? (FYI, quotes are supported.)")
            continue



        
        else:
            wprint("Unrecognized command.\n")
            continue

        
HOME_DIRECTORY = str(Path.home())
WHITTLER_DIRECTORY = HOME_DIRECTORY+"/.whittler"
if not os.path.isdir(WHITTLER_DIRECTORY):
    os.mkdir(WHITTLER_DIRECTORY,mode=0o770)

result_classes = {}
for fname in filter(lambda s: not s.startswith("__") , os.listdir(os.path.dirname(os.path.realpath(__file__))+"/modules")):
    module = importlib.import_module(f"modules.{fname[:fname.index('.')]}")
    for clsname in dir(module):
        if clsname.startswith("__"):
            continue
        cls = getattr(module, clsname)
        if isinstance(cls, type) and issubclass(cls, Result) and not cls is Result:
            result_classes[cls.FRIENDLY_NAME] = cls
            break

parser = argparse.ArgumentParser(description="An interactive script to whittle down false-positive trufflehog findings")
parser.add_argument('--config', help='the module to use to parse the specified tool output files.', type=str, nargs=1,
                                choices=list(result_classes.keys()), default=None)
parser.add_argument('--file', help='the tool output file to be parsed', type=str, nargs=1, default='')
parser.add_argument('--dir', help='the directory containing tool output files to be parsed', type=str, nargs=1, default='')
parser.add_argument('--log_output', help='a file to which all output in this session will be logged (default: a new file in the '+\
                                         '.whittler folder in your home directory)', type=str, nargs="?", default=None,
                                         const=WHITTLER_DIRECTORY+'/{date:%Y-%m-%d_%H-%M-%S}_log.txt'.format( date=datetime.datetime.now() ))
parser.add_argument('--log_command_history', help='a file in which to record the command history of this session (default: a new file in the '+\
                                                  '.whittler folder in your home directory)', type=str, nargs="?", default=None,
                                                  const=WHITTLER_DIRECTORY+'/{date:%Y-%m-%d_%H-%M-%S}_command_log.txt'.format( date=datetime.datetime.now() ))
parser.add_argument('--import_whittler_output', help='consume and continue working with a file that was outputted by Whittler\'s "export" command"',
                                                 type=str, nargs=1, default=None)

if __name__ == "__main__":
    args = parser.parse_args()
    if not args.log_output is None:
        logdir = args.log_output[0] if isinstance(args.log_output,list) else args.log_output
        try:
            global_redirect_file = open(logdir,"w+", encoding="utf-8")
        except PermissionError:
            print("Lacking permissions to write to the specified all-output log file.")
            sys.exit(1)
        global_redirect_file.write(" ".join(sys.argv)+"\n\n")
    if not args.log_command_history is None:
        logcmddir = args.log_command_history[0] if isinstance(args.log_command_history,list) else args.log_command_history
        try:
            command_redirect_file = open(logcmddir,"w+", encoding="utf-8")
        except PermissionError:
            print("Lacking permissions to write to the specified command history log file.")
            sys.exit(1)
    try:
        resultdb = ResultDatabase(result_classes[args.config[0]])
        if not args.dir and not args.file and not args.import_whittler_output:
            parser.print_help()
            sys.exit(1)
        wprint("\nWelcome to the Whittler shell. Type \"help\" for a list of commands.\n")
        wprint("Parsing provided files...")
        wprint()
        if args.dir:
            resultdb.parse_from_directory(args.dir[0])
        if args.file:
            resultdb.parse_from_file(args.file[0])
        if args.import_whittler_output:
            resultdb.parse_from_export(args.import_whittler_output[0])
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
        

