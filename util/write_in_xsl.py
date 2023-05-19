# 将结果保存到xsl文件中
import xlwt


def module_result_output(save_name, sum_results):
    # 创建工作簿
    wb = xlwt.Workbook(encoding='utf-8')
    # 创建工作表
    ws = wb.add_sheet("summary")
    # 写入数据
    name_list = ["ver", "totalRawLineCount", "totalFileCount", "dupFileCount", "dup_count", "dup_line", "dup_module_count",
                 "cross_dup_count", "cross_dup_line"]  # 表头
    for name in name_list:
        ws.write(0, name_list.index(name), name)
    i = 1
    for result in sum_results:
        for name in name_list:
            if not result.get(name):
                continue
            ws.write(i, name_list.index(name), str(result[name]))
        i += 1

    # 创建第二个工作表
    wsModule = wb.add_sheet("Module")
    module_name_list = []  # 存储所有版本的克隆涉及的模块名
    for result in sum_results:  # 得到所有版本涉及的模块名
        dup_module = result['dup_module']  # 得到克隆的模块信息
        for key in list(dup_module.keys()):
            if key not in module_name_list:
                module_name_list.append(key)
    module_count_results = []  # 用于写入模块个数信息的列表
    module_line_results = []  # 用于写入模块行数信息的列表
    module_count_results.append(module_name_list)
    module_line_results.append(module_name_list)  # 加入表头
    for result in sum_results:
        dup_module = result['dup_module']
        module_result_count = [0] * len(module_name_list)  # 个数
        module_result_line = [0] * len(module_name_list)  # 行数
        for name, value in dup_module.items():
            module_result_count[module_name_list.index(name)] = value['count']
            module_result_line[module_name_list.index(name)] = value['line']
        module_count_results.append(module_result_count)
        module_line_results.append(module_result_line)
    i = 0
    for i in range(len(module_count_results)):
        for j in range(len(module_count_results[i])):
            wsModule.write(i, j, module_count_results[i][j])
    i += 1
    for ii in range(len(module_line_results)):
        for j in range(len(module_line_results[ii])):
            wsModule.write(i, j, module_line_results[ii][j])
        i += 1

    # # 创建存储跨模块的克隆信息的工作表
    # wsCross = wb.add_sheet("Cross")
    # i = j = 0
    # for result in sum_results:
    #     j = 0
    #     cross_dup_line = result['cross_results']
    #     for key, value in cross_dup_line.items():
    #         wsCross.write(i, j, key)
    #         j += 1
    #         wsCross.write(i, j, value)
    #         j += 1
    #     i += 1
    # 保存
    wb.save(save_name)


def module_result_output_bug(save_name, sum_results):
    # 创建工作簿
    wb = xlwt.Workbook(encoding='utf-8')
    # 创建工作表
    ws = wb.add_sheet("summary")
    # 写入数据
    name_list = ["ver", "bug_dup_count", "bug_line", "module_count",
                 "cross_dup_count", "cross_line_count",
                 "sum_commit_count", "bug_commit_count",
                 "clone_fix_time", "no_clone_fix_time",
                 ]  # 表头
    for name in name_list:
        ws.write(0, name_list.index(name), name)
    i = 1
    for result in sum_results:
        for name in name_list:
            if not result.get(name):
                continue
            ws.write(i, name_list.index(name), str(result[name]))
        i += 1

    # 创建第二个工作表
    wsModule = wb.add_sheet("Module")
    module_name_list = []  # 存储所有版本的克隆涉及的模块名
    for result in sum_results:  # 得到所有版本涉及的模块名
        dup_module = result['module_name_dic']  # 得到克隆的模块信息
        for key in list(dup_module.keys()):
            if key not in module_name_list:
                module_name_list.append(key)
    module_count_results = []  # 用于写入模块个数信息的列表
    module_line_results = []  # 用于写入模块行数信息的列表
    module_fix_time_results = []  # 用于写入模块修复时间信息的列表
    module_count_results.append(module_name_list)
    module_line_results.append(module_name_list)
    module_fix_time_results.append(module_name_list)  # 加入表头
    for result in sum_results:
        dup_module = result['module_name_dic']
        module_result_count = [0] * len(module_name_list)  # 个数
        module_result_line = [0] * len(module_name_list)  # 行数
        module_result_fix_time = [0] * len(module_name_list)  # 行数
        for name, value in dup_module.items():
            module_result_count[module_name_list.index(name)] = value['count']
            module_result_line[module_name_list.index(name)] = value['line']
            module_result_fix_time[module_name_list.index(name)] = str(value['fix_time']) # 保存为秒数
        module_count_results.append(module_result_count)
        module_line_results.append(module_result_line)
        module_fix_time_results.append(module_result_fix_time)

    i = 0
    for i in range(len(module_count_results)):
        for j in range(len(module_count_results[i])):
            wsModule.write(i, j, module_count_results[i][j])
    i += 1
    for ii in range(len(module_line_results)):
        for j in range(len(module_line_results[ii])):
            wsModule.write(i, j, module_line_results[ii][j])
        i += 1
    for ii in range(len(module_fix_time_results)):
        for j in range(len(module_fix_time_results[ii])):
            wsModule.write(i, j, module_fix_time_results[ii][j])
        i += 1

    # # 创建存储跨模块的克隆信息的工作表
    # wsCross = wb.add_sheet("Cross")
    # i = j = 0
    # for result in sum_results:
    #     j = 0
    #     cross_dup_line = result['cross_results']
    #     for key, value in cross_dup_line.items():
    #         wsCross.write(i, j, key)
    #         j += 1
    #         wsCross.write(i, j, value)
    #         j += 1
    #     i += 1
    # 保存
    wb.save(save_name)

