import collections
from git import *
import re
from pydriller import git
import datetime
from analysisUtil_new.clone_comodify import extract_clone_block
from util.module_utl import merge_line, calculate_cross_line_count
from util.read_clone import read_clone_block, get_module_name
from util.read_commit import find_line_index
from util.write_in_xsl import result_out


def sort_module_bug_induce(result):  # 统计错误倾向克隆涉及的模块情况
    dup_total_line_count = 0
    file_dup = collections.defaultdict(list)
    module_name_dic = collections.defaultdict(
        lambda: {'count': 0, 'line': 0, 'commit_index': set(), 'fix_time': datetime.timedelta(seconds=0)})
    cross_results = []
    cross_dup_list = []

    for index, clone_info_list in result.items():
        module_name_set = set()
        cross_dup = []
        for clone_info in clone_info_list:
            sourcefile = clone_info['sourcefile']
            startLineNumber = int(clone_info.get("startLineNumber"))
            endLineNumber = int(clone_info.get("endLineNumber"))
            cross_dup.append({'sourcefile': sourcefile, 'start': startLineNumber, 'end': endLineNumber})
            file_dup[sourcefile].append({'start': startLineNumber, 'end': endLineNumber})
            moduleName = get_module_name(sourcefile)
            module_name_set.add(moduleName)
            if clone_info['commit_index'] not in module_name_dic[moduleName]['commit_index']:
                module_name_dic[moduleName]['commit_index'].add(clone_info['commit_index'])
                module_name_dic[moduleName]['fix_time'] += datetime.timedelta(
                    days=int(clone_info['fix_time'].split(',')[0]), seconds=int(clone_info['fix_time'].split(',')[1]))
                module_name_dic[moduleName]['fix_time'] /= len(module_name_dic[moduleName]['commit_index'])
            file_dup[sourcefile] = merge_line(file_dup[sourcefile])
        module_name_list = sorted(list(module_name_set))
        for moduleName in module_name_list:
            module_name_dic[moduleName]['count'] += 1
        if len(module_name_list) > 1:
            cross_results.append(','.join(module_name_list))
            cross_dup_list.extend(cross_dup)

    for sourcefile, index_list in file_dup.items():
        moduleName = get_module_name(sourcefile)
        for index in index_list:
            line_count = index['end'] - index['start'] + 1
            module_name_dic[moduleName]['line'] += line_count
            dup_total_line_count += line_count
    cross_line_count = calculate_cross_line_count(cross_dup_list)
    cross_dup_count = len(cross_results)
    cross_results = dict(collections.Counter(cross_results))

    for value in module_name_dic.values():
        value['fix_time'] = str(value['fix_time'])
        del value['commit_index']

    return {'dup_module': module_name_dic,
            'module_count': len(module_name_dic),
            'bug_line': dup_total_line_count,
            'cross_dup_count': cross_dup_count,
            'cross_results': cross_results,
            'cross_line_count': cross_line_count,
            }


def check_intersection(pre_file, pre_clone_list, post_line_index_list, line_index_list):
    bug_clone_list = []  # 用于存储与该提交相关的克隆片段信息
    for line_index in line_index_list:
        start, end = line_index['start'], line_index['end']  # 更改前的开始行号和结束行号
        clone_involve = extract_clone_block(pre_clone_list, start, end)  # 得到更改前的代码片段上涉及的克隆片段
        if not clone_involve:  # 如果当前修改位置上没有涉及前一个版本的克隆片段，直接跳过
            continue
        new_start, new_end = line_index['new_start'], line_index['new_end']  # 获得更改之后的开始行号和结束行号
        inter_flag = any(not (new_start > post_index['new_end'] or new_end < post_index['new_start']) for post_index in post_line_index_list)
        if inter_flag:
            bug_clone_list.extend({'fingerprint': clone[2],
                                   'sourcefile': pre_file,
                                   'startLineNumber': clone[0],
                                   'endLineNumber': clone[1],
                                   } for clone in clone_involve)
    return bug_clone_list


def extract_diff(diff_list, pre_clone_dic, commit_modified_files):
    # 抓取造成tag与当前提交差异的补丁片段，并且抓取与该补丁相关的克隆片段
    bug_clone_result = []
    for diff in diff_list:
        pre_file = re.findall("[-][-][-] a/(.*)", diff)
        post_file = re.findall("[+][+][+] b/(.*)", diff)
        if not pre_file or not post_file or pre_file[0] not in pre_clone_dic or post_file[0] not in commit_modified_files:
            continue
        pre_file, post_file = pre_file[0], post_file[0]
        line_index_list = find_line_index(diff)
        post_line_index_list = [find_line_index(modified_file) for modified_file in commit_modified_files[post_file]]
        clone_result = check_intersection(pre_file, pre_clone_dic[pre_file], post_line_index_list, line_index_list)
        bug_clone_result.extend(clone_result)
    return bug_clone_result


def extract_cloned_fix_commit(tag, commit_id, repo, pre_clone_dic, file_extensions):
    # 判断当前提交是否与指定版本中的克隆相关，输出相关的克隆信息
    args = [tag, commit_id, '--']
    args.extend(["*/*.{}".format(ext) for ext in file_extensions])
    diff_list = repo.git.diff(*args).split('diff')
    commit_modified_files = {}
    for x in gr.get_commit(commit_id).modified_files:
        commit_modified_files.setdefault(x.new_path, []).append(x.diff)
    # 得到该提交的修改前文件路径，修改后的文件路径以及提交前后的源代码差异
    bug_clone_result = extract_diff(diff_list, pre_clone_dic, commit_modified_files)
    # 得到与该提交相关的克隆片段信息
    bug_clone_commit = (len(bug_clone_result) > 0)  # 该提交是否与克隆相关的标志
    return bug_clone_result, bug_clone_commit


def extract_commit_info(repo, tag0, tag1):  # 得到两个版本之间所有的提交信息
    logs = repo.git.log(tag0 + '..' + tag1)  # 得到两个版本之间的所有提交
    pattern = r"commit (\w+)\nAuthor: (.*)\nDate:   (.*)\n\n    (.*)"
    matches = re.findall(pattern, logs)  # 匹配出提交的ID,DATE,AUTHOR和Content

    commits = []
    for match in matches:
        commit = {
            "Commit ID": match[0],
            "Author": match[1],
            "Date": match[2],
            "Content": match[3]
        }
        commits.append(commit)

    return commits


def get_bug_commits(repo, tag0, tag1, corrective_word_list):
    # 获取指定版本跨度内的所有的错误修复提交以及所有的提交个数
    bug_commit = []
    sum_commit_count = 0
    for commit in extract_commit_info(repo, tag0, tag1):
        sum_commit_count += 1
        commit_id = commit["Commit ID"]
        commit_msg = commit["Content"]
        if any(word.lower() in commit_msg.lower() for word in corrective_word_list):
            bug_commit.append(commit_id)
    return bug_commit, sum_commit_count


def calculate_fix_time(commit_id, buggy_commits):
    commit_date = gr.get_commit(commit_id).committer_date
    commit_fix_time = datetime.timedelta(seconds=0)
    alter_commit_count = 0
    for modified_commit_id_list in list(buggy_commits.values()):
        alter_commit = len(modified_commit_id_list)
        alter_commit_count += alter_commit
        for modified_commit_id in modified_commit_id_list:
            commit_alter = gr.get_commit(modified_commit_id)
            commit_alter_date = commit_alter.committer_date
            fix_time = commit_date - commit_alter_date
            commit_fix_time += fix_time
    if alter_commit_count != 0:
        commit_fix_time /= alter_commit_count
    return commit_fix_time


def n_version_process(tags, repo, project_name):
    all_results = []
    corrective_word_list = ['bug', 'fix', 'wrong', 'error', 'fail', 'problem', 'patch', 'correct']
    for tag0 in tags:
        print("开始进行版本" + tag0 + "的克隆错误倾向分析")
        tag1 = tags[tags.index(tag0) + tag_range - 1]  # 得到需要分析的最后一个版本的版本号
        pre_sourcefile = os.path.join(clone_path, repo_name.split('/')[-1] + "/" + repo_name.split('/')[-1] + "-" + tag0 + ".xml")
        # 初始版本的克隆信息文件路径
        pre_clone_dic = read_clone_block(pre_sourcefile)
        print("已读取版本" + tag0 + "的克隆结果")
        # 读取初始版本的克隆信息
        bug_commit, sum_commit_count = get_bug_commits(repo, tag0, tag1, corrective_word_list)
        print(
            "已完成错误修复提交的筛选, 提交总数为:" + str(sum_commit_count) + " 错误提交数量为:" + str(len(bug_commit)))
        # 获取错误修复提交，计算提交总数
        clone_bug_fix_time = datetime.timedelta(seconds=0)  # 克隆相关的平均修复时间
        no_clone_bug_fix_time = datetime.timedelta(seconds=0)   # 克隆无关的平均修复时间
        bug_inducing_result = {}  # 与错误相关的克隆信息
        for commit_id in bug_commit:
            bug_clone_result, bug_clone_commit = extract_cloned_fix_commit(tag0, commit_id, repo, pre_clone_dic, file_extensions)
            # 判断当前提交是否与克隆相关，得到所有相关的克隆片段信息
            buggy_commits = gr.get_commits_last_modified_lines(gr.get_commit(commit_id))
            # 获取所有最后接触到当前提交种修改行的提交
            commit_fix_time = calculate_fix_time(commit_id, buggy_commits)
            # 计算平均修复时间
            if bug_clone_commit:
                clone_bug_fix_time += commit_fix_time
            else:
                no_clone_bug_fix_time += commit_fix_time
            # 根据该提交是否与克隆相关，将其平均修复时间加至相应的时间
            for bug_clone in bug_clone_result:
                if not bug_inducing_result.get(bug_clone['fingerprint']):
                    bug_inducing_result[bug_clone['fingerprint']] = []
                bug_inducing_result[bug_clone['fingerprint']].append({
                    'sourcefile': bug_clone['sourcefile'],
                    'startLineNumber': bug_clone['startLineNumber'],
                    'endLineNumber': bug_clone['endLineNumber'],
                    'commit_index': commit_id,
                    'fix_time': (','.join([str(commit_fix_time.days), str(commit_fix_time.seconds)])),
                })
            # 将该提交相关的克隆信息存储
        clone_bug_fix_time /= len(bug_commit)
        no_clone_bug_fix_time /= len(bug_commit)
        print("已抓取版本" + tag0 + "到版本" + tag1 + "之间与克隆相关的错误修复提交!")
        # 计算与克隆相关以以及无关的平均错误修复时间(每条commit的平均修复时间)
        bug_inducing_result = {k: v for k, v in bug_inducing_result.items() if len(v) > 1}
        print("已完成对版本" + tag0 + "的错误倾向克隆的去重!")
        # 去掉克隆组中包含的克隆片段不足2个的结果
        bug_module_result = sort_module_bug_induce(bug_inducing_result)
        # 按照模块分组统计
        bug_module_result.update({
            'bug_dup_count': len(bug_inducing_result),
            'clone_fix_time': str(clone_bug_fix_time),
            'no_clone_fix_time': str(no_clone_bug_fix_time),
            'sum_commit_count': sum_commit_count,
            'bug_commit_count': len(bug_commit),
            'ver': project_name + "-" + tag0 + "_" + tag1,
        })
        # 添加总结信息保存
        print("已完成版本" + project_name + " " + tag0 + "的错误倾向克隆的代码计算以及模块分布的统计!正在保存结果......")
        all_results.append(bug_module_result)
        # 保存到总结果中
    return all_results


if __name__ == "__main__":
    # repo_name = "/home/clone/apollo"  # 需要进行检测的仓库名称
    repo_name = input("Input your repo path:")
    project_name = os.path.basename(repo_name)
    repo = Repo(repo_name)  # 获取git仓库
    gr = git.Git(repo_name)  # 该对象用于抓取bug-inducing commit
    tags = [tag.name for tag in sorted(repo.tags, key=lambda t: t.commit.committed_datetime)]  # 版本号按照时间排序
    clone_path = os.path.join(os.getcwd(), "clone-xml")
    save_path = os.path.join(os.getcwd(), "results")
    # tag_range = 5  # 需要进行对比的版本跨度
    tag_range = input("Input your tag range:")
    # file_extensions = ['cc', 'cpp', 'h']
    file_extensions = input("Input extension of file you want to analysis: (like cpp, py)")
    print("当前检测的仓库名为:" + repo_name + " tag数量为:" + str(len(tags)) + " 检测的tag跨度为:" + str(tag_range))
    all_results = n_version_process(tags, repo, project_name)
    result_out(os.path.join(save_path, project_name + "_bug_induce_results.xlsx"), all_results)
    print("已完成对项目" + repo_name.split('/')[-1] + "的错误倾向克隆检测!")
