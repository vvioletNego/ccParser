# 用于克隆的模块分类计数以及计算LOC
import collections
import datetime
import re


# 从文件路径中分离出包名，以便统计各模块的克隆数
def get_module_name(sourceFile):
    pattern = "modules\\\\(\w+)|ros\\\\src\\\\(\w+)"  # 匹配模块名的前缀 apollo是modules目录下，autoware是src目录下
    result = re.findall(pattern, sourceFile)
    module_name = result[0][0] if not result[0][0] == "" else result[0][1]
    if module_name == "computing":  # autoware的感知和规划模块都放在computing大模块下
        pattern = "computing\\\\(\w+)"
        result = re.findall(pattern, sourceFile)
        module_name = result[0]
    if module_name.find('perception') > -1:
        # 前期包中存在一个third_party_perception，虽然在1.5.0后鼓励使用perception取代，但是一直保留所以都归类为perception
        module_name = 'perception'
    if module_name.find('canbus') > -1:
        # 8.0.0出现了一个canbus_vehicle归类为canbus
        module_name = 'canbus'
    return module_name


def sort_module(result):  # 统计共同修改的克隆类涉及的模块情况
    dup_total_line_count = 0  # 记录总代码数
    file_dup = {}  # 用于统计代码数
    module_name_dic = {}  # 存储克隆所在包名以及代码行数
    cross_results = []  # 存储跨模块的包名
    cross_dup_list = []  # 存储所有的跨模块克隆，用于计算代码行数
    for index, clone_info_list in result.items():
        module_name_list = []  # 用于存储当前克隆类中涉及的模块名
        cross_dup = []  # 用于存储跨模块的代码克隆片段信息
        for clone_info in clone_info_list:
            sourcefile = clone_info['sourcefile']  # 得到该克隆结果的文件路径
            if not file_dup.get(sourcefile):
                file_dup[sourcefile] = []
            startLineNumber = int(clone_info.get("startLineNumber"))  # 开始行
            endLineNumber = int(clone_info.get("endLineNumber"))  # 结束行
            cross_dup.append({'sourcefile': sourcefile, 'start': startLineNumber, 'end': endLineNumber})
            # 将该克隆片段的行号信息存入，以备后续计算行数用
            flag = True  # 执行并集函数的标志
            while flag:  # 一直执行求并集的函数直到剩下的里面的没有交集
                flag, startLineNumber, endLineNumber = merge_line(file_dup[sourcefile], startLineNumber, endLineNumber)
            file_dup[sourcefile].append({'start': startLineNumber, 'end': endLineNumber})  # 将求得并集的元素塞回
            moduleName = get_module_name(sourcefile)  # 从文件路径中分离出包名
            module_name_list.append(moduleName)  # 将包名存储到列表中
            if not module_name_dic.get(moduleName):
                module_name_dic[moduleName] = {'count': 0, 'line': 0}
        module_name_list = list(set(module_name_list))  # 去掉重复的模块名
        module_name_list.sort()  # 按照字母顺序排序,以便后续统计跨模块数
        # 记录该克隆所涉及模块出现的次数和代码行数
        for moduleName in module_name_list:
            module_name_dic[moduleName]['count'] += 1  # 该模块的克隆数增加
        if not len(module_name_list) == 1:  # 如果克隆结果中涉及的模块数大于一
            cross_results.append(','.join(module_name_list))  # 将跨模块的包名信息存储
            cross_dup_list.extend(cross_dup)  # 将跨模块的克隆类的信息存储到计算跨模块的克隆行数的列表中

    for file, dup in file_dup.items():
        # 将文件中的克隆行信息按照开始行号排序
        file_dup[file] = sorted(dup, key=lambda x: x['start'])
    for sourcefile, index_list in file_dup.items():
        # 计算克隆涉及的行数
        moduleName = get_module_name(sourcefile)
        for index in index_list:
            module_name_dic[moduleName]['line'] += index['end'] - index['start'] + 1
            dup_total_line_count += index['end'] - index['start'] + 1
    # 计算跨模块克隆的代码行数
    cross_line_count = 0
    cross_line_dic = {}  # 跨模块的文件名对应的克隆信息
    for dup in cross_dup_list:
        sourceFile = dup['sourcefile']
        if not cross_line_dic.get(sourceFile):
            cross_line_dic[sourceFile] = []
        startLineNumber = dup['start']
        endLineNumber = dup['end']
        flag = True
        while flag:
            flag, startLineNumber, endLineNumber = merge_line(cross_line_dic[sourceFile], startLineNumber,
                                                              endLineNumber)
        cross_line_dic[sourceFile].append({'start': startLineNumber, 'end': endLineNumber})
    for index_list in cross_line_dic.values():
        for index in index_list:
            cross_line_count += index['end'] - index['start'] + 1
    cross_dup_count = len(cross_results)  # 跨模块的克隆个数
    cross_results = dict(collections.Counter(cross_results))  # 统计出现的跨模块克隆数
    return {'cross_dup_count': cross_dup_count,  # 跨模块克隆数
            'cross_dup_line': cross_line_count,  # 跨模块克隆的代码行数
            'cross_results': cross_results,  # 跨模块的具体包名
            'dup_line': dup_total_line_count,  # 克隆的代码行数
            'dup_count': len(result),  # 克隆个数
            'dup_module_count': len(module_name_dic),  # 克隆涉及模块数
            'dup_module': module_name_dic,  # 克隆的模块分布数据
            }


def sort_module_bug_induce(result):  # 统计共同修改的克隆类涉及的模块情况(错误倾向克隆结果)
    dup_total_line_count = 0  # 记录总代码数
    file_dup = {}  # 用于统计代码数
    module_name_dic = {}  # 存储克隆所在包名以及代码行数
    cross_results = []  # 跨模块的包名信息
    cross_dup_list = []  # 存储所有的跨模块克隆，用于计算代码行数
    for index, clone_info_list in result.items():
        module_name_list = []  # 用于存储当前克隆类中涉及的模块名
        cross_dup = []  # 用于存储跨模块的代码克隆片段信息
        for clone_info in clone_info_list:
            sourcefile = clone_info['sourcefile']  # 得到该克隆结果的文件路径
            if not file_dup.get(sourcefile):
                file_dup[sourcefile] = []
            startLineNumber = int(clone_info.get("startLineNumber"))  # 开始行
            endLineNumber = int(clone_info.get("endLineNumber"))  # 结束行
            cross_dup.append({'sourcefile': sourcefile, 'start': startLineNumber, 'end': endLineNumber})
            flag = True  # 执行函数的标志
            while flag:  # 一直执行求并集的函数直到剩下的里面的没有交集
                flag, startLineNumber, endLineNumber = merge_line(file_dup[sourcefile], startLineNumber, endLineNumber)
            file_dup[sourcefile].append({'start': startLineNumber, 'end': endLineNumber})  # 将求得并集的元素塞回
            moduleName = get_module_name(sourcefile)  # 从文件路径中分离出包名
            module_name_list.append(moduleName)  # 将包名存储到列表中
            if not module_name_dic.get(moduleName):
                module_name_dic[moduleName] = {'count': 0, 'line': 0,
                                               'commit_index': [],  # 涉及的提交哈希值
                                               'fix_time': datetime.timedelta(seconds=0)  # 涉及的提交的修复时间
                                               }
            else:
                if clone_info['commit_index'] not in module_name_dic[moduleName]['commit_index']:
                    module_name_dic[moduleName]['commit_index'].append(clone_info['commit_index'])
                    # 在该模块涉及的提交列表中添加该克隆对应的提交哈希值
                    module_name_dic[moduleName]['fix_time'] += datetime.timedelta(
                        days=int(clone_info['fix_time'].split(',')[0]),
                        seconds=int(clone_info['fix_time'].split(',')[1]))
                    # 累加该提交对应的修复时间
                    module_name_dic[moduleName]['fix_time'] /= len(module_name_dic[moduleName]['commit_index'])
                    # 求出平均修复时间
        module_name_list = list(set(module_name_list))  # 去掉重复的模块名
        module_name_list.sort()  # 按照字母顺序排序,以便后续统计跨模块数
        # 记录涉及模块出现的次数和代码行数
        for moduleName in module_name_list:
            module_name_dic[moduleName]['count'] += 1  # 该模块的克隆数增加

        if not len(module_name_list) == 1:  # 如果克隆结果中涉及的模块数大于一
            cross_results.append(','.join(module_name_list))  # 将跨模块的包名信息存储
            cross_dup_list.extend(cross_dup)  # 将跨模块的克隆类的信息存储到计算跨模块的克隆行数的列表中

    for file, dup in file_dup.items():
        file_dup[file] = sorted(dup, key=lambda x: x['start'])
    for sourceFile, index_list in file_dup.items():
        moduleName = get_module_name(sourceFile)
        for index in index_list:
            module_name_dic[moduleName]['line'] += index['end'] - index['start'] + 1
            dup_total_line_count += index['end'] - index['start'] + 1
    # 计算跨模块克隆的代码行数
    cross_line_count = 0
    cross_line_dic = {}  # 跨模块的文件名对应的克隆信息
    for dup in cross_dup_list:
        sourceFile = dup['sourcefile']
        if not cross_line_dic.get(sourceFile):
            cross_line_dic[sourceFile] = []
        startLineNumber = dup['start']
        endLineNumber = dup['end']
        flag = True
        while flag:
            flag, startLineNumber, endLineNumber = merge_line(cross_line_dic[sourceFile], startLineNumber,
                                                                endLineNumber)
        cross_line_dic[sourceFile].append({'start': startLineNumber, 'end': endLineNumber})
    for index_list in cross_line_dic.values():
        for index in index_list:
            cross_line_count += index['end'] - index['start'] + 1
    cross_dup_count = len(cross_results)  # 跨模块的克隆个数
    cross_results = dict(collections.Counter(cross_results))  # 统计出现的跨模块克隆数
    return {'module_name_dic': module_name_dic,
            'module_count': len(module_name_dic),
            'bug_line': dup_total_line_count,
            'cross_dup_count': cross_dup_count,
            'cross_results': cross_results,
            'cross_line_count': cross_line_count,
            }


def merge_line(dup_list, startLineNumber, endLineNumber):  # 处理克隆代码段，使其开始行号和结束行号没有交集
    flag = False  # 传入的克隆列表中是否存在与之有交集的标志
    length = len(dup_list)  # 求出当前克隆列表的长度
    for i in range(length):
        index = dup_list.pop(0)  # 弹出首个元素
        start = index['start']
        end = index['end']
        if not (start > endLineNumber or end < startLineNumber):  # 开始和结束行号取并集
            startLineNumber = start if start < startLineNumber else startLineNumber
            endLineNumber = end if end > endLineNumber else endLineNumber
            flag = True
        else:
            dup_list.append(index)  # 没有交集就塞回去
    return flag, startLineNumber, endLineNumber
