import os
import re
import xml.dom.minidom
from util import module_utl, write_in_xsl
# 读取克隆文件计算行数以及统计模块分布情况


def module_parse(xml_name):
    print("----------------------------------------------------------------")
    print("读取克隆文件:" + xml_name)
    DOMTree = xml.dom.minidom.parse(xml_name)  # 解析克隆结果的xml文件
    collection = DOMTree.documentElement  # 获取文档父节点
    summary = collection.getElementsByTagName("summary")[0]  # 获取总结部分
    totalRawLineCount = summary.getAttribute("totalRawLineCount")  # 获取代码总行数
    totalFileCount = summary.getAttribute("totalFileCount")  # 获取文件数量
    # 获取克隆组的节点列表
    dups = collection.getElementsByTagName("set")
    if not len(dups) > 0:  # 如果没有克隆信息，直接退出
        return
    dup_dic= {}  # 用于存储读取到的克隆信息
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
    print("克隆片段行数与模块分布情况计算完成")
    ver = xml_name.split('/')[-1].replace('.xml', '')  # 加入版本名
    module_result = add_dict(module_result, 'dupFileCount', int(len(file_list)))  # 将出现克隆的文件数加入结果中
    module_result = add_dict(module_result, 'totalFileCount', int(totalFileCount))  # 结果中加入源文件数
    module_result = add_dict(module_result, 'totalRawLineCount', int(totalRawLineCount))  # 结果中加入源代码数
    module_result = add_dict(module_result, 'ver', ver)  # 加入项目名以及版本号
    sum_results.append(module_result)  # 将当前版本的克隆信息加入到总数据列表中
    print("完成对克隆文件" + xml_name + "的克隆分析")
    print("-------------------------------------------------------------------")


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
        # print(file)
        if not ".xml" in file:
            continue
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
    clone_path = os.path.join(os.getcwd(), "clone_xml")
    sum_results = []  # 模块分类的结果，存放了所有检测版本的结果
    for dirpath in os.scandir(clone_path):
        if dirpath.is_dir():
            print(f"Clone classification of the [{dirpath.name}] project is in progress...")
            process_files(dirpath.path, process_file)
            save_name = os.path.join(os.getcwd(), f'results/{dirpath.name}_dup_results.xlsx')
            if not len(sum_results) > 0:
                continue
            write_in_xsl.result_out(save_name, sum_results)
            sum_results.clear()  # 清空结果列表以便于下一个项目的处理