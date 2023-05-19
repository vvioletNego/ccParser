# 以block粒度的克隆信息进行错误倾向的检测(设定一个初始版本以后检测后面四个版本的提交中的克隆错误倾向，加入修复时间的统计)
import datetime
import difflib
import os
import re
import chardet
from util import read_commit, read_clone, module_utl, write_in_xsl

codes_file = {}  # 文件名对应的代码内容，避免重读
bug_induce_result_dic = {}  # 存储结果的字典
bug_commit_list = []  # 存储与克隆相关的提交
bug_fix_time = datetime.timedelta(seconds=0)  # 与克隆相关的提交的平均修复时间
all_bug_induce_result = []  # 检索的所有版本的结果


def parse_xml(commit_xml, clone_xml):  # 读取提交和克隆信息的xml文件存储到相应的字典中
    clone_block_dic = read_clone.read_clone_block(clone_xml)  # 读取block粒度的克隆文件
    commit_dic = read_commit.parse_commit_block_new(commit_xml)  # 读取提交的文件
    # 两者都以文件路径为字典的key，便于快速找出两者的共同文件路径
    return clone_block_dic, commit_dic


def detect(clone_block_dic, commit_dic):
    common_sourcefile = clone_block_dic.keys() & commit_dic.keys()  # 求出两者共有的文件路径
    # bug_induce_result_dic = {}  # 用于存储错误诱导的克隆对结果的字典，以克隆对的id为key
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
                if not old_sourcefile.replace("\\", "/").find('/'.join(commit['old_sourcefile'].replace(".cc", ".cpp").split('/')[-3:-1])) > -1:
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


def extract_fix_time(commit_dic):  # 提取所有的提交数量 和修复时间
    commit_index_list = []  # 所有的提交哈希值
    commit_fix_time = datetime.timedelta(seconds=0)  # 所有提交的修复时间总和
    for commit_list in commit_dic.values():
        for commit_info in commit_list:
            if commit_info['index'] not in commit_index_list:
                commit_index_list.append(commit_info['index'])
                commit_fix_time += datetime.timedelta(days=int(commit_info['fix_time'].split(',')[0]),
                                                      seconds=int(commit_info['fix_time'].split(',')[1]))
    return len(commit_index_list), commit_fix_time


def n_version_extract(v0_filename, num):
    global bug_induce_result_dic, bug_commit_list, bug_fix_time
    bug_induce_result_dic = {}  # 存储结果的字典
    bug_commit_list = []  # 存储与克隆相关的提交
    bug_fix_time = datetime.timedelta(seconds=0)  # 与克隆相关的提交的平均修复时间
    commit_xml_list = []  # 用于检测的提交的文件路径列表
    sum_commit_count = 0  # 所有的提交数量
    sum_commit_time = datetime.timedelta(seconds=0)  # 所有的提交的修复时间

    pre_sourcefile = "../clone_xml/"
    pre_sourcefile += "apollo/" + v0_filename if v0_filename.find("apollo") > -1 else "autoware/" + v0_filename
    # 获取起始克隆结果的文件路径

    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\clone_xml"  # 进入克隆结果所在文件夹
    path += "\\apollo" if v0_filename.find("apollo") > -1 else "\\autoware"  # 根据检索的项目名称获取相应的文件路径父目录
    files = os.listdir(path)  # 得到当前文件夹下所有文件
    pattern = re.compile(r'\d+')
    files.sort(key=lambda x: int(pattern.findall(x)[0] + pattern.findall(x)[1]))  # 对读取的路径进行排序

    index = -1  # 起始文件的序号
    for file in files:
        file_name = os.path.basename(file)  # 获取文件名
        if file_name == v0_filename:  # 如果找到了该起始文件
            index = files.index(file)  # 得到该文件的序号
            break  # 退出循环

    # 筛选需要检测的提交文件
    path = path.replace("clone_xml", "time_commit")  # 换到提交所在文件夹
    files = os.listdir(path)  # 获取提交路径下的所有的文件
    post_sourcefile = ""  # 记录最后一个版本的文件路径
    for file in files[index:]:
        file_name = os.path.basename(file)
        digits = pattern.findall(file)
        post_ver = int(digits[3] + digits[4]) if int(digits[4]) < 10 else int(digits[3])*10 + int(int(digits[4])/10)*10 + int(digits[4])%10   # 后一个版本号
        v0_ver_digits = pattern.findall(v0_filename)
        if v0_filename.find('apollo') > -1:
            if (post_ver - int(v0_ver_digits[0] + v0_ver_digits[1])) / 5 > 4:
                break
            else:
                post_sourcefile = "../time_commit/apollo/" + file_name
                commit_xml_list.append(post_sourcefile)
        elif v0_filename.find('autoware') > -1:
            if post_ver - int(v0_ver_digits[0] + v0_ver_digits[1]) > 4:
                break
            else:
                post_sourcefile = "../time_commit/autoware/" + file_name
                commit_xml_list.append(post_sourcefile)

    # 进行错误倾向克隆检测，计算错误修复提交的平均修复时间
    for commit_xml in commit_xml_list:
        clone_block_dic, commit_dic = parse_xml(commit_xml, pre_sourcefile)  # 读取提交文件和克隆文件
        fix_count, fix_time = extract_fix_time(commit_dic)  # 提取当前文件中的提交数量以及提交修复时间的总和
        sum_commit_count += fix_count  # 总提交数增加
        sum_commit_time += fix_time  # 总修复时间增加
        bug_induce_result_dic = detect(clone_block_dic, commit_dic)  # 检测错误诱导的克隆信息

    # 对结果进行去重并按照模块名进行分组计数
    for index in list(bug_induce_result_dic.keys()):
        pre_list = []   # 用于去重
        for result in bug_induce_result_dic[index]:  # 统计该克隆类内的克隆片段数量
            sourcefile = result['sourcefile']  # 文件路径
            startLineNumber = result['startLineNumber']  # 开始行号
            endLineNumber = result['endLineNumber']  # 结束行号
            if [sourcefile, startLineNumber, endLineNumber] not in pre_list:
                pre_list.append([sourcefile, startLineNumber, endLineNumber])
        if not len(pre_list) > 1:   # 如果包含的克隆片段不超过1个则不算为该克隆类存在错误倾向，直接跳过对比下一个
            del bug_induce_result_dic[index]
            continue
    bug_module_result = module_utl.sort_module_bug_induce(bug_induce_result_dic)  # 按照模块名进行分组计数
    # 求出与克隆相关的提交的平均修复时间
    clone_fix_time = bug_fix_time/len(bug_commit_list)
    # 与克隆无关的提交的平均修复时间
    no_clone_fix_time = (sum_commit_time - bug_fix_time)/(sum_commit_count - len(bug_commit_list))
    pre_ver = pattern.findall(v0_filename)
    post_ver = pattern.findall(post_sourcefile)
    bug_module_result.update({
        'bug_dup_count': len(bug_induce_result_dic),  # 错误倾向克隆数量
        'clone_fix_time': str(clone_fix_time),  # 与克隆相关的平均修复时间
        'no_clone_fix_time': str(no_clone_fix_time),  # 与克隆无关的提交的平均修复时间
        'sum_commit_count': sum_commit_count,  # 所有提交的数量
        'bug_commit_count': len(bug_commit_list),  # 与错误相关的提交数
        'ver': pre_ver[0] + '.' + pre_ver[1] + '.' + pre_ver[2] + "_" + post_ver[3] + '.' + post_ver[4] + '.' + post_ver[5],
        })
    return bug_module_result


if __name__ == '__main__':
    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\clone_xml"  # 进入存储xml文件的文件夹
    for filepath, dirnames, filenames in os.walk(path):
        for dirname in dirnames:
            all_bug_induce_result = []
            d_path = path + "\\" + dirname
            for filepath, dirnames, filenames in os.walk(d_path):
                pattern = re.compile(r'\d+')
                filenames.sort(key=lambda x: int(pattern.findall(x)[0] + pattern.findall(x)[1]))  # 对读取的路径进行排序
                for filename in filenames:
                    v0_filename = filename
                    num = 5
                    if len(filenames) - filenames.index(filename) < num:
                        break
                    all_bug_induce_result.append(n_version_extract(v0_filename, num))
            save_name = "apollo_" if dirname.find("apollo") > -1 else "autoware_"
            write_in_xsl.module_result_output_bug("../results/" + save_name + "bug_induce_results.xls", all_bug_induce_result)

