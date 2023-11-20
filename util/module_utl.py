# 用于克隆的模块分类计数以及计算LOC
import collections
import datetime
import re

# 这里默认参数定义了针对Apollo和Autoware的模块分类的pattern和特殊情况，如果希望使用自定义的规则可以传入相应的参数
pattern="modules\\\\(\w+)|ros\\\\src\\\\(\w+)"
special_cases = {
            "computing": "computing\\\\(\w+)",
            "perception": 'perception',
            "canbus": 'canbus'
        }


# 从文件路径中分离出包名，以便统计各模块的克隆数
def get_module_name(sourceFile):
    result = re.findall(pattern, sourceFile)
    module_name = result[0][0] if not result[0][0] == "" else result[0][1]

    for case, new_pattern in special_cases.items():
        if module_name == case:
            result = re.findall(new_pattern, sourceFile)
            module_name = result[0]
        if module_name.find(case) > -1:
            module_name = case

    return module_name


def sort_module(result):  # 统计共同修改的克隆类涉及的模块情况
    dup_total_line_count = 0  # 克隆的总代码行数
    file_dup = collections.defaultdict(list)  # 克隆涉及的文件数
    module_name_dic = collections.defaultdict(lambda: {'count': 0, 'line': 0})  # 克隆涉及的模块名称
    cross_results = []  # 跨模块克隆
    cross_dup_list = []
    for index, clone_info_list in result.items():
        module_name_list = []
        cross_dup = []
        for clone_info in clone_info_list:
            sourcefile = clone_info['sourcefile']  # 获取当前片段的文件路径
            startLineNumber = int(clone_info.get("startLineNumber"))  # 获取当前片段的开始行号
            endLineNumber = int(clone_info.get("endLineNumber"))  # 获取当前片段的结束行号
            cross_dup.append({'sourcefile': sourcefile, 'start': startLineNumber, 'end': endLineNumber})
            file_dup[sourcefile].append({'start': startLineNumber, 'end': endLineNumber})
            moduleName = get_module_name(sourcefile)
            module_name_list.append(moduleName)
            file_dup[sourcefile] = merge_line(file_dup[sourcefile])
            module_name_list = sorted(list(set(module_name_list)))
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

    return {
        'dup_line': dup_total_line_count,
        'dup_count': len(result),
        'dup_module_count': len(module_name_dic),
        'cross_dup_count': cross_dup_count,
        'cross_dup_line': cross_line_count,
        'cross_results': cross_results,
        'dup_module': dict(module_name_dic),
    }


def sort_module_bug_induce(result):  # 统计共同修改的克隆类涉及的模块情况(错误倾向克隆结果)
    dup_total_line_count = 0
    file_dup = collections.defaultdict(list)
    module_name_dic = collections.defaultdict(
        lambda: {'count': 0, 'line': 0, 'commit_index': [], 'fix_time': datetime.timedelta(seconds=0)})
    cross_results = []
    cross_dup_list = []
    for index, clone_info_list in result.items():
        module_name_list = []
        cross_dup = []
        for clone_info in clone_info_list:
            sourcefile = clone_info['sourcefile']
            startLineNumber = int(clone_info.get("startLineNumber"))
            endLineNumber = int(clone_info.get("endLineNumber"))
            cross_dup.append({'sourcefile': sourcefile, 'start': startLineNumber, 'end': endLineNumber})
            file_dup[sourcefile].append({'start': startLineNumber, 'end': endLineNumber})
            moduleName = get_module_name(sourcefile)
            module_name_list.append(moduleName)
            if clone_info['commit_index'] not in module_name_dic[moduleName]['commit_index']:
                module_name_dic[moduleName]['commit_index'].append(clone_info['commit_index'])
                module_name_dic[moduleName]['fix_time'] += datetime.timedelta(
                    days=int(clone_info['fix_time'].split(',')[0]), seconds=int(clone_info['fix_time'].split(',')[1]))
                module_name_dic[moduleName]['fix_time'] /= len(module_name_dic[moduleName]['commit_index'])
            file_dup[sourcefile] = merge_line(file_dup[sourcefile])
            module_name_list = sorted(list(set(module_name_list)))
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
    # 计算跨模块克隆的代码行数
    cross_line_count = calculate_cross_line_count(cross_dup_list)
    cross_dup_count = len(cross_results)
    cross_results = dict(collections.Counter(cross_results))

    for value in module_name_dic.values():  # 结果中不需要提交的id列表,直接删除
        value['fix_time'] = str(value['fix_time'])  # 以字符串形式存储在字典中
        if 'commit_index' in value:
            del value['commit_index']

    return {'dup_module': module_name_dic,
            'module_count': len(module_name_dic),
            'bug_line': dup_total_line_count,
            'cross_dup_count': cross_dup_count,
            'cross_results': cross_results,
            'cross_line_count': cross_line_count,
            }


def merge_line(dup_list):
    dup_list.sort(key=lambda x: x['start'])  # 按照开始行号排序
    merged = [dup_list[0]]
    for current in dup_list:
        last = merged[-1]
        if current['start'] <= last['end']:
            last['end'] = max(last['end'], current['end'])  # 合并有交集的范围
        else:
            merged.append(current)
    return merged


def calculate_cross_line_count(cross_dup_list):
    cross_line_count = 0
    cross_line_dic = collections.defaultdict(list)
    for dup in cross_dup_list:
        sourceFile = dup['sourcefile']
        startLineNumber = dup['start']
        endLineNumber = dup['end']
        cross_line_dic[sourceFile].append({'start': startLineNumber, 'end': endLineNumber})
    for sourceFile, index_list in cross_line_dic.items():
        cross_line_dic[sourceFile] = merge_line(index_list)
    for index_list in cross_line_dic.values():
        for index in index_list:
            cross_line_count += index['end'] - index['start'] + 1
    return cross_line_count