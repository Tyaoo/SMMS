# coding:utf-8
# 参考官方文档: https://doc.sm.ms/

import requests as rq 
import os, re, random, fire, sys, time
import concurrent.futures
from log.logger import logger
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import urllib3
import ipaddress

# 不显示HTTPS警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SMMS(object):
    """
    SMMS帮助信息

    一款简单的MarkDown图片一键上传SMMS工具

    Example:
        python smms.py --ifile <inputfile>
        python smms.py --ifile <inputfile> --ofile <outputfile>
        python smms.py --timeout <timeout>

    :param str ifile:        需要转换的MarkDown文件
    :param str ofile:        输出的文件名, 默认为 new_{your inputfile}.md
    :param int timeout:      设置HTTP请求中的超时时间，默认为 5
    """
    def __init__(self, ifile, ofile='', timeout=5):
        '''
        init params

        '''
        # 图床API
        self.URL = "https://sm.ms/api/v2"
        # 本地图片列表
        self.ORIGINAL_LINK = []
        # 图片映射表
        self.LINK_MAP = {}
        # 调试
        self.DEBUG = True
        # 输入文件
        self.INPUT_FILE = ifile
        # 输出文件
        self.OUTPUT_FILE = 'new_' + os.path.basename(ifile)
        # 请求超时时间
        self.TIMEOUT = timeout
        # Cookie字段
        self.COOKIES = None
        # User-Agent字段
        self.AGENT = None
        # 代理IP
        self.PROXY = None
        # 当前分组
        self.GROUP = 1
        # 最大递归次数
        self.RECUR = 3

        self.run()

    def gen_random_ip(self):
        """
        生成随机的点分十进制的IP字符串，绕过 HOST 云 WAF

        """
        while True:
            ip = ipaddress.IPv4Address(random.randint(0, 2 ** 32 - 1))
            if ip.is_global:
                return ip.exploded

    def get_headers(self):
        '''
        绕过 5 秒的 Cloudflare，获取其 User-Agent 和 Cookie
        cfscrape 识别不了该 Cloudflare 
        所以选择使用 webdriver 模拟浏览器访问拿到 cookie

        '''
        logger.log('INFOR', f"开启模拟浏览器访问")
        try:
            # 进入浏览器设置
            opt = webdriver.ChromeOptions()
            # 设置中文
            opt.add_argument('lang=zh_CN.UTF-8')
            # 采用 headless 模式打开 Chrome
            opt.add_argument('headless')
            opt.add_argument('--disable-gpu')
            # 不加载图片
            prefs = {
              'profile.default_content_setting_values': {
                'images': 2
              }
            }
            opt.add_experimental_option('prefs', prefs)
            #设置代理
            if self.PROXY:
                opt.add_argument('proxy-server=' + self.PROXY)
            driver = webdriver.Chrome(executable_path='config/chromedriver',options=opt)
            driver.get(self.URL)
            # 等待5秒
            time.sleep(5)

            # 获取 User-Agent
            agent = driver.execute_script("return navigator.userAgent")
            self.AGENT = agent
            logger.log('INFOR', f"获取user-agent: {self.AGENT}")

            # 获取 Cookie
            cf_clearance_value = driver.get_cookie('cf_clearance')['value']
            cookies = {'cf_clearance':cf_clearance_value}
            self.COOKIES = cookies
            logger.log('INFOR', f"获取cookie: {self.COOKIES}")

            # 关闭引擎
            driver.close()
        except Exception as e:
            logger.log('ERROR', e)
        if self.AGENT == None or self.COOKIES == None:
            logger.log('ERROR', f"获取User-Agent或者Cookie失败")
            sys.exit()
        logger.log('INFOR', f"获取HTTP头部结束")

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

        ip = self.gen_random_ip()
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.AGENT,
            'X-Forwarded-For': ip,
            'X-Real-IP': ip
        }

        try:
            res = rq.post(upload_url, 
                data=data, 
                files=files, 
                verify=False,
                timeout=self.TIMEOUT, 
                cookies=self.COOKIES, 
                headers=headers)
            if self.DEBUG:
                logger.log('DEBUG', f"获取{img_path}的上传信息{res.text}")
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
                logger.log('ALERT', f"上传图片失败: {img_path}")
                return None
        except Exception as e:
            logger.log('ERROR', e)
            return None


    def multi_upload(self):
        '''
        上传图床，限制每分钟传10张，一天限制30张

        '''
        logger.log('INFOR', f"开启多线程上传图片")
        round_time = 0
        index = 0
        while True:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                while True:
                    executor.submit(self.upload_image, self.ORIGINAL_LINK[index])
                    index += 1
                    # 每上传10张就暂停
                    if index % 10 == 0:
                        round_time += 1
                        break
                     # 已经上传完就直接退出
                    if index == len(self.ORIGINAL_LINK):
                        break
            # 已经上传完就直接退出
            if index == len(self.ORIGINAL_LINK):
                break
            else:
                # 每上传10张等待60秒
                logger.log('INFOR', f"需要等待一分钟")
                time.sleep(60)
                continue

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
            if len(self.ORIGINAL_LINK) > 1:
                break
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
        self.get_headers()
        self.multi_upload()
        self.replace_link()
        logger.log('INFOR', f'结束运行SMMS')
        sys.exit()

if __name__ == "__main__":
    fire.Fire(SMMS)