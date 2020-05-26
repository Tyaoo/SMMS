# coding:utf-8
# 参考官方文档: https://doc.sm.ms/

import requests as rq 
import os, re, random, fire, logger, sys
import concurrent.futures
from logger import logger
from datetime import datetime

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/68.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) '
    'Gecko/20100101 Firefox/68.0',
    'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/68.0']

class SMMS(object):
    """
    SMMS帮助信息

    一款简单的MarkDown图片一键上传SMMS工具

    Example:
        python smms.py --ifile <inputfile>
        python smms.py --ifile <inputfile> --t <thread_num>
        python smms.py --ifile <inputfile> --ofile <outputfile>
        python smms.py --timeout <timeout>

    :param str ifile:        需要转换的MarkDown文件
    :param str ofile:        输出的文件名, 默认为 new.md
    :param int t:            设置线程池中最大线程数，默认为 5
    :param int timeout:      设置HTTP请求中的超时时间，默认为 5
    """
    def __init__(self, ifile, ofile="new.md", t=5, timeout=5):
        '''
        init params

        '''
        self.URL = "https://sm.ms/api/v2"
        self.ORIGINAL_LINK = []
        self.LINK_MAP = {}
        self.DEBUG = True
        self.INPUT_FILE = ifile
        self.OUTPUT_FILE = ofile
        self.THREAD_NUM = t
        self.TIMEOUT = timeout

        self.run()

    def upload_image(self, img_path, reformat="json"):
        '''
        上传图床

        :param str image_path: the location of the image
        :param str reformat: return type
        :return link: the link of the image
        :retype: str
        '''
        upload_url = self.URL + "/upload"
        data = {"format":reformat}
        files = {"smfile":open(img_path, 'rb')}
        headers = {'User-Agent':random.choice(user_agents)}

        try:
            res = rq.post(upload_url, data=data, files=files, timeout=self.TIMEOUT, headers=headers)
        except Exception as e:
            logger.log('ERROR', e)
            return None

        # 上传成功
        if res.json()["code"] == "success":
            resdata = res.json()["data"]
            filename = resdata["filename"]
            storename = resdata["storename"]
            imgurl = resdata["url"]
            page = resdata["page"]

            logger.log('INFOR', f"上传图片成功: {imgurl}")
            self.LINK_MAP[img_path] = imgurl

        # 重复上传
        elif res.json()["code"] == "image_repeated":
            filename = os.path.basename(img_path)
            imgurl = res.json()["images"]

            logger.log('INFOR', f"上传图片成功: {imgurl}")
            self.LINK_MAP[img_path] = imgurl
            return imgurl

        # 上传失败
        else:
            logger.log('INFOR', f"上传图片失败: {img_path}")
            return None


    def multi_upload(self):
        '''
        开启线程池上传图床

        '''
        logger.log('INFOR', f"开启多线程上传图片")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.THREAD_NUM) as executor:
            futures = [executor.submit(self.upload_image, img) for img in self.ORIGINAL_LINK]
        logger.log('INFOR', f"多线程上传图片结束")
        logger.log('ALERT', f"成功上传{len(self.LINK_MAP)}张图片")
        logger.log('ALERT', f"上传失败{len(self.ORIGINAL_LINK)-len(self.LINK_MAP)}张图片")


    def find_link(self):
        '''
        找到文件中的全部本地图片
        
        '''
        data = open(self.INPUT_FILE, 'r', encoding="utf-8").read()
        all_links = re.findall(r"!\[image-\d{17}\]\((.+?)\)", data)
        for link in all_links:
            # append local image link
            if "Users" in link:
                self.ORIGINAL_LINK.append(link)
        logger.log('INFOR', f"共找到{len(self.ORIGINAL_LINK)}张本地图片")
        if self.DEBUG:
            for link in self.ORIGINAL_LINK:
                logger.log('DEBUG', f"找到本地图片: {link}")

    def replace_link(self):
        '''
        替换本地图片为图床图片

        '''
        data = open(self.INPUT_FILE, 'r', encoding="utf-8").read()
        f = open(self.OUTPUT_FILE, 'w', encoding="utf-8")
        for old_link, new_link in self.LINK_MAP.items():
            if self.DEBUG:
                logger.log('DEBUG', f"{old_link} ==> {new_link}")
            data = data.replace(old_link, new_link)
        f.write(data)
        f.close()
        logger.log('INFOR', f"另存为文件{self.OUTPUT_FILE}")

    def run(self):
        '''
        程序入口

        '''
        logger.log('INFOR', f'开始运行SMMS')
        self.find_link()
        self.multi_upload()
        self.replace_link()
        logger.log('INFOR', f'结束运行SMMS')
        sys.exit()



if __name__ == "__main__":
    fire.Fire(SMMS)