"""
1.将两个版本的克隆文件（block粒度）读出，存储在以文件名为key的字典中
2.将上一步中得到的字典中相同的key（文件名）筛出，遍历两个字典
3.按照文件路径将两个文件的代码内容读出，求两者差异，得到差异位置行号，与克隆位置行号进行对比，如果有交集则证明为共变克隆，计入结果，结果字典以克隆类的id为key
4.对上一步中得到的结果进行分组计数，筛去一个克隆序号对应的克隆结果不足2个的结果，即为最后的结果
"""
import json
import os
import re
import chardet
from util import read_clone, write_in_xsl, module_utl
import difflib
from packaging import version


all_commodify_results = []  # 检测的全部的版本的结果
ver_num = 5  # 设置版本跨度


def read_xml(pre_sourcefile, post_sourcefile):  # 按照两个版本的文件路径读取相应的克隆信息字典
    pre_clone_dic = read_clone.read_clone_block(pre_sourcefile)
    post_clone_dic = read_clone.read_clone_block(post_sourcefile)
    return pre_clone_dic, post_clone_dic


def read_cpp(cpp_adr):  # 读取cpp文件，返回读取结果
    with open(cpp_adr, 'rb') as f:
        data = f.read()
        encode_str = chardet.detect(data)['encoding']  # 获取该文件的编码格式，防止因为编码有问题读取错误或者影响后面生成树的行号出现偏差
    with open(cpp_adr, encoding=encode_str) as f:  # 以该文件原本的编码格式把文件读取出来
        codes = f.read()
        return codes


def detect(pre_clone_dic, post_clone_dic, comodify_result):  # 对比两个文件的克隆对结果，找出两个版本中相同文件名和相同函数名的克隆信息
    common_sourcefile = pre_clone_dic.keys() & post_clone_dic.keys()  # 求出两个克隆对结果中相同的文件名
    for sourcefile in common_sourcefile:
        pre_clone_list = pre_clone_dic[sourcefile]
        post_clone_list = post_clone_dic[sourcefile]  # 得到两个结果中该文件路径对应的克隆信息
        pre_old_sourcefile_list = {x['old_sourcefile'] for x in pre_clone_list}
        post_old_sourcefile_list = {x['old_sourcefile'] for x in post_clone_list}
        for pre_old_sourcefile in pre_old_sourcefile_list:
            pre_old_sourcefile_path = "".join(pre_old_sourcefile.split("\\")[-3:-1])
            for post_old_sourcefile in post_old_sourcefile_list:
                post_old_sourcefile_path = "".join(post_old_sourcefile.split("\\")[-3:-1])
                if pre_old_sourcefile_path.find(post_old_sourcefile_path) > -1:
                    pre_code = read_cpp(pre_old_sourcefile)
                    post_code = read_cpp(post_old_sourcefile)  # 读取两个文件路径下的源码
                    change_index, diff_context = diff_text(pre_code, post_code)  # 求出两个源码的差异
                    if not len(change_index) > 0:
                        continue
                    for change in change_index:
                        change_start = change['change_start']
                        change_end = change['change_end']
                        pre_clone_involve = extract_clone_block(pre_old_sourcefile, pre_clone_list, change_start,
                                                                change_end)
                        if not len(pre_clone_involve) > 0:
                            continue
                        post_change_start = change['post_start']
                        post_change_end = change['post_end']
                        post_clone_involve = extract_clone_block(post_old_sourcefile, post_clone_list,
                                                                 post_change_start, post_change_end)
                        min_length = min(len(pre_clone_involve), len(post_clone_involve))
                        for i in range(min_length):
                            fingerprint = pre_clone_involve[i][2]
                            startLineNumber = pre_clone_involve[i][0]
                            endLineNumber = pre_clone_involve[i][1]
                            post_startLineNumber = post_clone_involve[i][0]
                            post_endLineNumber = post_clone_involve[i][1]
                            comodify_result.setdefault(fingerprint, []).append({
                                'sourcefile': pre_old_sourcefile,  # 文件路径
                                'startLineNumber': startLineNumber,  # 开始行号
                                'endLineNumber': endLineNumber,  # 结束行号
                                'post_start': post_startLineNumber,  # 修改后的开始行号
                                'post_end': post_endLineNumber,  # 修改后的结束行号
                                'change_start': max(change_start, startLineNumber),  # 修改片段的开始行号
                                'change_end': min(change_end, endLineNumber),  # 修改片段的结束行号
                            })
    return comodify_result


def extract_clone_block(old_sourcefile, clone_list, change_start, change_end):  # 抓取当前差异位置中涉及的克隆片段信息
    involve_clone = []  # 该位置上包含的克隆片段
    clone_list = sorted(clone_list, key=lambda x: x['startLineNumber'])  # 将需要比对的克隆片段按照开始行号升序排列
    for clone in clone_list:
        if not clone['old_sourcefile'] == old_sourcefile:  # 如果当前克隆片段所在文件路径不符合，直接跳过
            continue
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


def diff_text(old, new):  # 产生两段文本的差异结果，输出两者产生变化的行号
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines()
    )
    diff_context = list(diff)
    diff_list = [x for x in diff_context if '@@' in x]
    change_index = []
    pattern = re.compile('@@ \\-(.*),(.*) \\+(.*),(.*) @@')

    for diff in diff_list:
        match = pattern.findall(diff)
        if not match:
            continue
        result = match[0]
        change_start, change_end, post_start, post_end = map(int, result)
        change_end += change_start - 1
        post_end += post_start - 1
        change_index.append({
            'change_start': change_start,
            'change_end': change_end,
            'post_start': post_start,
            'post_end': post_end,
        })

    diff_context = '\n'.join(diff_context[2:]) if diff_list else ""
    return change_index, diff_context


def sort_count(L):  # 将列表中元素去重然后计数
    M = []
    for i in range(len(L)):
        n = L[i].copy()
        # n["count"] = L.count(L[i])
        if not n in M:
            M.append(n)
    return M


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


def n_version_detect(start_version_file, file_list):
    comodify_result = {}  # 用于存储结果的字典
    for file in file_list[1:]:
        pre_clone_dic, post_clone_dic = read_xml(start_version_file, file)  # 读取两者的克隆对信息
        comodify_result = detect(pre_clone_dic, post_clone_dic, comodify_result)  # 检测共变克隆

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
        if len(comodify_result[index]) <= 1:  # 如果去重后的克隆对内对应的函数量不超过1条则直接删除，保留的即为共同修改的结果
            del comodify_result[index]
            continue

        # 将克隆的更改数据提取出来处理
        if not change_comidify_results.get(index):
            change_comidify_results[index] = []
        for clone in comodify_result[index]:
            change_comidify_results[index].append(
                {'startLineNumber': clone['change_start'], 'endLineNumber': clone['change_end'],
                 'sourcefile': clone['sourcefile']})

    modify_result = module_utl.sort_module(comodify_result)  # 统计行数和跨模块的数据
    change_modify_result = module_utl.sort_module(change_comidify_results)  # 统计更改行的行数和跨模块克隆上的数据

    modify_result['change_cross_dup_line'] = change_modify_result['cross_dup_line']
    modify_result['change_line'] = change_modify_result['dup_line']
    modify_result['change_dup_module'] = change_modify_result['dup_module']

    start_parts = os.path.basename(start_version_file).split('-')
    end_parts = os.path.basename(file_list[-1]).split('-')
    new_file_name = start_parts[0] + '-' + start_parts[1] + '-' + end_parts[1]  # 获取项目名和版本号
    new_dict = {'ver': new_file_name}  # 创建一个新的字典
    with open(os.path.join("../json/comodify", new_file_name+"_comodify.json"), "w", encoding='utf-8') as f:
        f.write(json.dumps(comodify_result, ensure_ascii=False, indent=4))
    new_dict.update(modify_result)  # 将原始字典的元素添加到新字典中
    all_commodify_results.append(new_dict)


if __name__ == '__main__':
    # 获取当前文件的绝对路径
    current_path = os.path.abspath(__file__)
    # 获取当前文件所在目录的父目录，即项目根目录
    project_root_path = os.path.dirname(os.path.dirname(current_path))

    path = os.path.join(project_root_path, 'clone_xml')  # 你的目录路径

    n = ver_num  # 你想要的文件数量
    all_file_dict = get_files(path, n)  # 获取到所有的连续n个版本的文件名，保存到一个列表里面

    for project_name, project_file_dict in all_file_dict.items():  # 遍历文件名的列表
        all_commodify_results = []  # 检测的全部的版本的结果
        print(f"Co-modified Clone detection of the [{project_name}] project is in progress...")
        for start_file, file_list in project_file_dict.items():
            print(f"Co-modified Clone detection of file [{start_file}] is in progress...")
            n_version_detect(start_file, file_list)  # 检测起始文件中的共变克隆
        # 将检测的所有的结果存入xls文件中
        save_name = project_name  # 加入项目名
        write_in_xsl.result_out("../results/" + project_name + "_comodify_dup_results.xlsx",
                                all_commodify_results)  # 将得到的结果保存到excel表中
        print("All Done!")
