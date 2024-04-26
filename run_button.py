import re
from obtain_info import CPax

def separate_pr(txt_file_path):
    txtObj = open(txt_file_path,'rt')
    txtContent = txtObj.read()
    txtObj.close()

    #Seperate text using splitor "PR:".
    prFields = txtContent.split("PR: ")
    index = 0
    effective_pattern = re.compile(r"1[.]\s")
    pr_pattern = re.compile(r"PR:\s")
    orgnaized_prs = []
    for pr in prFields:
        if effective_pattern.search(pr): # if the info has a name, that is valid.
            orgnaized_prs.append(pr)
        else:
            if pr_pattern.search(pr): 
                # if the info without a name but has the command, 
                # it shall continue with the last item.
                origin = orgnaized_prs[-1]
                orgnaized_prs[-1] = origin + pr

    return orgnaized_prs

def loop_obtain_info(orgnaized_prs):
    error_msg=[]
    debug_msg=[]
    for pax in orgnaized_prs:
        pax_func=CPax(pax)
        error_msg.extend(pax_func.error_msg)
        debug_msg.extend(pax_func.debug_msg)
    return error_msg, debug_msg

