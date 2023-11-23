## 1. Clone Analysis Toolkit (New Version)

**The functions implemented in this toolkit are the same as `/analysisUtil`, but the usage is simpler.**

#### 1.1 module_sort.py-------Used for cloning by module classification, counting the number of cross-module clones and the number of lines of code
#### 1.2 clone_comodify.py----Used for detecting co-modified clones  
#### 1.3 bug_induce_clone.py--Used to detect bug-prone clones, count the number of bug-fix commits related to clones, and calculate the average fix time

## 2. Repo Clone
Clone the project you want to analyze to your computer.

## 3. Code Clone detection
Use `Simian-2.5.10` to detect all the code clones of source files.
See [Docs | Simian Similarity Analyzer (quandarypeak.com)](https://simian.quandarypeak.com/docs/) to set par grams you need.

(**note**: Because simian only supports C++ files with the suffix `.cpp`. In order to detect `.cc` files in Apollo, you'll have to change  all `.cc` suffixes to `.cpp` suffixes, if your OS is `windows`, you can put `/source/rename.bat` in the main directory of the source code, eg. `apollo-1.0.0/apollo-1.0.0/`, and run this batch command.
And if your OS is `Linux`, you can use the command `find . -name "*.cc" -exec bash -c 'mv "$1" "${1%.cc}".cpp' - '{}' \;` Or you can write your own command to complete this work).

Put the clone detection results in `/clone_xml` (we already put all the results we use in the `/clone_xml`), and make sure the file name of clone results refers to the example in `/clone_xml`.

In addition, if your operating system is Linux, you can use the script "detect.sh" to complete automated code clone detection, provided that "Your_Simian_path" is changed to your Simian installation directory. At the same time, you can change the configuration as needed.

## 3. Usage
#### 3.1 Module distribution analysis
Run the following command: ```$ python module_sort.py```

#### 3.2 Bug-prone clones detection
Run the following command: ```$ python bug_induce_clone.py```

#### 3.3 Co-modified clones detection
Run the following command: ```$ python clone_comodify.py```


