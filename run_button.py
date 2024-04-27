import re
from obtain_info import CPax
from general_func import find_a_miss
from concurrent.futures import ThreadPoolExecutor

def separate_pr(txt_file_path):
    txtObj = open(txt_file_path,'rt')
    txtContent = txtObj.read()
    txtObj.close()

    #Seperate text using splitor "PR:".
    prFields = txtContent.split("PR: ")
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

def handle_batch(batch):
    error_msg = []
    debug_msg = []
    prpd=[]
    pax_func = CPax(batch[0])  # Create a new instance of CPax for each batch
    for pr in batch:
        pax_func.run(pr)
        error_msg.extend(pax_func.error_msg)
        debug_msg.extend(pax_func.debug_msg)
        prpd.append(pax_func.PrPdNumber)
    return error_msg, debug_msg, prpd

#这种简单任务本来是不需要做多线程和线程池的。
#但是因为担心输入数据的异常会让主进程退出，所以不得不尝试多线程。
#所以虽然可以把batch_size提高到100，甚至200来减小线程创建开销。
#不过一旦出错，那就要复查那个数量的结果丢失了。有点不现实。
#同时也难得的及时销毁类。
def loop_obtain_info(orgnaized_prs, batch_size=5):
    error_msgs = []
    debug_msgs = []
    prpd_list=[]
    with ThreadPoolExecutor() as executor:
        batches = [orgnaized_prs[i:i+batch_size] for i in range(0, len(orgnaized_prs), batch_size)]
        futures = [executor.submit(handle_batch, batch) for batch in batches]
        for future in futures:
            error_msg, debug_msg, prpd = future.result()
            error_msgs.extend(error_msg)
            debug_msgs.extend(debug_msg)
            prpd_list.extend(prpd)
    prpd_missing=find_a_miss(prpd_list)
    return error_msgs, debug_msgs, prpd_missing

