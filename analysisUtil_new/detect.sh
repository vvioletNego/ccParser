for tag in `git tag --sort=committerdate`
  do
  git checkout $tag  # 转到指定分支
  find . -name "*.cc" -exec bash -c 'mv "$1" "${1%.cc}".cpp' - '{}' \; # 如果要检测.cc后缀的文件需要将其换成.cpp才能被正确识别为C++文件
  ls  # 列出当前目录下所有文件名，可以检查是否已经切换分支
  curPath=$(readlink -f "$(dirname "$0")")  # 得到当前文件路径
  # echo $curPath  # 打印文件路径
  project_path=$(cd `dirname $0`; pwd) # 得到当前文件路径
  project_name="${project_path##*/}"  # 得到当前文件夹名称
  # echo $project_name
  java -jar /Your_Simian_path/bin/simian-2.5.10.jar -threshold=6 -reportDuplicateText+ -ignoreCurlyBraces+ -ignoreIdentifiers+ -ignoreStrings+ -ignoreNumbers+ -ignoreCharacters+ -ignoreVariableNames+ -balanceParentheses+ -balanceSquareBrackets+ "$curPath/**/*.cpp" "$curPath/**/*.h" -formatter=xml:/Your_Simian_path/results/$project_name-$tag.xml "*.rb" -language="cpp"
  # 检测克隆
  done

git reset --hard
git clean df # 将仓库还原
