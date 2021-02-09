from classes.NestedObjectPointer import NestedObjectPointer
from config import Config
import textwrap
import random


actions = {
    "navigation" : {
        "show [[limit]]" : "Show the current data context, up to [limit] entries (shows all entries by default). Mutes "+\
                           "results or table entries with 0 relevant results.",
        "showall [[limit]]" : "Show the current data context, up to [limit] entries (shows all entries by default). Includes "+\
                              "results or table entries with 0 relevant results.",
        "dig [attr]" : "Dig into a specific data grouping category, either by attribute name, or by attribute id",
        "up" : "Dig up a level into the broader data grouping category",
        "top" : "Dig up to the top level",
        "dump [[limit]]" : "Display every relevant result in every category, up to [limit] entries (shows all by default)",
        "dumpall [[limit]]" : "Display every result, both relevant and irrelevant, in every category, up to [limit] entries "+\
                              "(shows all by default)",
        #"search [searchstr]" : "Finds the thing", # todo
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
        "sort [colname]" : "Sorts the displayed results by the value in the specified column. Use quotes if the column name "+\
                           "has a space in it.",
        "sortn [colname]" : "Sorts the displayed results numerically by the value in the specified column. Use quotes if the "+\
                            "column name has a space in it.",
        "rsort [colname]" : "Reverse-sorts the displayed results by the value in the specified column. Use quotes if the column name "+\
                            "has a space in it.",
        "rsortn [colname]" : "Reverse-sorts the displayed results numerically by the value in the specified column. Use quotes if the "+\
                             "column name has a space in it.",
        "history" : "Print all commands that have been run in this session so far",
        "export [fname] [[id]]" : "Export all relevant results in JSON form at into the file [fname]. Optionally, limit "+\
                                  "the output to the result set as referenced by [id]."
    }
}

# A simple history of the commands that have been run in the Whittler shell.
command_history = []

# The file to which the command history will be written, if any. By default, a .txt file named after
# the current date and time, placed in the .whittler directory in the user's home folder.
command_redirect_file = None
def set_command_redirect_file(obj):
    global command_redirect_file
    command_redirect_file = obj
def get_command_redirect_file():
    return command_redirect_file

# The file to which all Whittler output will be written, if any. By default, a .txt file named after
# the current date and time, placed in the .whittler directory in the user's home folder.
global_redirect_file = None
def set_global_redirect_file(obj):
    global global_redirect_file
    global_redirect_file = obj
def get_global_redirect_file():
    return global_redirect_file

# The file to which the output of the specified command will be written. This adds support for shell-
# style redirection, e.g. "showall > ./my_file.txt"
redirect_file = None
def set_redirect_file(obj):
    global redirect_file
    redirect_file = obj
def get_redirect_file():
    return redirect_file


class _NoInput:
    pass
def wprint(s=_NoInput,end="\n"):
    if s is _NoInput:
        s = ""
    if not redirect_file is None:
        redirect_file.write(str(s)+end)
    if not global_redirect_file is None:
        global_redirect_file.write(str(s)+end)
    print(s,end=end)

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
    wprint("NOTE: This shell supports quoted arguments and redirecting command output to a file using the \">\" operator.")
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
    try:
        index = int(winput(msg))
    except ValueError:
        return None
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
        wprint(f"I found {len(similar_results)} similar results with \"{groupattr}\" values as shown above.")
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
        wprint("Created result group based on this entry. You can view this group in the \"groups\" pane in the top context.")
        ptr = NestedObjectPointer(resultdb)
        ptr.access_property("grouped_results")
        ptr.get_by_index(groupval)
        return ptr

def parse_user_input(user_input):
    if not user_input.strip():
        return None
    
    # Support strings with escaped quote characters
    user_input = user_input.replace("\\'","###_TRUFFLEHOG_SINGLE_QUOTE_###")
    user_input = user_input.replace("\\\"","###_TRUFFLEHOG_DOUBLE_QUOTE_###")

    # Support multiple commands in a single line with semicolons, but also ignore escaped semicolons
    user_input = user_input.replace("\\;","__WHITTLER_SEMICOLON_ESCAPE_W89UHA938F__")

    inputs = [cmd.strip().replace("__WHITTLER_SEMICOLON_ESCAPE_W89UHA938F__",";") for cmd in user_input.split(";")]

    ret = []
    for inp in inputs:
        # For now, just treat single and double quotes identically.
        inp = inp.replace("'","\"")

        if not inp.strip():
            continue

        if inp.find("\"") == -1:
            verb,*args = list(filter(None,inp.split(" ")))
        else:
            if inp.count("\"") % 2:
                wprint("Failed to parse quoted input.")
                return None
            quote_regions = inp.split("\"")
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
        ret.append((verb,args,redirect))
    return ret

irrelevance_filters = []
already_marked_relevant = []
def play_elimination_game(resultdb, obj):
    global irrelevance_filters
    global already_marked_relevant
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
                wprint("Unrecognized selection.")
                continue
        except ValueError:
            wprint("Unrecognized selection.")
            continue
        if answer == 4:
            wprint("\nEnding game, thanks for playing.")
            break
        elif answer == 3:
            wprint("\nOK, taking no action.")
            continue
        elif answer == 1:
            wprint("\nOK, taking no action.")
            continue # todo
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
        wprint("\nOK, this result will be marked as irrelevant.\n")
        random_result.mark_irrelevant()
        num_results_eliminated = 1
        wprint("I can try to find other results similar to this one through various heuristics, and mark them irrelevant as well.\n")

        search_actions = {
            1 : "contains this specific value",
            2 : "contains a substring of this value (case-insensitive)",
            3 : "loosely resembles this value (fuzzy string matching)",
            4 : "never mind"
        }
        initial_str = "OK. To start, which"
        again_str = "Search for similar results? (y/N) "
        while True:
            go_again = winput(again_str)
            if go_again is None:
                wprint("Unrecognized input.")
                continue
            again_str = "Search again? (y/N)"
            if not go_again.strip() or go_again.lower() != "y":
                break
            wprint()
            wprint("\n".join(["| "+line for line in random_result.show_view()[0].splitlines()]))
            wprint()
            problematic_attr = select_attribute(resultdb, f"{initial_str} attribute's value makes this result irrelevant? ")
            initial_str = "Which"
            if not problematic_attr:
                wprint("Unrecognized selection.")
                continue
            wprint(f"\n\nFor reference, here is the value of the \"{problematic_attr}\" attribute for this result:")
            wprint("_"*Config.MAX_OUTPUT_WIDTH)
            wprint(random_result[problematic_attr])
            wprint("^"*Config.MAX_OUTPUT_WIDTH)

            question = f"\nI can search for results where the \"{problematic_attr}\" attribute:\n"
            for action_id, action_description in search_actions.items():
                question += f" {action_id} : {action_description.format(problematic_attr)}\n"
            question += "\naction? "
            answer = winput(question)
            try:
                answer = int(answer)
                if not answer in search_actions.keys():
                    wprint("Unrecognized selection.")
                    continue
            except ValueError:
                wprint("Unrecognized selection.")
                continue
            generate_report = True
            if answer == 1:
                irrelevant_resultlist = resultdb.categorized_results[problematic_attr][random_result[problematic_attr]]
                num_results_eliminated = len(irrelevant_resultlist)
                irrelevant_resultlist.mark_irrelevant()
            elif answer == 2:
                substring = winput("What is the substring you would like to filter by? ")
                if substring.lower() not in random_result[problematic_attr].lower():
                    wprint(f"Sorry, that is not a case-insensitive substring of this result's \"{problematic_attr}\" attribute...")
                    continue
                irrelevant_resultlist = resultdb.categorized_results[problematic_attr][random_result[problematic_attr]]
                for result in resultdb.results:
                    if substring.lower() in result[problematic_attr].lower():
                        result.mark_irrelevant()
                        num_results_eliminated += 1
            elif answer == 3:
                group_ptr = group_interactive(resultdb, problematic_attr, random_result[problematic_attr])
                if group_ptr is None:
                    continue
                irrelevant_resultdict = group_ptr.give_pointed_object()
                num_results_eliminated = len(irrelevant_resultdict.all_result_objects())
                irrelevant_resultdict.mark_irrelevant()
            elif answer == 4:
                generate_report = False
            
            if generate_report:
                excitement = num_results_eliminated//100
                report = f"\n > Eliminating {num_results_eliminated} results{'.' if not excitement else ''}{'!'*excitement}\n"
                if excitement >= 3:
                    report = report.upper()
                wprint(report)
