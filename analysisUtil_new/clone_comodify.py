import builtins
import json
import re
from git import *
import os
from util.module_utl import sort_module
from util.read_clone import read_clone_block
from util.read_commit import find_line_index
from util.write_in_xsl import result_out
# 分析指定仓库中指定版本跨度的共同修改克隆


def get_file_path(pattern, diff, pre):
    result = re.findall(pattern, diff)
    if not len(result) > 0:
        return None
    result = result[0]
    if pre not in result:
        return None
    file_path = result[result.find(pre)+2:].replace(".cc", ".cpp")
    return file_path


def extract_clone_block(clone_list, change_start, change_end):  # 抓取当前差异位置中涉及的克隆片段信息
    involve_clone = []  # 该位置上包含的克隆片段
    clone_list = sorted(clone_list, key=lambda x: x['startLineNumber'])  # 将需要比对的克隆片段按照开始行号升序排列
    for clone in clone_list:
        endLineNumber = clone["endLineNumber"]  # 获取克隆片段的结束行号
        startLineNumber = clone["startLineNumber"]  # 获取克隆片段的开始行号
        fingerprint = clone['fingerprint']  # 获取当前克隆的id
        if startLineNumber > change_end:  # 如果克隆片段的开始行号已经超过了差异位置的结束行号，那么后续的克隆片段也不会与该差异位置产生交集，直接退出
            break
        if change_start > endLineNumber or change_end < startLineNumber:  # 如果当前克隆片段与差异位置没有交集就跳过
            continue
        if not [startLineNumber, endLineNumber, fingerprint] in involve_clone:
            involve_clone.append([startLineNumber, endLineNumber, fingerprint])
        else:  # 如果当前产生交集的克隆片段已经存入直接跳过，对比下一个片段
            continue
    return involve_clone


def judge_intersection(sourcefile, post_sourcefile, line_index_list, pre_clone_list,
                       post_clone_list, comodify_result):
    for line_index in line_index_list:
        start = line_index['start']
        end = line_index['end']  # 更改前的开始行号和结束行号
        pre_clone_involve = extract_clone_block(pre_clone_list, start, end)
        # 得到更改前的代码片段上涉及的克隆片段
        if not len(pre_clone_involve) > 0:  # 如果当前修改位置上没有涉及前一个版本的克隆片段，直接跳过
            continue
        new_start = line_index['new_start']
        new_end = line_index['new_end']  # 更改后的开始行号和结束行号
        post_clone_involve = extract_clone_block(post_clone_list, new_start, new_end)
        # 得到更改后的代码片段上涉及的克隆片段
        min_length = min(len(pre_clone_involve), len(post_clone_involve))
        # 取两个克隆片段列表中较小的长度，避免过界
        for i in builtins.range(min_length):
            fingerprint = pre_clone_involve[i][2]  # 获取克隆id
            startLineNumber = pre_clone_involve[i][0]  # 获取克隆更改前的开始行号
            endLineNumber = pre_clone_involve[i][1]  # 获取克隆更改前的结束行号
            post_startLineNumber = post_clone_involve[i][0]  # 获取克隆更改后的开始行号
            post_endLineNumber = post_clone_involve[i][1]  # 获取克隆更改后的结束行号
            if not comodify_result.get(fingerprint):
                comodify_result[fingerprint] = []
                # 如果没有当前序号对应的克隆信息就创建一个新列表用于存储结果
            comodify_result.get(fingerprint).append({'sourcefile': sourcefile,
                                                     # 更改前的文件名
                                                     'startLineNumber': startLineNumber,
                                                     # 更改前的开始行号
                                                     'endLineNumber': endLineNumber,
                                                     # 更改前的结束行号
                                                     'post_sourcefile': post_sourcefile,
                                                     # 更改后的文件路径
                                                     'post_start': post_startLineNumber,
                                                     # 更改后的开始行号
                                                     'post_end': post_endLineNumber,
                                                     # 更改后的结束行号
                                                     'change_start': start if start > startLineNumber else startLineNumber,
                                                     # 更改开始行号
                                                     'change_end': end if end < endLineNumber else endLineNumber,
                                                     # 更改结束行号
                                                     })  # 存储命中的克隆块的信息
    return comodify_result


def process_diff(diff, pre_clone_dic, post_clone_dic, commodify_result):
    pre_file = get_file_path("[-][-][-] (.*)", diff, "a/")
    if pre_file is None or pre_file not in list(pre_clone_dic.keys()):
        return commodify_result
    post_file = get_file_path("[+][+][+] (.*)", diff, "b/")
    if post_file is None or post_file not in list(post_clone_dic.keys()):
        return commodify_result
    line_index_list = find_line_index(diff)
    commodify_result = judge_intersection(pre_file, post_file,
                                          line_index_list,
                                          pre_clone_dic[pre_file],
                                          post_clone_dic[post_file],
                                          commodify_result)
    return commodify_result


def sort_count(L):  # 将列表中元素去重然后计数
    M = []
    for i in range(len(L)):
        n = L[i].copy()
        # n["count"] = L.count(L[i])
        if n not in M:
            M.append(n)
    return M


def refactor_code(tags, tag_range, xml_path, project_name, file_extensions):
    for tag in tags:
        print("-----------------------------------------------------------------------------------")
        print("当前检测的初始版本为:" + tag)
        if len(tags) - tags.index(tag) < tag_range:  # 如果剩下的tag不足够设定的版本跨度，直接退出
            break
        clone_exist = True
        for cpm_tag in tags[tags.index(tag) + 1:tags.index(tag) + tag_range]:
            if not os.path.exists(os.path.join(xml_path, project_name + "/" + project_name + "-" + cpm_tag + ".xml")):
                clone_exist = False
        if not clone_exist:  # 如果对比的版本的克隆文件不存在直接跳过
            continue
        comodify_result = {}  # 存储共同修改的结果
        pre_sourcefile = os.path.join(xml_path, project_name + "/" + project_name + "-" + tag + ".xml")  # 前一个版本的克隆结果路径
        pre_clone_dic = read_clone_block(pre_sourcefile)
        print("已读取初始版本" + tag + "的克隆结果")
        for cpm_tag in tags[tags.index(tag) + 1:tags.index(tag) + tag_range]:
            args = [tag, cpm_tag, '--']
            args.extend(["*/*.{}".format(ext) for ext in file_extensions])
            diff_list = repo.git.diff(*args).split('diff')  # 得到指定后缀名的文件diff
            # pdb.set_trace()
            print("已得到版本" + tag + "与版本" + cpm_tag + "之间的diff")
            # 两个版本之间的文件差异
            post_sourcefile = os.path.join(xml_path, project_name + "/" + project_name + "-" + cpm_tag + ".xml")
            # 后一个版本的克隆结果路径
            post_clone_dic = read_clone_block(post_sourcefile)
            print("已得到版本" + cpm_tag + "的克隆结果")
            # 读取两个版本的克隆结果
            for diff in diff_list:  # 遍历差异结果
                comodify_result = process_diff(diff, pre_clone_dic, post_clone_dic, comodify_result)
        print("完成对初始版本" + tag + "与指定版本的共同修改检测")
        change_comidify_results = {}  # 用于给共变克隆上的修改行计数
        for index in list(comodify_result.keys()):
            pre_clone = set()
            post_clone = set()  # 使用集合进行去重
            for result in comodify_result[index]:
                pre_clone.add((result['sourcefile'], result['startLineNumber'], result['endLineNumber']))
                post_clone.add((result['post_start'], result['post_end']))

            if len(pre_clone) <= 1 or len(post_clone) <= 1:
                del comodify_result[index]  # 如果该克隆类内的克隆片段不超过两个，直接筛去
                continue

            comodify_result[index] = sort_count(comodify_result[index])  # 将克隆对函数信息去重并计数
            if len(comodify_result[index]) <= 1:  # 如果去重后的克隆对内对应的克隆片段不超过1条则直接删除，保留的即为共同修改的结果
                del comodify_result[index]
                continue

            # 将克隆的更改数据提取出来处理
            if not change_comidify_results.get(index):
                change_comidify_results[index] = []
            for clone in comodify_result[index]:
                change_comidify_results[index].append(
                    {'startLineNumber': clone['change_start'], 'endLineNumber': clone['change_end'],
                     'sourcefile': clone['sourcefile']})
        print("已获得共同修改克隆片段的修改信息")
        module_result = sort_module(comodify_result)  # 对所得结果的代码行数以及模块分布情况进行统计
        change_modify_result = sort_module(change_comidify_results)  # 统计更改代码片段的代码行数以及分布情况
        print("已完成对共同修改结果的行数统计以及模块分布统计")
        module_result['change_cross_dup_line'] = change_modify_result['cross_dup_line']
        module_result['change_line'] = change_modify_result['dup_line']
        module_result['change_dup_module'] = change_modify_result['dup_module']
        ver = project_name + "-" + tag + "-" + tags[tags.index(tag) + 4]
        new_dict = {'ver': ver}  # 创建一个新的字典
        new_dict.update(module_result)  # 将原始字典的元素添加到新字典中
        all_commodify_results.append(new_dict)
        with open(os.path.join("../json/comodify", ver + "_comodify.json"), "w", encoding='utf-8') as f:
            f.write(json.dumps(comodify_result, ensure_ascii=False, indent=4))
        print("已完成对初始版本" + tag + "的共同修改检测，结果正在保存...")
        print("-----------------------------------------------------------------------------------")


if __name__ == "__main__":
    # repo_name = "/home/clone/apollo"  # 需要进行检测的仓库名称
    repo_name = input("Input your repo path:")
    project_name = os.path.basename(repo_name)
    repo = Repo(repo_name)  # 获取git仓库
    tags = [tag.name for tag in sorted(repo.tags, key=lambda t: t.commit.committed_datetime)]  # 版本号按照时间排序
    all_commodify_results = []  # 存储该项目检测到所有的共同修改的结果
    # tag_range = 5  # 需要进行对比的版本跨度
    tag_range = input("Input your tag range:")
    file_extensions = ['cc', 'h', 'cpp']  # 需要进行分析的文件后缀
    xml_path = os.path.join(os.getcwd(), "clone-xml")  # 代码克隆检测结果所在的文件路径
    save_path = os.path.join(os.getcwd(), 'results')  # 结果保存的文件路径
    print("当前检测的仓库名为:" + repo_name + " tag数量为:" + str(len(tags)) + " 检测的tag跨度为:" + str(tag_range) + " 检测的文件后缀为:" + ' '.join(file_extensions))
    # 进行共同修改检测
    refactor_code(tags, tag_range, xml_path, project_name, file_extensions)
    print("已完成项目所有tag的共同修改检测，结果正在保存....")
    save_name = os.path.join(save_path, project_name + '_comodify_dup_results.xlsx')
    result_out(save_name, all_commodify_results)  # 将得到的结果保存到excel表中
    print("共同修改检测结束！")