# file mover
Moves files from one location to another based on the config file. Purposefully has limitations to prevent files from being overwritten. Meant to be used in tandem with a cloud sync application such as OneDrive or Google Drive. 

## limitations
It does not handle partial files. Scenario not tested: If the cloud sync application is in the middle of a download what does this program do. 

# Setup
Python 3.10.9 or greater

Run the following from the synced repo. 
```bash
python3.10 -m venv venv
source ./venv/bin/activate
pip3 install -r requirements.txt
```

# usage
```
usage: Autobackup [-h] --rootDst ROOTDST --rootSrc ROOTSRC --config CONFIG [--version]
```

## config file
Setup your config file using `config.yaml` as an example. Source and destination values are case sensitive. 

Files listed in `filesToIgnore` will skipped and deleted from the source. 

# logging
Console output is logged to a rotating log file `autobackup.log` total of 10 files at 8MB each. 
