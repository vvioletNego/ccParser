# ccParser
## This tool can support the following functionalities: 
1.Grouping the code clones by the module where they are located, extracting within-module code clones and cross-module code clones.   
2.Selecting an initial version, comparing clones in the initial version with clones in four versions following the initiail version, extracting the co-modified code clones.  
3.Selecting an initial version, extracting bug-fix commits start with the initial version and within five versions, checking if the bug-fix commit is in between the start line and the end line of the code clones.
### Main analysis functions are in \analsisUtil directory, before doing all the analysis work, you need to download all required versions of the project source files in \source directory, and use Simian for code clone detection, put the clone results in the \clone_xml directory. Besides, using extract-commit.py in the \utl directory to extract information of commits, and save it in \time_commit directory.
