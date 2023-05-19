# 以两个版本的克隆结果文件对比检测出共同修改(block粒度)(测试版本)
#  加入对更改代码行的统计()
"""
1.将两个版本的克隆文件（block粒度）读出，存储在以文件名为key的字典中
2.将上一步中得到的字典中相同的key（文件名）筛出，遍历两个字典
3.按照文件路径将两个文件的代码内容读出，求两者差异，得到差异位置行号，与克隆位置行号进行对比，如果有交集则证明为共变克隆，计入结果，结果字典以克隆类的id为key
4.对上一步中得到的结果进行分组计数，筛去一个克隆序号对应的克隆结果不足2个的结果，即为最后的结果
"""
import os
import re
import chardet
from util import read_clone, module_utl, write_in_xsl
import difflib

all_commodify_results = []  # 检测的全部的版本的结果
all_change_results = []  # 检错的所有版本跨度的修改行结果


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
    common_sourcefile = pre_clone_dic.keys() & post_clone_dic.keys()  # 找出两者中相同的key值（文件路径）
    # comodify_result = {}  # 用于存储共同修改结果的字典，key是克隆对序号
    for sourcefile in common_sourcefile:
        pre_clone_list = pre_clone_dic[sourcefile]  # 得到v0版本的所有克隆类信息
        post_clone_list = post_clone_dic[sourcefile]  # 得到v1版本的所有克隆类信息
        pre_old_sourcefile_list = set([x['old_sourcefile'] for x in pre_clone_list])  # 将v0克隆类的文件路径去重，防止重名
        post_old_sourcefile_list = set([x['old_sourcefile'] for x in post_clone_list])  # 将v1克隆类的文件路径去重，防止重名
        for pre_old_sourcefile in pre_old_sourcefile_list:
            for post_old_sourcefile in post_old_sourcefile_list:
                if "".join(pre_old_sourcefile.split("\\")[-3:-1]).find(
                        "".join(post_old_sourcefile.split("\\")[-3:-1])) > -1:
                    # 对比两个文件路径在最后三级目录的部分，如果一致则判断为一个文件的内容
                    pre_code = read_cpp(pre_old_sourcefile)  # 获取v0的代码内容
                    post_code = read_cpp(post_old_sourcefile)  # 获取v1的代码内容
                    change_index, diff_context = diff_text(pre_code, post_code)  # 求两个版本的代码内容的差异
                    if not len(change_index) > 0:  # 如果没有差异就跳过
                        continue
                    for change in change_index:
                        change_start = change['change_start']  # 获取更改前开始行号
                        change_end = change['change_end']  # 获取更改前结束行号
                        pre_clone_involve = extract_clone_block(pre_old_sourcefile, pre_clone_list,
                                                                change_start, change_end)  # 得到该修改位置上涉及的前一个版本的克隆片段
                        if not len(pre_clone_involve) > 0:  # 如果当前修改位置上没有涉及前一个版本的克隆片段，直接跳过
                            continue
                        post_change_start = change['post_start']  # 获取更改后开始行号
                        post_change_end = change['post_end']  # 获取更改后结束行号
                        post_clone_involve = extract_clone_block(post_old_sourcefile, post_clone_list,
                                                                 post_change_start, post_change_end)
                        # 得到更改后的位置上涉及的下一个版本的克隆片段
                        min_length = len(pre_clone_involve) if len(pre_clone_involve) < len(
                            post_clone_involve) else len(post_clone_involve)
                        # 取两个克隆片段列表中较小的长度，避免过界
                        for i in range(min_length):
                            fingerprint = pre_clone_involve[i][2]  # 获取克隆id
                            startLineNumber = pre_clone_involve[i][0]  # 获取克隆更改前的开始行号
                            endLineNumber = pre_clone_involve[i][1]  # 获取克隆更改前的结束行号
                            post_startLineNumber = post_clone_involve[i][0]  # 获取克隆更改后的开始行号
                            post_endLineNumber = post_clone_involve[i][1]  # 获取克隆更改后的结束行号
                            if not comodify_result.get(fingerprint):
                                comodify_result[fingerprint] = []  # 如果没有当前序号对应的克隆信息就创建一个新列表用于存储结果
                            comodify_result.get(fingerprint).append({'sourcefile': pre_old_sourcefile,  # 更改前的文件名
                                                                     'startLineNumber': startLineNumber,  # 更改前的开始行号
                                                                     'endLineNumber': endLineNumber,  # 更改前的结束行号
                                                                     # 'post_sourcefile': '\\'.join(post_old_sourcefile.split('\\')[4:]),
                                                                     'post_start': post_startLineNumber,  # 更改后的开始行号
                                                                     'post_end': post_endLineNumber,  # 更改后的结束行号
                                                                     'change_start': change_start if change_start > startLineNumber else startLineNumber,
                                                                     # 更改开始行号
                                                                     'change_end': change_end if change_end < endLineNumber else endLineNumber,
                                                                     # 更改结束行号
                                                                     })  # 存储命中的克隆块的信息
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
    diff_list = list(filter(lambda x: (x.find('@@') > -1), diff_context))  # 把差异结果里面涉及到改变行号的筛选出来
    change_index = []  # 用于存储改变行号的列表
    if len(diff_list) > 0:
        for diff in diff_list:
            pattern = re.compile('@@ \\-(.*),(.*) \\+(.*),(.*) @@')  # 正则表达式截取行号
            if not len(pattern.findall(diff)) > 0:
                continue  # 如果没有找到对应的行号则直接跳过
            result = pattern.findall(diff)[0]  # 获取第一个结果
            change_start = int(result[0])  # 更改前的开始行
            change_end = int(result[0]) + int(result[1]) - 1  # 更改前的结束行
            post_start = int(result[2])  # 更改后的开始行号
            post_end = int(result[2]) + int(result[3]) - 1  # 更改后的结束行
            change_index.append({'change_start': change_start, 'change_end': change_end,
                                 'post_start': post_start, 'post_end': post_end,
                                 })
        diff_context = str('\n'.join(diff_context[2:]))  # 拼接差异内容
    else:
        diff_context = ""
    # 注意差异结果中行号是从0开始的，并且开始行号是改变前一行
    # diff = '\n'.join(diff)
    return change_index, diff_context


def sort_count(L):  # 将列表中元素去重然后计数
    M = []
    for i in range(len(L)):
        n = L[i].copy()
        # n["count"] = L.count(L[i])
        if not n in M:
            M.append(n)
    return M


def n_version_detect(v0_filename, num):  # 以一个起始版本开始的共num个版本的共变克隆的检测
    pre_sourcefile = "../clone_xml/"
    pre_sourcefile += "apollo/" + v0_filename if v0_filename.find("apollo") > -1 else "autoware/" + v0_filename
    # 获取起始文件的文件路径
    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\clone_xml"  # 进入克隆结果所在文件夹
    path += "\\apollo" if v0_filename.find("apollo") > -1 else "\\autoware"  # 根据检索的项目名称获取相应的文件路径父目录
    files = os.listdir(path)  # 得到当前文件夹下所有文件
    if v0_filename.find("autoware") > -1:  # 如果是autoware项目的文件路径需要额外进行排序因为字符串中的10会排在2的前面
        pattern = re.compile(r'\d+')
        files.sort(key=lambda x: int(pattern.findall(x)[1]))  # 对读取的路径进行排序
    index = -1  # 起始文件的序号
    for file in files:
        file_name = os.path.basename(file)  # 获取文件名
        if file_name == v0_filename:  # 如果找到了该起始文件
            index = files.index(file)  # 得到该文件的序号
            break  # 退出循环
    # if index == -1:  # 如果没有找到该文件名对应的文件则退出程序
    #     print("文件名有误!")
    #     exit  # 退出程序
    # if len(files) - index < num:  # 如果往后已经不够num个版本了就退出
    #     print("版本数量不足！")
    #     # save_name = "apollo" if v0_filename.find('apollo') > -1 else "autoware"
    #     # write_in_xsl.module_result_output("../results/" + save_name + "_comodify_dup_results.xls", all_commodify_results)
    #     # write_in_xsl.module_result_output("../results/" + save_name + "_change_commodify_results.xls", all_change_results)
    #     exit  # 退出程序
    k = 0  # 计数，用于往后找四个版本的文件使用
    comodify_result = {}  # 用于存储结果的字典
    v1_filename = ""  # 最后一个版本的文件名
    for file in files[index + 1:]:
        file_name = os.path.basename(file)
        post_sourcefile = "../clone_xml/"
        post_sourcefile += "apollo/" + file_name if file_name.find("apollo") > -1 else "autoware/" + file_name
        # 根据项目名获取相应的文件名
        pre_clone_dic, post_clone_dic = read_xml(pre_sourcefile, post_sourcefile)  # 读取两者的克隆对信息
        comodify_result = detect(pre_clone_dic, post_clone_dic, comodify_result)
        k += 1  # 计数增加
        if k >= num - 1:
            v1_filename = file_name
            break  # 如果计数已经到达了4，则说明已经对比完成了
    for index in list(comodify_result.keys()):
        pre_clone = []
        post_clone = []  # 用于去重
        for result in comodify_result[index]:
            if not [result['sourcefile'], result['startLineNumber'], result['endLineNumber']] in pre_clone:
                pre_clone.append([result['sourcefile'], result['startLineNumber'], result['endLineNumber']])
            if not [result['post_start'], result['post_end']] in post_clone:
                post_clone.append([result['post_start'], result['post_end']])
        if not (len(pre_clone) > 1 and len(post_clone) > 1):
            del comodify_result[index]
            continue  # 如果该克隆类内的克隆片段不超过两个，直接筛去
        comodify_result[index] = sort_count(comodify_result[index])  # 将克隆对函数信息去重并计数
        if not len(comodify_result[index]) > 1:  # 如果去重后的克隆对内对应的函数量不超过1条则直接删除，保留的即为共同修改的结果
            del comodify_result[index]
            continue
    change_comidify_results = {}  # 用于给共变克隆上的修改行计数
    for index, clone_list in comodify_result.items():
        if not change_comidify_results.get(index):
            change_comidify_results[index] = []
        for clone in clone_list:
            change_comidify_results[index].append(
                {'startLineNumber': clone['change_start'], 'endLineNumber': clone['change_end'],
                 'sourcefile': clone['sourcefile']})  # 将更改信息存入
    # 对共同修改的克隆的模块信息进行统计
    modify_result = module_utl.sort_module(comodify_result)
    change_modify_result = module_utl.sort_module(change_comidify_results)
    # 加入版本信息
    modify_result['ver'] = v0_filename.replace(".xml", "") + "_" + v1_filename.replace(".xml", "")
    change_modify_result['ver'] = v0_filename.replace(".xml", "") + "_" + v1_filename.replace(".xml", "")  # 给两个结果加入版本信息
    return modify_result, change_modify_result


if __name__ == '__main__':
    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\clone_xml"  # 进入存储xml文件的文件夹
    for filepath, dirnames, filenames in os.walk(path):
        for dirname in dirnames:
            all_commodify_results = []
            all_change_results = []  # 进入一个新项目就要清空检测结果
            d_path = path + "\\" + dirname
            for filepath, dirnames, filenames in os.walk(d_path):
                pattern = re.compile(r'\d+')
                filenames.sort(key=lambda x: int(pattern.findall(x)[0] + pattern.findall(x)[1]))  # 文件名按照版本号排序
                for filename in filenames:
                    v0_filename = filename
                    num = 5
                    if len(filenames) - filenames.index(filename) < num:  # 如果版本数量不足就退出
                        print('版本数量不足!')
                        break
                    modify_result, change_modify_result = n_version_detect(v0_filename, num)
                    all_commodify_results.append(modify_result)
                    all_change_results.append(change_modify_result)
            # 将检测的所有的结果存入xls文件中
            save_name = "apollo" if d_path.find('apollo') > -1 else "autoware"
            write_in_xsl.module_result_output("../results/" + save_name + "_comodify_dup_results.xls", all_commodify_results)
            write_in_xsl.module_result_output("../results/" + save_name + "_change_commodify_results.xls", all_change_results)
