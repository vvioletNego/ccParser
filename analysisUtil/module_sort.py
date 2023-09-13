# 统计克隆结果中涉及的模块数以及跨模块克隆的情况
import os
from xml.dom.minidom import parse
import xml.dom.minidom
import re
from util import module_utl, write_in_xsl

sum_results = []  # 模块分类的结果，存放了所有检测版本的结果


def module_parse(xml_name):
    DOMTree = xml.dom.minidom.parse(xml_name)  # 解析克隆结果的xml文件
    collection = DOMTree.documentElement  # 获取文档父节点
    summary = collection.getElementsByTagName("summary")[0]  # 获取总结部分
    totalRawLineCount = summary.getAttribute("totalRawLineCount")  # 获取代码总行数
    totalFileCount = summary.getAttribute("totalFileCount")  # 获取文件数量
    # 获取克隆组的节点列表
    dups = collection.getElementsByTagName("set")
    dup_dic = {}  # 用于存储读取到的克隆信息
    file_list = []  # 用于存储出现了克隆的文件名
    # 打印每个克隆对的信息
    for dup in dups:
        blocks = dup.getElementsByTagName('block')  # 获取克隆块信息所在元素
        fingerprint = dup.getAttribute("fingerprint")  # 获取克隆对的id
        if not dup_dic.get(fingerprint):
            dup_dic[fingerprint] = []
        for block in blocks:
            dup_dic[fingerprint].append({'sourcefile': block.getAttribute("sourceFile"),  # 文件路径
                                         'startLineNumber': int(block.getAttribute("startLineNumber")),  # 克隆片段开始行号
                                         'endLineNumber': int(block.getAttribute("endLineNumber"))  # 克隆片段结束行号
                                         })
            if block.getAttribute("sourceFile") not in file_list:
                file_list.append(block.getAttribute("sourceFile"))  # 将该文件名存入文件列表中
    module_result = module_utl.sort_module(dup_dic)  # 计算克隆行数以及检测跨模块克隆
    module_result = add_dict(module_result, 'dupFileCount', int(len(file_list)))  # 将出现克隆的文件数加入结果中
    module_result = add_dict(module_result, 'totalFileCount', int(totalFileCount))  # 结果中加入源文件数
    module_result = add_dict(module_result, 'totalRawLineCount', int(totalRawLineCount))  # 结果中加入源代码数
    new_file_name = os.path.basename(xml_name).split('-')[0] + "_" + os.path.basename(xml_name).split('-')[1]
    module_result = add_dict(module_result, 'ver', new_file_name)  # 假如项目名以及版本号
    sum_results.append(module_result)  # 将当前版本的克隆信息加入到总数据列表中


def add_dict(original_dic, key, value):
    new_dict = {key: value}  # 创建一个新的字典
    new_dict.update(original_dic)  # 将原始字典的元素添加到新字典中
    return new_dict


def process_files(path, process_func):
    # 获取目录下的所有文件
    files = os.listdir(path)
    # 根据版本号对文件进行排序
    files.sort(key=get_version)
    # 对排序后的文件进行处理
    for file in files:
        process_func(os.path.join(path, file))


def process_file(file_path):
    print(f"Process the clone module classification of file [{file_path}]")
    module_parse(file_path)


def get_version(filename):
    # 使用正则表达式匹配版本号
    match = re.search(r'\d+\.\d+\.\d+', filename)
    if match:
        # 如果找到了版本号，将其转换为元组
        return tuple(map(int, match.group().split('.')))
    else:
        # 如果没有找到版本号，返回一个空元组
        return ()


if __name__ == "__main__":
    project_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root_path, 'clone_xml')  # 你存放克隆检测结果的目录名

    for dirpath in os.scandir(path):
        if dirpath.is_dir():
            print(f"Clone classification of the [{dirpath.name}] project is in progress...")
            process_files(dirpath.path, process_file)
            save_name = f"../results/{dirpath.name}_dup_results.xlsx"
            write_in_xsl.result_out(save_name, sum_results)
            sum_results.clear()  # 清空结果列表以便于下一个项目的处理

    print("All Done!")
