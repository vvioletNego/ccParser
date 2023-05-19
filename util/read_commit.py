# 从xml中提取提交描述信息
import datetime
import os
import re
import xml.dom.minidom


def find_line_index(diff):  # 根据传入的提交信息提取修改的行号
    pattern = re.compile('@@ \\-(.*),(.*) \\+(.*),(.*) @@')  # 正则表达式
    results = pattern.findall(diff)  # 获取第一个结果
    line_index_list = []  # 用于存储涉及到的行号
    for result in results:
        start = int(result[0])  # 更改前的开始行
        end = int(result[0]) + int(result[1]) - 1  # 更改前的结束行
        new_start = int(result[2])  # 更改后的开始行
        new_end = int(result[3]) + int(result[2]) - 1  # 更改后的结束行
        line_index_list.append({'start': start, 'end': end, 'new_start': new_start, 'new_end': new_end,
                                'change_index': new_end - end})
        # 将涉及的行号信息存储到输出列表中
    return line_index_list


def find_content_change(diff):  # 根据传入的差异内容提取每一个位置的修改内容
    results = diff.split("@@")
    results = [x for x in results if not x == ""]  # 去空值
    pattern = re.compile('\\-(\d+),(\d+) \\+(\d+)(\d+)')
    diff_results = []  # 从提交内容中解析出的修改行号和修改内容
    line_index_results = []
    for i in range(len(results)):
        if i % 2 == 0:
            line_index_results = pattern.findall(results[i])[0]  # 如果是偶数项那么就是修改行号
            start = int(line_index_results[0])  # 更改前的开始行
            end = int(line_index_results[0]) + int(line_index_results[1]) - 1  # 更改前的结束行
            new_start = int(line_index_results[2])  # 更改后的开始行
            new_end = int(line_index_results[3]) + int(line_index_results[2]) - 1  # 更改后的结束行
            line_index_results = {'start': start, 'end': end, 'new_start': new_start, 'new_end': new_end}
        else:
            diff_results.append([line_index_results, results[i]])  # 如果是奇数项就是修改的内容
    return results


def parse_commit_func(xml_name, mode):  # 读取function粒度的提交描述文件
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    root = DOMTree.documentElement
    commits = root.childNodes  # 获取提交信息
    commit_func_list = []  # 存储提交信息列表
    for commit in commits:
        if not isinstance(commit, xml.dom.minidom.Element):  # 跳过中间的换行的文本节点
            continue
        if mode == 'bug_induce':  # 如果是用于错误诱导的检测则需要根据提交描述信息进行筛选
            flag = False  # 检测是否是错误修复提交的标志位
            msg = commit.getElementsByTagName("msg")[0].childNodes[0].data  # 提交描述信息
            corrective_words = ['bug', 'fix', 'wrong', 'error', 'fail', 'problem', 'patch']  # 错误修复提交的关键词
            for word in corrective_words:
                if word.lower() in msg.lower():  # 如果该提交描述中包含错误修复提交的关键词
                    flag = True
                    break
            if not flag:
                continue
        modified_files = commit.getElementsByTagName("modified_files")[0]  # 修改文件的节点
        files = modified_files.getElementsByTagName("file")  # 获取修改文件的列表
        if not len(files) > 0:  # 如果修改文件为0则跳过
            continue
        for file in files:
            old_path = file.getAttribute("old_path")  # 修改前的文件路径
            new_path = file.getAttribute("new_path")  # 修改后的文件路径
            methods_element = file.getElementsByTagName("methods")[0]  # 函数列表节点
            methods = methods_element.getElementsByTagName("method")  # 函数列表
            for method in methods:
                function_name = method.getAttribute("function_name")  # 函数名
                commit_func = {'old_path': old_path, 'new_path': new_path, 'function_name': function_name}
                commit_func_list.append(commit_func)  # 将函数信息存储到列表
    return commit_func_list  # 返回提交信息列表


def parse_commit_block(xml_name):  # 读取block粒度的提交描述信息，得到git提交的diff
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    root = DOMTree.documentElement
    commits = root.getElementsByTagName("commit")  # 得到提交信息的节点列表
    commit_block_list = []  # 获取到的提交信息结果列表

    for commit in commits:
        old_path = commit.getAttribute("old_path")  # 修改前的文件路径
        new_path = commit.getAttribute("new_path")  # 修改后的文件路径
        if not len(commit.getElementsByTagName("diff")[0].childNodes) > 0:
            continue  # 如果该提交中的修改信息为空则跳过，处理结果中的空值
        diff = commit.getElementsByTagName("diff")[0].childNodes[0].data  # 提交的diff信息，包含修改详情和行号信息
        line_index_list = find_line_index(diff)  # 本次提交发生的行号变化
        commit_block_list.append({'old_path': old_path, 'new_path': new_path, 'diff': diff,
                                  'line_index_list': line_index_list})
    return commit_block_list


def parse_commit_block_new(xml_name):  # 解析block粒度的提交描述信息，用于错误诱导检测
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    root = DOMTree.documentElement
    commits = root.getElementsByTagName("commit")  # 得到提交信息的节点列表
    commit_block_dic = {}  # 获取到的提交信息结果字典，以文件路径为key，便于后续的比较
    for commit in commits:
        msg = commit.getElementsByTagName('msg')[0].childNodes[0].data  # 提交描述信息
        fix_time = commit.getAttribute('fix_time')  # 获取修复时间
        commit_hash = commit.getAttribute('hash')  # 提交的哈希值
        modified_files = commit.getElementsByTagName('modified_files')[0]  # 得到修改的文件列表节点
        files = modified_files.getElementsByTagName('file')  # 获取单个修改文件的信息节点
        # 累加本次提交的修复时间
        if not len(files) > 0:
            continue  # 如果当前提交中没有修改文件的信息直接跳过
        for file in files:  # 遍历该提交涉及的文件信息
            old_path = file.getAttribute('old_path')  # 获取修改前的文件路径
            if xml_name.find('apollo') > -1 and old_path.find('cc') > -1:
                old_path = old_path.replace('cc', 'cpp')  # apollo项目中可能有一些文件夹里面的是cc后缀全部统一为cpp
            old_sourcefile = old_path  # 存储原来的文件路径
            # new_path = file.getAttribute('new_path')  # 获取修改后的文件路径
            old_path = old_path.split("/")[-1]  # 将文件路径全部提取为文件名
            if len(file.getElementsByTagName('diff')) < 1 or len(file.getElementsByTagName('diff')[0].childNodes) < 1:
                # 防止过界
                continue
            diff = file.getElementsByTagName('diff')[0].childNodes[0].data  # 获取提交前后的差异信息
            line_index_list = find_line_index(diff)  # 本次提交发生的行号变化
            # diff_results = find_content_change(diff)  # 获取本次提交的修改内容和涉及行号
            if len(file.getElementsByTagName('old_file')) < 1 or len(file.getElementsByTagName('old_file')[0].childNodes) < 1:
                # 防止过界
                continue
            old_content = file.getElementsByTagName('old_file')[0].childNodes[0].data
            # 获取修改前的文件内容
            if not commit_block_dic.get(old_path):
                commit_block_dic[old_path] = []
            commit_block_dic[old_path].append({'line_index_list': line_index_list,
                                               'old_content': old_content,
                                               # 'diff': diff,
                                               # 'msg': msg,
                                               # 'diff_results': diff_results,  # 提交的修改内容和位置信息
                                               'index': commit_hash,  # 提交的哈希值,
                                               'old_sourcefile': old_sourcefile,  # 提交修改的文件路径
                                               'fix_time': fix_time,  # 提交修复时间
                                               })
            # 将获取到提交信息存储到对应的列表中
    return commit_block_dic


if __name__ == '__main__':
    # parse_commit_block_new("../commit_block/commit_a_branch/autoware_a_new/autoware_1.0.0_1.4.0_commit_func.xml")
    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\commit_block\\commit_a_branch\\apollo_a_new"  # 进入存储xml文件的文件夹
    for filepath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            xml_name = os.path.join(filepath, filename)
            parse_commit_block(xml_name)
