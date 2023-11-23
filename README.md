## 1. Code clone  analysis tool	
[![Backers on Open Collective](https://img.shields.io/badge/python-3.10-orange.svg?style=flat-square)](#backers)

This is a code clone analysis tool and it can support the following functionalities:	

1. Grouping the code clones by the module where they are located, extracting within-module code clones and cross-module code clones.	
2. Selecting an initial version, comparing clones in the initial version with clones in four versions following the initial version, extracting the co-modified code clones.
3. Selecting an initial version, extracting bug-fix commits start with the initial version and within **five** versions, checking if the bug-fixing commit is in between the start line and the end line of the code clones.

## 2. Installation

#### 2.1 Git Clone

Clone the project from git. And `cd` to the project root:

```
$ git clone https://github.com/vvioletNego/ccParser.git
$ cd ccParser
```

#### 2.2 Install requirements

Install the requirements from the `ccParser` project root as the following commands:

```
$ pip install -r requirements.txt
```

#### 2.3 Download source files

Download the source code of all required versions to the `/source` directory, first enter the `/source` directory, and download all the source files in `urls.txt` (we put all download links of source files we use in `urls.txt`).  If your OS is `linux`, you can use the batch command like:

```
$ cd ./source
$ wget -i urls.txt
```

Besides, you can change the context of `urls.txt` so that you can download the source files you want to analysis.

#### 2.4 Code clone detection

Use `Simian-2.5.10` to detect all the code clones of source files. See [Docs | Simian Similarity Analyzer (quandarypeak.com)](https://simian.quandarypeak.com/docs/) to set par grams you need (**note**: Because simian only supports C++ files with the suffix `.cpp`. In order to detect `.cc` files in Apollo, you'll have to change  all `.cc` suffixes to `.cpp` suffixes, if your OS is `windows`, you can put `/source/rename.bat` in the main directory of the source code, eg. `apollo-1.0.0/apollo-1.0.0/`, and run this batch command. And if your OS is `Linux`, you can use the command `find . -name "*.cc" -exec bash -c 'mv "$1" "${1%.cc}".cpp' - '{}' \;` Or you can write your own command to complete this work.). Put the clone detection results in `/clone_xml` (we already put all the results we use in the `/clone_xml`), and make sure the file name of clone results refers to the example in `/clone-xml`.

#### 2.5 Module distribution analysis

`cd` to `/analysisUtil` and run the following command:

```
$ python module_sort.py
```

In the `util/module_utl.py` we define the default rules for separating module names. If you want to separate according to your own rules, you can modify pattern and special_cases in `util/module_utl.py`.
The results of module distribution and cross-module clones will be put in `results/YourRepo_dup_results.xlsx`

#### 2.6 Bug-prone clones detection

To extract bug-fixing commits from repositories, `cd` to `/util` and run  the following command:

```
$ python extract_commit.py
```

Enter the corresponding parameters according to the prompt. And all bug-fixing commits information will be stored in `/time-commit`.

`cd` to `/analysisUtil` and run the following command:

```
$ python bug_induce_clone.py
```

all the summary results will be put in `results/YourRepo_bug_induce_results.xlsx`.
all the data of bug-prone clones extracted will be put in `json/bug-induce`.

#### 2.7 Co-modified clones detection

To extract all co-modified clones in the corresponding project, `cd` to `/analysisUtil` and run the following command:

```
$ python clone_comodify.py
```

All the summary results will be put in `results/YourRepo_comodify_dup_results.xlsx`.
All the data of co-modified clones extracted will be put in `json/comodify`.

## 3. New version
We have launched a new method and placed it in the directory `/analysisUtil_new`. It is currently being tested. The usage method is in the [`/analysisUtil_new/readme.md`](https://github.com/vvioletNego/ccParser/blob/master/analysisUtil_new/readme.md).

## 4. Publication
If you are interested in our work, you can find more details in our paper listed below. If you use our dateset and tool, please cite our paper.  
```
@INPROCEEDINGS{10298437,
  author={Mo, Ran and Jiang, Yingjie and Zhan, Wenjing and Wang, Dongyu and Li, Zengyang},
  booktitle={2023 38th IEEE/ACM International Conference on Automated Software Engineering (ASE)}, 
  title={A Comprehensive Study on Code Clones in Automated Driving Software}, 
  year={2023},
  pages={1073-1085},
  doi={10.1109/ASE56229.2023.00053}}
```


