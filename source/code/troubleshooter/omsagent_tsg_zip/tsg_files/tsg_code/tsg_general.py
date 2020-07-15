import os
import subprocess

from tsg_error_codes               import *
from tsg_errors                    import is_error, get_input, print_errors, err_summary
from install.tsg_install           import check_installation
from connect.tsg_connect           import check_connection
from heartbeat.tsg_heartbeat       import check_heartbeat
from high_cpu_mem.tsg_high_cpu_mem import check_high_cpu_memory
from syslog1.tsg_syslog            import check_syslog
from custom_logs.tsg_custom_logs   import check_custom_logs

logcollect_sh_path = "/opt/microsoft/omsagent/plugin/troubleshooter/tsg_code/log_collector/omslinux_agentlog.sh"

# check to make sure the user is running as root
def check_sudo():
    if (os.geteuid() != 0):
        print("The troubleshooter is not currently being run as root. In order to "\
              "have accurate results, we ask that you run this troubleshooter as root.\n"\
              "The OMS Agent Troubleshooter needs to be run as root for the following reasons:")
        print("  - getting workspace ID and other relevant information to debugging")
        print("  - checking files in folders with strict permissions")
        print("  - checking certifications exist / are correct")
        # TODO: add more reasons as troubleshooter changes
        print("NOTE: it will not add, modify, or delete any files without express permission.")
        print("Please try running the troubleshooter again with 'sudo'. Thank you!")
        return False
    else:
        return True



# run through all troubleshooting scenarios
def check_all(interactive):
    all_success = NO_ERROR
    # 1: Install
    checked_install = check_installation(interactive)
    if (is_error(checked_install)):
        return checked_install
    else:
        all_success = checked_install
    
    print("================================================================================")
    # 2: Connection
    checked_connection = check_connection(interactive)
    if (is_error(checked_connection)):
        return checked_connection
    else:
        all_success = checked_connection

    print("================================================================================")
    # 3: Heartbeat
    checked_hb = check_heartbeat(interactive)
    if (is_error(checked_hb)):
        return checked_hb
    else:
        all_success = checked_hb

    print("================================================================================")
    checked_highcpumem = check_high_cpu_memory(interactive)
    if (is_error(checked_highcpumem)):
        return checked_highcpumem
    else:
        all_success = checked_highcpumem

    print("================================================================================")
    checked_syslog = check_syslog(interactive)
    if (is_error(checked_syslog)):
        return checked_syslog
    else:
        all_success = checked_syslog

    print("================================================================================")
    checked_cl = check_custom_logs(interactive)
    if (is_error(checked_cl)):
        return checked_cl
    else:
        all_success = checked_cl

    return all_success




def collect_logs():
    # get SR number / company name
    print("Please input the SR number to collect OMS logs and (if applicable) the company\n"\
        "name for reference. (Leave field empty to skip)")
    sr_num = get_input("SR Number", (lambda x : True), "")
    com_name = get_input("Company Name", (lambda x : True), "")

    # create command to run
    logcollect_cmd = ['sudo', 'sh', logcollect_sh_path]
    if (sr_num != ''):
        logcollect_cmd = logcollect_cmd + ['-s', sr_num]
    if (com_name != ''):
        logcollect_cmd = logcollect_cmd + ['-c', com_name]

    # run command
    print("Starting up log collector...")
    print("--------------------------------------------------------------------------------")
    log_collection = subprocess.call(logcollect_cmd)
    if (log_collection != 0):
        print("--------------------------------------------------------------------------------")
        print("Log collector returned error code {0}. Please look through the above output to\n"\
            "find the reason for the error.".format(log_collection))
    return




def run_tsg():
    # check if running as sudo
    if (not check_sudo()):
        return

    print("Welcome to the OMS Agent for Linux Troubleshooter! What is your issue?\n"\
        "================================================================================\n"\
        "1: Agent is unhealthy or heartbeat data missing.\n"\
        "2: Agent doesn't start, can't connect to Log Analytic Services.\n"\
        "3: Syslog issue.\n"\
        "4: Agent consuming high CPU/memory.\n"\
        "5: Installation failures.\n"\
        "6: Custom logs issue.\n"\
        "================================================================================\n"\
        "A: Run through all scenarios.\n"\
        "L: Collect the logs for OMS Agent.\n"\
        "Q: Press 'Q' to quit.\n"\
        "================================================================================")
    switcher = {
        '1': check_heartbeat,
        '2': check_connection,
        '3': check_syslog,
        '4': check_high_cpu_memory,
        '5': check_installation,
        '6': check_custom_logs,
        'A': check_all
    }
    issue = get_input("Please select an option",\
                      (lambda x : x in ['1','2','3','4','5','6','q','quit','a','l']),\
                      "Please enter an integer corresponding with your issue (1-6) to\n"\
                        "continue (or 'A' to run through all scenarios), 'L' to run the log\n"\
                        "collector, or 'Q' to quit.")

    # quit troubleshooter
    if (issue.lower() in ['q','quit']):
        print("Exiting the troubleshooter...")
        return

    # collect logs
    if (issue.lower() == 'l'):
        print("Running the OMS Log Collector...")
        print("================================================================================")
        collect_logs()
        return

    # silent vs interactive mode
    print("--------------------------------------------------------------------------------")
    print("The troubleshooter can be run in two different modes.\n"\
          "  - Silent Mode runs through with no input required\n"\
          "  - Interactive Mode includes extra checks that require input")
    mode = get_input("Do you want to run the troubleshooter in silent (s) or interactive (i) mode?",\
                     (lambda x : x in ['s','silent','i','interactive']),\
                     "Please enter 's'/'silent' to run silent mode, 'i'/'interactive' to run \n\
                        interactive mode, or 'q'/'quit' to quit.")
    if (mode.lower() in ['q''quit']):
        print("Exiting the troubleshooter...")
        return
    elif (mode.lower() in ['s','silent']):
        print("Running troubleshooter in silent mode...")
        interactive_mode = False
    elif (mode.lower() in ['i','interactive']):
        print("Running troubleshooter in interactive mode...")
        interactive_mode = True

    # run troubleshooter
    section = switcher.get(issue.upper(), lambda: "Invalid input")
    print("================================================================================")
    success = section(interactive=interactive_mode)

    print("================================================================================")
    print("================================================================================")
    # print out all errors/warnings
    if (len(err_summary) > 0):
        print("ALL ERRORS/WARNINGS ENCOUNTERED:")
        for err in err_summary:
            print("  {0}".format(err))
        print("--------------------------------------------------------------------------------")
        
    # no errors found
    if (success == NO_ERROR):
        print("No errors were found.")
    # user requested to exit
    elif (success == USER_EXIT):
        return
    # error found
    else:
        print("Please review the errors found above.")
    # give information to user about next steps
    print("If you still have an issue, please run the troubleshooter again and collect the\n"\
        "logs for OMS.\n"\
        "In addition, please include the following information:\n"\
        "  - Azure Subscription ID where the Log Analytics Workspace is located\n"\
        "  - Workspace ID the agent has been onboarded to\n"\
        "  - Workspace Name\n"\
        "  - Region Workspace is located\n"\
        "  - Pricing Tier assigned to the Workspace\n"\
        "  - Linux Distribution on the VM\n"\
        "  - Log Analytics Agent Version")
    return
    

run_tsg()