# 抓取相应版本的错误修复提交并保存
import datetime
import xml.dom.minidom as minidom
from pydriller import Repository
from pydriller import git


def get_commit(save_name, rep_dir, dt1, dt2):
    dom = minidom.getDOMImplementation().createDocument(None, 'Root', None)  # 创建树
    root = dom.documentElement  # 创建root节点
    gr = git.Git(rep_dir)  # 获取仓库
    parse_repeat_commit = []  # 用于提交去重
    datetime1 = datetime.datetime(dt1.split(',')[0], dt1.split(',')[1], dt1.split(',')[2], dt1.split(',')[3],
                            dt1.split(',')[4], dt1.split(',')[5])
    datetime2 = datetime.datetime(dt2.split(',')[0], dt2.split(',')[1], dt2.split(',')[2], dt2.split(',')[3],
                                  dt2.split(',')[4], dt2.split(',')[5])
    rep = Repository(rep_dir,
                     since=datetime1,
                     to=datetime2,
                     include_remotes=True).traverse_commits()
    for commit in rep:
        commit_msg = commit.msg  # 获取提交描述
        commit_date = commit.committer_date  # 获取提交日期
        if [commit_msg, commit_date] in parse_repeat_commit:
            continue  # 筛去重复提交
        else:
            parse_repeat_commit.append([commit_msg, commit_date])
        # 筛出错误提交
        corrective_word_list = ['bug', 'fix', 'wrong', 'error', 'fail', 'problem', 'patch', 'correct']
        bug_flag = False  # 当前提交是否与错误修复相关的标志
        for word in corrective_word_list:
            if word.lower() in commit_msg.lower():
                bug_flag = True
                break
        if not bug_flag:
            continue
        # 筛出C++源文件与头文件
        try:
            files = commit.modified_files  # 获取此次提交修改的文件列表
            commit_files = []  # 筛选出修改的C++头文件和源文件
            commit_names = []  # 筛选出的文件路径
            for file in files:
                if file.old_path and ('.cc' in file.old_path or '.cpp' in file.old_path or '.h' in file.old_path):
                    commit_files.append(file)  # 将涉及了cpp文件和头文件的提交文件存储
                    commit_names.append(file.old_path)  # 将该文件路径加入到列表中
            if not len(commit_files) > 0:  # 如果当前提交中不包含cpp源文件和头文件的修改就跳过
                continue
            print(commit_date)
        except:  # 可能遇到提交丢失，直接跳过该提交
            continue

        # xml写入
        root_element = dom.createElement('commit')  # 提交信息的父节点
        root_element.setAttribute('hash', commit.hash)  # 提交的哈希值
        add_text_element(dom, root_element, commit_msg, 'msg')  # 添加描述信息的节点
        files_element = dom.createElement('modified_files')  # 改变文件信息的节点
        # 获取修复时间
        buggy_commits = gr.get_commits_last_modified_lines(commit)  # 得到最后修改该提交中修改行的所有提交
        commit_fix_time = datetime.timedelta(seconds=0)  # 当前提交对所有相关文件的平均修复时间
        alter_commit_count = 0  # 之前与该提交修复的文件相关的的所有提交数
        for file_path, modified_commit_id_list in buggy_commits.items():
            if file_path not in commit_names:  # 筛出与本次提交中文件路径一致的提交
                continue
            alter_commit_count += len(modified_commit_id_list)  # 总提交数加上该文件的提交数
            for modified_commit_id in buggy_commits[file_path]:  # 遍历修改了该文件的所有提交
                commit_alter = gr.get_commit(modified_commit_id)  # 获取该提交
                commit_alter_date = commit_alter.committer_date  # 获取该提交的提交时间
                fix_time = commit_date - commit_alter_date  # 获取该文件该次提交到本次提交之间的时间差
                commit_fix_time += fix_time  # 将该时间差加入总修复时间中
        if not alter_commit_count == 0:
            commit_fix_time /= alter_commit_count  # 求出当前提交的平均修复时间
        # 将提交文件信息写入XML文件
        root_element.setAttribute('fix_time', (','.join([str(commit_fix_time.days),
                                                         str(commit_fix_time.seconds)])))
        # 该提交的平均修复时间
        for file in commit_files:
            file_element = dom.createElement('file')  # 单条改变文件信息的节点
            old_path = file.old_path
            new_path = file.new_path
            file_element.setAttribute('old_path', old_path)  # 旧文件路径
            file_element.setAttribute('new_path', new_path)  # 新文件路径
            diff = file.diff  # 该文件的差异内容
            add_text_element(dom, file_element, diff, 'diff')  # 添加差异信息的节点
            old_file = file.content_before  # 该提交修改前的文件内容
            if old_file:
                add_text_element(dom, file_element, old_file.decode("utf-8", 'ignore'), 'old_file')
            else:
                add_text_element(dom, file_element, "", 'old_file')
            files_element.appendChild(file_element)  # 将单条文件信息添加到文件信息的节点上
        root_element.appendChild(files_element)  # 将文件信息添加到该条提交节点上
        root.appendChild(root_element)  # 将提交信息节点添加到文档父节点上

    with open(save_name, 'w', encoding='utf-8') as f:
        dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')


def add_text_element(dom, root_element, text, element_name):  # 用于添加需要的文本节点
    element = dom.createElement(element_name)  # 生成相应的节点
    element.appendChild(dom.createTextNode(text))  # 添加加入节点的文本
    root_element.appendChild(element)  # 在父节点加入这个文本节点


if __name__ == '__main__':
    save_name = "../time_commit"  # 提交存储的位置
    rep_dir = input("Input your repo dir:")  # 输入分析的项目仓库所在位置
    save_name = save_name + 'apollo/' if 'apollo' in rep_dir else save_name + 'autoware/'
    # 根据项目仓库的名称存到相应的目录下
    dt1 = input("Input the commit start datetime:(year,month,day,hour,minute,second)")  # 输入获取提交的起始时间
    dt2 = input("Input the commit end datetime:(year,month,day,hour,minute,second)")  # 输入获取提交的结束时间
    get_commit(save_name, rep_dir, dt1, dt2)
