# httool

This tool allow to use parameters and templates inside html documents. This is `python3` tool with zero dependencies.

### Features
- support html templates
- compress and minify js and css files
- add timestamp to image files

### Development a tool
For development purposes add current directory to path variable:
```
export PATH=`pwd`:$PATH
```

### Installation
To install `httool` use following commands:
```
sudo cp httool /usr/bin/httool
sudo chmod 777 /usr/bin/httool
```

### Usage
`httool` use config file to read settings from it. Config file have to be placed to project root. `httool` find all `.html` files by extention inside project root and it subfolders, parse these files and substitute parameters and templates.


### Config file syntax
Config file is a file in json format. It contains following settings:



### Tags syntax