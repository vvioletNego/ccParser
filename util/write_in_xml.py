# 将得到的结果写入xml文件中
import xml.dom.minidom


def bug_induce_result_block(bug_clone_result_dic, save_name):  # 错误诱导的克隆信息结果写入xml文件
    dom = xml.dom.minidom.getDOMImplementation().createDocument(None, 'Root', None)  # 创建树
    root = dom.documentElement  # 文档父节点
    for index, clone_info_list in bug_clone_result_dic.items():
        root_element = dom.createElement('bug_induce_results')  # 错误诱导结果组的父节点
        root_element.setAttribute('fingerpoint', index)  # 克隆对id
        for clone_info in clone_info_list:
            element = dom.createElement('result')  # 单条结果的节点
            element.setAttribute('startLineNumber', str(clone_info['startLineNumber']))  # 该克隆块的开始行号
            element.setAttribute('endLineNumber', str(clone_info['endLineNumber']))  # 该克隆块的结束行号
            element.setAttribute('sourcefile', clone_info['sourcefile'])  # 该克隆块的文件路径
            element.setAttribute('count', str(clone_info['count']))  # 该克隆块的提交次数
            diff_element = dom.createElement('diff')  # 详细的提交差异内容
            diff = clone_info['diff']  # 获取差异内容
            diff_element.appendChild(dom.createTextNode(diff))  # 将差异内容添加到差异节点上
            element.appendChild(diff_element)  # 将差异内容的节点添加到结果节点上
            # codes_element = dom.createElement('codes')  # 克隆块的代码内容
            # codes = clone_info['codes']  # 获取代码内容
            # codes_element.appendChild(dom.createTextNode(codes))  # 将代码内容添加到差异节点上
            # element.appendChild(codes_element)  # 将代码内容的节点添加到结果节点上
            msg_element = dom.createElement('msg')  # 详细的修改内容差异对比
            msg = clone_info['msg']  # 获取差异内容
            msg_element.appendChild(dom.createTextNode(msg))  # 将差异内容添加到差异节点上
            element.appendChild(msg_element)
            root_element.appendChild(element)
        root.appendChild(root_element)  # 将结果节点添加到文档父节点上
    summary_element = dom.createElement('summary')  # 总结节点
    summary_element.setAttribute("count", str(len(bug_clone_result_dic)))  # 错误诱导结果组的总数
    root.appendChild(summary_element)  # 将总结节点添加到文档父节点上

    # 保存文件
    with open(save_name, 'w', encoding='utf-8') as f:
        dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')


def bug_induce_result_func(bug_clone_result_dic, save_name):  # 错误诱导的克隆信息结果写入xml文件
    dom = xml.dom.minidom.getDOMImplementation().createDocument(None, 'Root', None)  # 创建树
    root = dom.documentElement  # 文档父节点
    for index, clone_info_list in bug_clone_result_dic.items():
        root_element = dom.createElement('bug_induce_results')  # 错误诱导结果组的父节点
        root_element.setAttribute('index', str(index))  # 克隆对序号
        for clone_info in clone_info_list:
            element = dom.createElement('result')  # 单条结果的节点
            element.setAttribute('function_name', clone_info['function_name'])  # 该克隆块的开始行号
            element.setAttribute('sourcefile', clone_info['sourcefile'])  # 该克隆块的文件路径
            element.setAttribute('count', str(clone_info['count']))  # 该克隆块的提交次数
            root_element.appendChild(element)
        root.appendChild(root_element)  # 将结果节点添加到文档父节点上
    summary_element = dom.createElement('summary')  # 总结节点
    summary_element.setAttribute("count", str(len(bug_clone_result_dic)))  # 错误诱导结果组的总数
    root.appendChild(summary_element)  # 将总结节点添加到文档父节点上

    # 保存文件
    with open(save_name, 'w', encoding='utf-8') as f:
        dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')


def comodify_result_xml_func(comodify_func_result, save_name):  # 将共同修改的结果存入xml文件中
    dom = xml.dom.minidom.getDOMImplementation().createDocument(None, 'Comodify', None)  # 创建树
    root = dom.documentElement  # 文档父节点
    for index, comodify_func_list in comodify_func_result.items():
        root_element = dom.createElement('results')    # 共同修改结果组的父节点
        root_element.setAttribute('count', str(len(comodify_func_list)))  # 该共同修改结果内包含的函数数量
        for comodify_func in comodify_func_list:
            element = dom.createElement('result')  # 单条共同修改结果的节点
            sourcefile = comodify_func['sourcefile']  # 获取该共同修改结果中的文件路径
            element.setAttribute('sourcefile', sourcefile)  # 文件路径
            start = str(comodify_func['start'])  # 获取该共同修改结果中的开始行号
            element.setAttribute('start', start)  # 开始行号
            end = str(comodify_func['end'])  # 获取该共同修改结果中的结束行号
            element.setAttribute('end', end)  # 结束行号
            count = str(comodify_func['count'])  # 获取该共同修改结果中的被修改的次数
            element.setAttribute('count', count)  # 修改次数
            function_element = dom.createElement('function')  # 函数内容节点
            function_name = comodify_func['function_name']  # 获取该共同修改结果中的函数名
            function_element.setAttribute('function_name', function_name)  # 函数名
            diff_element = dom.createElement('diff')  # 详细的修改内容差异对比
            diff = comodify_func['diff']  # 获取差异内容
            diff_element.appendChild(dom.createTextNode(diff))  # 将差异内容添加到差异节点上
            function_element.appendChild(diff_element)  # 将差异内容的节点添加到函数节点上
            element.appendChild(function_element)  # 将函数节点添加到结果节点上
            # old_code_element = dom.createElement('old_code')  # 旧代码的节点
            # old_code = comodify_func['old_code']  # 获取该共同修改结果中的修改前的代码
            # old_code_element.appendChild(dom.createTextNode(old_code))
            # element.appendChild(old_code_element)  # 将旧代码的节点添加到结果节点上
            # new_code_element = dom.createElement('new_code')  # 新代码的节点
            # new_code = comodify_func['new_code']  # 获取该共同修改结果中的修改后的代码
            # new_code_element.appendChild(dom.createTextNode(new_code))
            # element.appendChild(new_code_element)  # 将新代码的节点添加到结果节点上
            root_element.appendChild(element)
        root.appendChild(root_element)  # 将结果节点添加到文档父节点上
    summary_element = dom.createElement('summary')  # 总结节点
    summary_element.setAttribute("count", str(len(comodify_func_result)))  # 共同修改组的总数
    root.appendChild(summary_element)  # 将总结节点添加到文档父节点上

    # 保存文件
    with open(save_name, 'w', encoding='utf-8') as f:
        dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')


def comodify_result_xml_block(comodify_func_result, save_name):  # 将共同修改的结果存入xml文件中
    dom = xml.dom.minidom.getDOMImplementation().createDocument(None, 'Comodify', None)  # 创建树
    root = dom.documentElement  # 文档父节点
    for index, comodify_func_list in comodify_func_result.items():
        root_element = dom.createElement('results')    # 共同修改结果组的父节点
        root_element.setAttribute('count', str(len(comodify_func_list)))  # 该共同修改结果内包含的函数数量
        for comodify_func in comodify_func_list:
            element = dom.createElement('result')  # 单条共同修改结果的节点
            # sourcefile = comodify_func['sourcefile']  # 获取该共同修改结果中的文件名
            # element.setAttribute('sourcefile', sourcefile)  # 文件路径
            old_path = comodify_func['old_path']  # 获取该共同修改结果中的文件路径
            element.setAttribute('old_path', old_path)  # 文件路径
            startLineNumber = str(comodify_func['startLineNumber'])  # 获取该共同修改结果中的开始行号
            element.setAttribute('startLineNumber', startLineNumber)  # 开始行号
            endLineNumber = str(comodify_func['endLineNumber'])  # 获取该共同修改结果中的结束行号
            element.setAttribute('endLineNumber', endLineNumber)  # 结束行号
            diff_element = dom.createElement('diff')  # 详细的修改内容差异对比
            diff = comodify_func['diff']  # 获取差异内容
            diff_element.appendChild(dom.createTextNode(diff))  # 将差异内容添加到差异节点上
            element.appendChild(diff_element)
            # old_code_element = dom.createElement('old_code')  # 旧代码的节点
            # old_code = comodify_func['old_code']  # 获取该共同修改结果中的修改前的代码
            # old_code_element.appendChild(dom.createTextNode(old_code))
            # element.appendChild(old_code_element)  # 将旧代码的节点添加到结果节点上
            # new_code_element = dom.createElement('new_code')  # 新代码的节点
            # new_code = comodify_func['new_code']  # 获取该共同修改结果中的修改后的代码
            # new_code_element.appendChild(dom.createTextNode(new_code))
            # element.appendChild(new_code_element)  # 将新代码的节点添加到结果节点上
            root_element.appendChild(element)
        root.appendChild(root_element)  # 将结果节点添加到文档父节点上
    summary_element = dom.createElement('summary')  # 总结节点
    summary_element.setAttribute("count", str(len(comodify_func_result)))  # 共同修改组的总数
    root.appendChild(summary_element)  # 将总结节点添加到文档父节点上

    # 保存文件
    with open(save_name, 'w', encoding='utf-8') as f:
        dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')