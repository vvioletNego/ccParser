# 以block粒度的克隆信息进行错误倾向的检测(设定一个初始版本以后检测后面四个版本的提交中的克隆错误倾向，加入修复时间的统计)
import datetime
import difflib
import json
import os
import re
import chardet
from packaging import version
from util import read_commit, read_clone, write_in_xsl, module_utl

codes_file = {}  # 文件名对应的代码内容，避免重读
bug_induce_result_dic = {}  # 存储结果的字典
bug_commit_list = []  # 存储与克隆相关的提交
bug_fix_time = datetime.timedelta(seconds=0)  # 与克隆相关的提交的平均修复时间
all_bug_induce_result = []  # 检索的所有版本的结果
ver_num = 5


def parse_xml(commit_xml, clone_xml):  # 读取提交和克隆信息的xml文件存储到相应的字典中
    clone_block_dic = read_clone.read_clone_block(clone_xml)  # 读取block粒度的克隆文件
    commit_dic = read_commit.parse_commit_block_new(commit_xml)  # 读取提交的文件
    # 两者都以文件路径为字典的key，便于快速找出两者的共同文件路径
    return clone_block_dic, commit_dic


def detect(clone_block_dic, commit_dic):
    common_sourcefile = clone_block_dic.keys() & commit_dic.keys()  # 求出两者共有的文件路径
    for sourcefile in common_sourcefile:
        commit_list = commit_dic[sourcefile]  # 获取该文件路径对应的提交列表
        clone_list = clone_block_dic[sourcefile]  # 获取该文件路径对应的克隆信息列表
        for commit in commit_list:
            flag = False  # 该条提交是否与克隆相关
            line_index_list = commit['line_index_list']  # 获取当前提交的修改的行号
            old_content = commit['old_content']  # 获取当前提交修改前的文件内容
            fix_time = commit['fix_time']  # 获取当前提交的修复时间
            for clone in clone_list:
                clone_temp = clone.copy()  # 因为每次都要重新判断原始文件与提交前文件的差异，更改可能不依靠顺序，所以不能直接修改原来的克隆列表中信息
                old_sourcefile = clone_temp['old_sourcefile']  # 获取该文件在克隆检测时的文件路径
                if not old_sourcefile.replace("\\", "/").find(
                        '/'.join(commit['old_sourcefile'].replace(".cc", ".cpp").split('/')[-3:-1])) > -1:
                    continue  # 如果文件路径不对就跳过(为了能够检测到文件路径发生变化之后的对比后三级目录)
                if codes_file.get(old_sourcefile):
                    codes = codes_file[old_sourcefile]
                else:
                    codes = read_cpp(old_sourcefile)  # 读取克隆检测时的文件内容
                    codes_file[old_sourcefile] = codes
                change_index, diff_context = diff_text(codes, old_content)  # 求两个文件的差异
                if len(change_index) > 0:  # 如果两个文件有差异则可能需要更新克隆对的位置信息
                    update_clone_line_index(clone_temp, change_index)
                startLineNumber = clone_temp['startLineNumber']  # 获取当前克隆块的开始行
                endLineNumber = clone_temp['endLineNumber']  # 获取当前克隆块的结束行
                for line_index in line_index_list:
                    commit_start = line_index['start']  # 获取提交的开始行
                    commit_end = line_index['end']  # 获取提交的结束行
                    if not (commit_start > endLineNumber or commit_end < startLineNumber):
                        fingerprint = clone['fingerprint']  # 获取当前克隆的id
                        if not bug_induce_result_dic.get(fingerprint):
                            bug_induce_result_dic[fingerprint] = []  # 如果没有当前序号对应的克隆信息就创建一个新列表用于存储结果
                        bug_induce_result_dic.get(fingerprint).append({'sourcefile': old_sourcefile,
                                                                       'startLineNumber': startLineNumber,
                                                                       'endLineNumber': endLineNumber,
                                                                       'commit_index': commit['index'],  # 提交的id
                                                                       'fix_time': fix_time,  # 该提交的错误修复时间
                                                                       })  # 存储当前克隆的信息
                        flag = True  # 如果命中则该条提交与克隆相关
            if flag:
                if commit['index'] not in bug_commit_list:
                    bug_commit_list.append(commit['index'])  # 与克隆相关的提交中添加当前哈希值
                    global bug_fix_time
                    bug_fix_time += datetime.timedelta(days=int(commit['fix_time'].split(',')[0]),
                                                       seconds=int(commit['fix_time'].split(',')[1]))  # 加上当前提交的修复时间
    return bug_induce_result_dic


def update_clone_line_index(clone, change_index):  # 根据与提交前的文件内容的差异，更新克隆对中的克隆位置信息
    startLineNumber = clone['startLineNumber']  # 获取当前克隆块的开始行
    endLineNumber = clone['endLineNumber']  # 获取当前克隆块的结束行
    for index in change_index:
        change_end = index['change_end']  # 获取更改的结束行
        if change_end < endLineNumber:  # 如果更改的结束行位于克隆块的结束行之前，那么结束行的行号将收到影响
            change = index['change']  # 更改对结束行后的代码行号产生的变化量
            endLineNumber += change
            if change_end < startLineNumber:  # 如果更改的结束行位于克隆块的开始行之前，那么开始行的行号也会收到影响
                startLineNumber += change


def read_cpp(cpp_adr):  # 读取文件路径对应的文件内容，以字符串形式返回
    with open(cpp_adr, 'rb') as f:
        data = f.read()
        encode_str = chardet.detect(data)['encoding']  # 获取该文件的编码格式，防止因为编码有问题读取错误或者影响后面生成树的行号出现偏差
    with open(cpp_adr, encoding=encode_str) as f:  # 以该文件原本的编码格式把文件读取出来
        codes = f.read()
        return codes


def diff_text(old, new):  # 产生两段文本的差异结果，输出两者产生变化的行号
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines()
    )
    diff_context = list(diff)
    diff_list = list(filter(lambda x: (x.find('@@') > -1), diff_context))  # 把差异结果里面涉及到改变行号的筛选出来
    change_index = []  # 用于存储改变行号的列表
    if len(diff_list) > 0:
        for diff in diff_list:
            pattern = re.compile('@@ \\-(.*),(.*) \\+(.*),(.*) @@')  # 正则表达式截取行号
            if not len(pattern.findall(diff)) > 0:
                continue  # 如果没有找到对应的行号则直接跳过
            result = pattern.findall(diff)[0]  # 获取第一个结果
            # change_start = int(result[0])  # 更改开始行
            change_end = int(result[0]) + int(result[1]) - 1  # 更改前结束行
            change = int(result[3]) + int(result[2]) - 1 - change_end  # 更改造成的结束行号之后的代码的行号的变化值
            change_index.append({'change_end': change_end, 'change': change})
        diff_context = str('\n'.join(diff_context[2:]))  # 拼接差异内容
    else:
        diff_context = ""
    return change_index, diff_context


def sort_count(L):  # 将列表中元素分组然后计数
    M = []
    for i in range(len(L)):
        n = L[i].copy()
        # n["count"] = L.count(L[i])
        if not n in M:
            M.append(n)
    return M


def extract_fix_time(commit_dic):  # 提取所有的提交数量和修复时间
    commit_index_list = []  # 所有的提交哈希值
    commit_fix_time = datetime.timedelta(seconds=0)  # 所有提交的修复时间总和
    for commit_list in commit_dic.values():
        for commit_info in commit_list:
            if commit_info['index'] not in commit_index_list:
                commit_index_list.append(commit_info['index'])
                commit_fix_time += datetime.timedelta(days=int(commit_info['fix_time'].split(',')[0]),
                                                      seconds=int(commit_info['fix_time'].split(',')[1]))
    return len(commit_index_list), commit_fix_time


def n_version_detect(start_file, commit_files):
    global bug_induce_result_dic, bug_commit_list, bug_fix_time
    bug_induce_result_dic = {}  # 存储结果的字典
    bug_commit_list = []  # 存储与克隆相关的提交
    bug_fix_time = datetime.timedelta(seconds=0)  # 与克隆相关的提交的平均修复时间
    sum_commit_count = 0  # 所有的提交数量
    sum_commit_time = datetime.timedelta(seconds=0)  # 所有的提交的修复时间

    # 进行错误倾向克隆检测，计算错误修复提交的平均修复时间
    for commit_xml in commit_files:
        clone_block_dic, commit_dic = parse_xml(commit_xml, start_file)  # 读取提交文件和克隆文件
        print("reading clone detection file " + start_file + "and\ncommit file " + commit_xml + ": Complete")
        fix_count, fix_time = extract_fix_time(commit_dic)  # 提取当前文件中的提交数量以及提交修复时间的总和
        sum_commit_count += fix_count  # 总提交数增加
        sum_commit_time += fix_time  # 总修复时间增加
        bug_induce_result_dic = detect(clone_block_dic, commit_dic)  # 检测错误诱导的克隆信息

    # 对结果进行去重并按照模块名进行分组计数
    for index in list(bug_induce_result_dic.keys()):
        pre_list = []  # 用于去重
        for result in bug_induce_result_dic[index]:  # 统计该克隆类内的克隆片段数量
            sourcefile = result['sourcefile']  # 文件路径
            startLineNumber = result['startLineNumber']  # 开始行号
            endLineNumber = result['endLineNumber']  # 结束行号
            if [sourcefile, startLineNumber, endLineNumber] not in pre_list:
                pre_list.append([sourcefile, startLineNumber, endLineNumber])
        if not len(pre_list) > 1:  # 如果包含的克隆片段不超过1个则不算为该克隆类存在错误倾向，直接跳过对比下一个
            del bug_induce_result_dic[index]
            continue
    bug_module_result = module_utl.sort_module_bug_induce(bug_induce_result_dic)  # 按照模块名进行分组计数
    # 求出与克隆相关的提交的平均修复时间
    clone_fix_time = bug_fix_time / len(bug_commit_list)
    # 与克隆无关的提交的平均修复时间

    no_clone_fix_time = (sum_commit_time - bug_fix_time) / (sum_commit_count - len(bug_commit_list))
    start_parts = os.path.basename(start_file).split('-')
    end_parts = os.path.basename(file_list[-1]).split('-')
    new_file_name = start_parts[0] + '-' + start_parts[1] + '-' + end_parts[1]  # 获取项目名和版本号
    for key, value in bug_induce_result_dic.items():
        # 使用列表推导式和if x not in来去重，保持原有的顺序
        bug_induce_result_dic[key] = [x for i, x in enumerate(value) if value.index(x) == i]

    with open(os.path.join("../json/bug-induce", new_file_name+"_bug_induce.json"), "w", encoding='utf-8') as f:
        f.write(json.dumps(bug_induce_result_dic, ensure_ascii=False, indent=4))

    bug_module_result = add_dict(bug_module_result, 'no_clone_fix_time', str(no_clone_fix_time))
    bug_module_result = add_dict(bug_module_result, 'clone_fix_time', str(clone_fix_time))
    bug_module_result = add_dict(bug_module_result, 'bug_commit_count', len(bug_commit_list))
    bug_module_result = add_dict(bug_module_result, 'sum_commit_count', sum_commit_count)
    bug_module_result = add_dict(bug_module_result, 'bug_dup_count', len(bug_induce_result_dic))
    bug_module_result = add_dict(bug_module_result, 'ver', new_file_name)

    all_bug_induce_result.append(bug_module_result)


def add_dict(original_dic, key, value):
    new_dict = {key: value}  # 创建一个新的字典
    new_dict.update(original_dic)  # 将原始字典的元素添加到新字典中
    return new_dict


def get_files(path, n):
    # 获取目录下所有子目录
    subdirs = [os.path.join(path, subdir) for subdir in os.listdir(path) if os.path.isdir(os.path.join(path, subdir))]
    all_file_dict = {}
    for subdir in subdirs:
        # 获取子目录下所有文件
        files = [os.path.join(subdir, file) for file in os.listdir(subdir)]
        # 使用正则表达式匹配版本号
        version_files = [(version.parse(re.search(r'(\d+\.\d+(\.\d+)?(\.\d+)?)', file).group(1)), file) for file in
                         files if
                         re.search(r'(\d+\.\d+(\.\d+)?(\.\d+)?)', file)]
        # 按版本号排序
        version_files.sort()
        # 取出连续的n个文件
        project_file_dict = {}
        for i in range(len(version_files) - n + 1):
            start_file = version_files[i][1]
            file_list = [version_files[j][1] for j in range(i, i + n)]
            project_file_dict[start_file] = file_list
        # 将项目文件字典添加到总文件字典中
        project_name = os.path.basename(subdir)
        all_file_dict[project_name] = project_file_dict
    return all_file_dict


def get_version_dup(filename):  # 获取克隆文件里面的版本信息
    match = re.search(r'(\d+\.\d+(\.\d+)?(\.\d+)?)', filename)
    if match:
        return version.parse(match.group(1))


def get_versions(filename):  # 得到commit文件的开始和结束版本
    match = re.search(r'(\d+\.\d+(\.\d+)?(\.\d+)?)(_(\d+\.\d+(\.\d+)?(\.\d+)?))?', filename)
    if match:
        start_version_str = match.group(1)
        end_version_str = match.group(5)  # group 5 corresponds to the second version number
        start_version = version.parse(start_version_str)
        end_version = version.parse(end_version_str) if end_version_str else None
        return start_version, end_version
    else:
        exit(-1)
        print("解析修复提交信息文件中的版本名出错！请检查命名或者重写解析规则！")


def get_commit_files(start_file, end_file, project_name):
    start_version = get_version_dup(start_file)
    end_version = get_version_dup(end_file)
    directory = os.path.join(os.path.join(project_root_path, 'time_commit'), project_name)
    files = [os.path.join(directory, file) for file in os.listdir(directory)]
    files.sort(key=get_versions)
    commit_files = []
    for file in files:
        file_start_version, file_end_version = get_versions(file)
        if file_start_version >= start_version and file_end_version <= end_version:
            commit_files.append(os.path.abspath(file))
    return commit_files


if __name__ == '__main__':
    # 获取当前文件的绝对路径
    current_path = os.path.abspath(__file__)
    # 获取当前文件所在目录的父目录，即项目根目录
    project_root_path = os.path.dirname(os.path.dirname(current_path))

    path = os.path.join(project_root_path, 'clone_xml')  # 你的目录路径

    n = ver_num  # 你想要的文件数量
    all_file_dict = get_files(path, n)  # 获取到所有的连续n个版本的文件名，保存到一个列表里面

    for project_name, project_file_dict in all_file_dict.items():  # 遍历文件名的列表
        all_bug_induce_result = []  # 检测的全部的版本的结果
        print(f"Bug inducing Clone detection of the [{project_name}] project is in progress...")
        for start_file, file_list in project_file_dict.items():
            commit_files = get_commit_files(start_file, file_list[-1], project_name)
            print(f"Bug inducing Clone detection of file [{start_file}] is in progress...")
            n_version_detect(start_file, commit_files)  # 检测起始文件中的错误倾向克隆
        # 将检测的所有的结果存入xls文件中
        save_name = project_name  # 加入项目名
        write_in_xsl.result_out("../results/" + project_name + "_bug_induce_dup_results.xlsx",
                                all_bug_induce_result)  # 将得到的结果保存到excel表中
        print("All Done!")
