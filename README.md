# SMMS

smms is a simple tool for uploading pictures located in your .md file to the https://sm.ms/.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install required packages from requirements.txt.

```bash
pip install -r requirements.txt
```

## Usage

```shell
python smms.py --ifile <inputfile>
python smms.py --ifile <inputfile> --ofile <outputfile>
python smms.py --timeout <timeout>

:param str ifile:        需要转换的MarkDown文件
:param str ofile:        输出的文件名, 默认为 new_{your inputfile}.md
:param int timeout:      设置HTTP请求中的超时时间，默认为 5
```

## Attention

On account of the limit of the smms, you only upload 10 pictures per minute and 30 pictures per day at most.

## License

[MIT](https://choosealicense.com/licenses/mit/)

Copyright (c) 2017 - 2019 Molunerfinn