# 读取克隆结果xml文件
import re
import xml.dom.minidom


# 从文件路径中分离出包名，以便统计各模块的克隆数
def get_module_name(sourceFile):
    pattern = "modules\\\\[a-z]+|src\\\\[a-z]+"  # 匹配模块名的前缀 apollo是modules目录下，autoware是src目录下
    result = re.findall(pattern, sourceFile)
    module_name = result[0].split('\\')[1]
    # print(module_name)
    return module_name


def read_clone_block(xml_name):  # 读取block粒度的克隆文件
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    collection = DOMTree.documentElement

    # 获取xml文件中的克隆对信息节点列表
    dups = collection.getElementsByTagName("set")
    clone_dic = {}  # 存储获取的克隆对信息字典，以文件路径为key，便于提高检索速度

    for dup in dups:
        blocks = dup.getElementsByTagName('block')  # 获取克隆块信息所在元素
        fingerprint = dup.getAttribute("fingerprint")  # 获取克隆对的id
        for block in blocks:
            sourceFile = block.getAttribute("sourceFile")  # 获取该克隆结果的文件路径
            old_sourcefile = sourceFile  # 保存旧的文件路径，以便打开源代码时使用
            if '\\modules' in sourceFile:
                module_index = sourceFile.find("modules")  # 为了后期的文件路径比较将module包后的文件路径截取
            elif '\\ros' in sourceFile:
                module_index = sourceFile.find("ros")
            else:
                module_index = 0
            sourceFile = sourceFile[module_index:].replace("\\", "/")  # 获取文件路径
            sourceFile = sourceFile.split("/")[-1]  # 将文件路径全部提取为文件名
            # if "apollo" in xml_name:  # 如果是apollo项目的文件路径修改文件后缀名,因为克隆结果的文件后缀是cpp，但是源文件后缀名是cc
            #     sourceFile = sourceFile.replace("cpp", "cc")
            # moduleName = get_module_name(sourceFile)  # 从文件路径中分离出包名
            startLineNumber = int(block.getAttribute("startLineNumber"))  # 开始行
            endLineNumber = int(block.getAttribute("endLineNumber"))  # 结束行
            if not clone_dic.get(sourceFile):
                clone_dic[sourceFile] = []  # 如果没有当前文件路径的克隆信息，创建一个新的空列表用于存储
            clone_dic[sourceFile].append({'startLineNumber': startLineNumber, 'endLineNumber': endLineNumber,
                                          'fingerprint': fingerprint,
                                          'old_sourcefile': old_sourcefile
                                          })  # 将当前克隆信息存储到列表中
            # clone_dic[sourceFile].sort(key=lambda clone: clone["startLineNumber"])  # 按照开始行号进行升序排列
    return clone_dic


def read_clone_func(xml_name):  # 读取function粒度的克隆文件
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    root = DOMTree.documentElement
    clone_file_dic = {}  # 存储克隆对的字典
    dups = root.getElementsByTagName("dup")  # 获取文档的子节点，包含了克隆对信息
    for dup in dups:
        # print("读取" + str(dups.index(dup)) + "号克隆对")
        # if not isinstance(dup, xml.dom.minidom.Element):  # 跳过中间的换行的文本节点
        #     continue
        # count = dup.getAttribute("count")  # 获取克隆对内包含的函数信息
        source_elements = dup.getElementsByTagName("source")  # 获取存储了文件信息的节点
        i = dups.index(dup)  # 获取目前的列表索引
        for source in source_elements:
            sourceFile = source.getAttribute("sourseFile")  # 获取文件路径
            start = source.getAttribute("clone_start")  # 获取克隆开始行号
            end = source.getAttribute("clone_end")  # 获取克隆结束行号
            if 'apollo' in xml_name:
                module_index = sourceFile.find("modules")  # 为了后期的文件路径比较将module包后的文件路径截取
            else:
                module_index = sourceFile.find("ros")
                if not sourceFile.find("ros") > -1:
                    module_index = 0
            sourceFile = sourceFile[module_index:].replace("\\", "/")  # 获取文件路径
            # if "apollo" in xml_name and ".cc" in xml_name:  # 如果是apollo项目的文件路径修改文件后缀名,可能出现后缀名的
            #     sourceFile = sourceFile.replace("cc", "cpp")
            sourceFile = sourceFile.split("/")[-1]  # 将文件路径全部提取为文件名
            code_element = source.getElementsByTagName("code")[0]  # 获取函数信息节点
            code = code_element.childNodes[0].data  # 获取函数代码
            function_name = code_element.getAttribute("function_name").replace(" ", "")  # 获取函数名，将空白字符全部去掉，便于比较
            if not clone_file_dic.get(sourceFile):  # 如果在函数信息中没有查到文件路径对应的函数信息
                clone_file_dic[sourceFile] = {}  # 创建该文件路径对应的新字典，key为函数名
            if not clone_file_dic.get(sourceFile).get(function_name):
                clone_file_dic[sourceFile][function_name] = {}
                clone_file_dic[sourceFile][function_name]['code'] = code  # 存储该函数代码内容
                clone_file_dic[sourceFile][function_name]['clone'] = []  # 创建由该文件路径以及函数名对应的列表
            clone_file_dic.get(sourceFile).get(function_name)['clone'].append({'index': i, 'start': start, 'end': end})
            # clone_file_dic.get(sourceFile).get(function_name)['clone'].sort(key=lambda clone: clone["start"])
            # 按照开始行号进行排序
            # 将当前函数信息存入文件路径对应的列表中
    # for file, clone_fun_list in clone_file_dic.items():
    #     if len(clone_fun_list) > 1:
    #         clone_file_dic[file] = [dict(t) for t in set([tuple(d.items()) for d in clone_fun_list])]  # 去重
    return clone_file_dic  # 将克隆信息列表以及文件路径对应序号的字典返回


def sort_count(L):  # 将列表中元素分组然后计数
    M = []
    for i in range(len(L)):
        n = L[i].copy()
        # n["count"] = L.count(L[i])
        if not n in M:
            M.append(n)
    return M


def read_clone_block_new(xml_name):  # 读取block粒度的克隆文件
    # 使用minidom解析器打开 XML 文档
    DOMTree = xml.dom.minidom.parse(xml_name)
    collection = DOMTree.documentElement

    # 获取xml文件中的克隆对信息节点列表
    dups = collection.getElementsByTagName("set")
    clone_dic = {}  # 存储获取的克隆对信息字典，以文件路径为key，便于提高检索速度
    file_block_list = []  # 存储处理过后的克隆类的列表
    for dup in dups:
        blocks = dup.getElementsByTagName('block')  # 获取克隆块信息所在元素
        fingerprint = dup.getAttribute("fingerprint")  # 获取克隆对的id
        dup_list = []  # 装处理后的克隆类的列表
        for block in blocks:
            sourceFile = block.getAttribute("sourceFile")  # 获取该克隆结果的文件路径
            old_sourcefile = sourceFile  # 保存旧的文件路径，以便打开源代码时使用
            startLineNumber = int(block.getAttribute("startLineNumber"))  # 开始行
            endLineNumber = int(block.getAttribute("endLineNumber"))  # 结束行
            flag = False  # 判断与已存的克隆块有交集的标志
            if len(dup_list) > 0:
                length = len(dup_list)  # 先保留列表长度
                for i in range(length):
                    dup_block = dup_list.pop()  # 弹出需要比较的第一个克隆块
                    if not dup_block['old_sourcefile'] == old_sourcefile:  # 如果文件路径对不上，重新放入列表
                        dup_list.append(dup_block)
                        continue
                    start = dup_block["startLineNumber"]
                    end = dup_block['endLineNumber']
                    if not (startLineNumber > end or endLineNumber < start):  # 如果开始和结束行号有交集，取它俩的并集
                        dup_block['startLineNumber'] = startLineNumber if startLineNumber < start else start  # 取最小的行号
                        dup_block['endLineNumber'] = endLineNumber if endLineNumber > end else end  # 取最大的行号
                        flag = True  # 标志设为真
                    dup_list.append(dup_block)  # 不管有没有交集都要重新放回列表
            if not flag:  # 如果和现存的克隆块没有交集就作为新的克隆块加入列表
                dup_list.append({'startLineNumber': startLineNumber, 'endLineNumber': endLineNumber,
                                                       'fingerprint': fingerprint,
                                                       'old_sourcefile': old_sourcefile
                                })
        if len(dup_list) > 1:  # 经过了上述去重处理后仍然存在两个及以上的克隆块的话就加入到克隆类的列表中
            file_block_list.append(dup_list)

    for dup in file_block_list:
        for block in dup:
            sourceFile = block.get("old_sourcefile")  # 获取文件路径
            if '/module' in xml_name:
                module_index = sourceFile.find("modules")  # 为了后期的文件路径比较将module包后的文件路径截取
            elif '/ros' in xml_name:
                module_index = sourceFile.find("ros")
            else:
                module_index = 0
            sourceFile = sourceFile[module_index:].replace("\\", "/")  # 获取文件路径
            sourceFile = sourceFile.split("/")[-1]  # 将文件路径全部提取为文件名
            if "apollo" in xml_name:  # 如果是apollo项目的文件路径修改文件后缀名,因为克隆结果的文件后缀是cpp，但是源文件后缀名是cc
                sourceFile = sourceFile.replace("cpp", "cc")
            sourceFile = sourceFile.split("/")[-1]  # 将文件路径全部提取为文件名
            if not clone_dic.get(sourceFile):
                clone_dic[sourceFile] = []  # 如果没有当前文件路径的克隆信息，创建一个新的空列表用于存储
            clone_dic[sourceFile].append({'startLineNumber': block.get("startLineNumber"),
                                          'endLineNumber': block.get("endLineNumber"),
                                          'fingerprint': block.get("fingerprint"),
                                          'old_sourcefile': block.get("old_sourcefile")
                                          })  # 将当前克隆信息存储到列表中

    return clone_dic


if __name__ == '__main__':
    # read_clone_block_new("../xml_src/h-detect/apollo/apollo-8.0.0-dup.xml")
    read_clone_block("../xml_src/h-detect/autoware/autoware-1.14.0-dup.xml")