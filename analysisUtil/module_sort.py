# 统计克隆结果中涉及的模块数以及跨模块克隆的情况
import os
from xml.dom.minidom import parse
import xml.dom.minidom
import re
from util import module_utl, write_in_xsl


# sum_results = []  # 检测所有的版本的克隆结果

def module_parse(xml_name, sum_results):
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
    module_result['totalRawLineCount'] = totalRawLineCount  # 结果中加入源代码数
    module_result['totalFileCount'] = totalFileCount  # 结果中加入源文件数
    module_result['dupFileCount'] = len(file_list)  # 将出现克隆的文件数加入结果中
    module_result['ver'] = xml_name.split('\\')[-1].replace('.xml', '')  # 加入版本名
    sum_results.append(module_result)  # 将当前版本的克隆信息加入到总数据列表中


def batch_process(path):  # 读取给定文件夹下所有的克隆文件并分析
    sum_results = []
    for filepath, dirnames, filenames in os.walk(path):
        if path.find("autoware") > -1:  # 如果是autoware项目的文件路径需要额外进行排序因为字符串中的10会排在2的前面
            pattern = re.compile(r'\d+')
            filenames.sort(key=lambda x: int(pattern.findall(x)[1]))  # 对读取的路径进行排序
        for filename in filenames:
            xml_name = os.path.join(filepath, filename)
            module_parse(xml_name, sum_results)
    save_name = "../results/apollo_" if path.find("apollo") > -1 else "../results/autoware_"
    write_in_xsl.module_result_output(save_name + "dup_results.xls", sum_results)


if __name__ == "__main__":
    path = os.getcwd()  # 获取当前目录
    parent = os.path.join(path, os.pardir)  # 父目录
    path = os.path.abspath(parent)  # 当前目录的父目录
    path += "\\clone_xml"  # 进入存储xml文件的文件夹
    for filepath, dirnames, filenames in os.walk(path):
        for dirname in dirnames:
            d_path = path + "\\" + dirname
            batch_process(d_path)
