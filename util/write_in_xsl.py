import pandas as pd
from openpyxl.styles import Alignment, Font


def merge_module_list(sum_results):
    # 遍历sum_results
    if not (len(sum_results) > 0 and sum_results[0].get('change_dup_module')):
        return sum_results  # 如果不包含修改行的信息就不用合并了
    for result in sum_results:
        # 提取change_dup_module和dup_module
        change_dup_module = result['change_dup_module']
        dup_module = result['dup_module']

        # 合并两个字典
        merged_dict = {}
        for module in set(dup_module.keys()).union(change_dup_module.keys()):
            merged_dict[module] = {}
            if module in dup_module:
                merged_dict[module]['count'] = dup_module[module]['count']
                merged_dict[module]['dup_line'] = dup_module[module]['line']
            if module in change_dup_module:
                merged_dict[module]['change_line'] = change_dup_module[module]['line']

        # 将合并后的字典添加到结果中
        result['dup_module'] = merged_dict
        result.pop('change_dup_module')
    return sum_results


def extract_module_info(sum_results):
    # 获取所有的模块名
    modules = set()
    for result in sum_results:
        modules.update(result['dup_module'].keys())
    modules = sorted(list(modules))

    key_list = []
    if len(sum_results) > 0:  # 获取模块数据字典中所有的key
        key_list = list(sum_results[0]['dup_module'].values())[0].keys()

    sum_module_results = []  # 存储所有与模块相关的数据

    # 初始化列表
    for key in key_list:
        module_list = [['version'] + modules]  # 将模块名添加为表头

        # 遍历sum_results
        for result in sum_results:
            ver = result['ver']  # 第一列为版本号
            module_row = [ver]
            for module in modules:
                if module in result['dup_module']:
                    module_row.append(result['dup_module'][module][key])  # 取出相应的数据
                else:
                    module_row.append(0)
            module_list.append(module_row)
        sum_module_results.append(module_list)
    return sum_module_results


def create_excel(sum_module_results, sum_results, save_name):
    key_list = []
    if len(sum_results) > 0:  # 获取模块数据字典中所有的key
        key_list = list(sum_results[0]['dup_module'].values())[0].keys()
    sum_results = [{k: v for k, v in d.items() if k != 'dup_module'} for d in sum_results]  #
    # 创建一个Excel writer对象
    with pd.ExcelWriter(save_name, engine='openpyxl') as writer:
        # 将sum_results转换为DataFrame并写入Excel的第一个表
        df1 = pd.DataFrame(sum_results)
        df1.to_excel(writer, sheet_name='summary', index=False)

        # 创建'module'工作表
        writer.book.create_sheet('module')

        startrow = 1
        for module_results in sum_module_results:
            # 打开工作簿和工作表
            writer.sheets['module'].merge_cells(start_row=startrow, start_column=1, end_row=startrow,
                                                end_column=len(module_results[0]))
            writer.sheets['module']['A' + str(startrow)] = 'module_' + list(key_list)[sum_module_results.index(module_results)]
            writer.sheets['module']['A' + str(startrow)].alignment = Alignment(horizontal='center')
            writer.sheets['module']['A' + str(startrow)].font = Font(bold=True)

            # 将module_count_list转换为DataFrame并写入Excel的第二个表
            df = pd.DataFrame(module_results[1:], columns=module_results[0])
            df.to_excel(writer, sheet_name='module', index=False, startrow=startrow)
            startrow += len(df) + 2


def result_out(save_name, sum_results):
    sum_results = merge_module_list(sum_results)
    sum_module_results = extract_module_info(sum_results)
    create_excel(sum_module_results, sum_results, save_name)


if __name__ == '__main__':
    sum_results = [{'ver': '1.6.0', 'totalRowLine': 24, 'totalFileCount': 22, 'dupFileCount': 25, 'cross_dup_count': 23,
                    'cross_dup_line': 242,
                    'cross_results': [{'pass,sss': 2, 'safa,sadas,sfsd': 5}],
                    'dup_line': 234234,
                    'dup_count': 23,
                    'dup_module_count': 6546,
                    'dup_module': {'sdfh': {'count': 34, 'line': 'asda'},
                                   'asdasd': {'count': 24, 'line': 23}},
                    'change_dup_module': {'sdfh': {'count': 34, 'line': 'asda'},
                                          'asdasd': {'count': 24, 'line': 23}}, },
                   {'ver': '1.7.0', 'totalRowLine': 24, 'totalFileCount': 22, 'dupFileCount': 25, 'cross_dup_count': 23,
                    'cross_dup_line': 242,
                    'cross_results': [{'pass,sss': 2, 'safa,sadas,sfsd': 5}],
                    'dup_line': 234234,
                    'dup_count': 23,
                    'dup_module_count': 6546,
                    'dup_module': {'adsasd': {'count': 34, 'line': 2423},
                                   'asdasd': {'count': 12, 'line': 643}},
                    'change_dup_module': {'adsasd': {'count': 34, 'line': 'asda'},
                                          'asdasd': {'count': 24, 'line': 23}}, },
                   ]
    sum_results = merge_module_list(sum_results)
    sum_module_results = extract_module_info(sum_results)
    create_excel(sum_module_results, sum_results, 'output.xlsx')
