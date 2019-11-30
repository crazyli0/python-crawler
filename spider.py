# coding=utf-8
# import something here
import sys
import random
import requests
import math
import time
import os
import msvcrt
from tqdm import tqdm
from lxml import etree

'''
面向对象实现的爬虫的主程序文件
将网页中所有的房产逐一爬取
并实现将爬取的网页中特定元素按顺序保存到csv文件中
再把文件压缩一下
features:
# 1 等待延迟 done
# 2 进度条 done
# 3 进度保存 working...
# 4 压缩处理完的数据包
# 5 生成运行日志
todo:
# 1 分离写入csv文件的函数 done
# 2 优化冗余
# 3 debug
'''
version = 'v1.4-beta'


def cls():
    os.system('cls')
    return


class spider:
    def __init__(self, city: str = 'Unknown', domain: str = 'lianjia.com'):
        self.file_path: str = ''  # csv文件保存的位置
        self.cur_city: str = city  # 城市名称
        self.file_name: str = city + '.csv'  # 文件名，直接使用城市名，一个城市一个csv文件
        self.file_type: str = '.html'  # 文件类型
        self.first_id: int = 0  # 每个城市第一个房产的id，避免爬取重复页面
        self.notFirst: bool = True  # 是否是第一抓？
        self.repeat: bool = False  # 是否已经重复
        self.noWelcome: bool = False
        # 网页地址处理相关设定
        self.latency = True  # 是否启用延迟
        self.timeout: int = 15  # 连接超时15秒
        self.retry: int = 3  # 错误重连3次
        self.aWait: int = 10  # 等待时间, 秒
        self.domain: str = domain  # 'lianjia.com'
        self.https: bool = True  # True：使用https, False:使用http
        self.prefix: str = city  # 网站前缀,eg:bj
        self.midfix: str = ''  # 网站中间名,eg:fang
        self.tail: str = ''  # 网页后缀,eg:loupan
        self.totalPages: int = 1  # 总页数
        self.numPrePage: int = 30  # 每页的房产总数
        # html文件处理相关
        self.houseTotal: int = 1  # 房产总数
        self.houseNum: int = 1  # 已处理的房产总数
        self.keyword: list = list()  # 字典中拥有的键
        self.kwLen: int = 1  # 键数量
        self.dictFlag: bool = True  # 是否需要初始化字典
        self.baseKey = ['id', 'title', 'totalPrice', 'unitPrice']
        self.item = ['file_path', 'cur_city', 'first_id', 'if_repeat',
                     'https', 'prefix', 'midfix', 'tail', 'total',
                     'numPrePage', 'houseTotal', 'houseNum', 'backLen']

    def backup(self):
        bk = list()
        tmp = [self.file_path, self.cur_city,
               self.first_id, self.repeat, self.https, self.prefix,
               self.midfix, self.tail, self.totalPages, self.numPrePage,
               self.houseTotal, self.houseNum]
        bk_len = len(bk) * 2  # 还要加上键的长度
        bk.append(bk_len)
        fullPath = self.file_path + self.file_name + '.bk'
        bkDict = dict(zip(self.item, tmp))
        try:
            file = open(fullPath, mode='w', encoding='utf-8')
            for i in self.item:
                file.write(i + ' ' + str(bkDict.get(i)) + '\t')  # 将字典中的内容逐项写入到备份文件
            file.close()
        except Exception as e:
            print(e, '\n in', fullPath)
        else:
            return True

    def recovery(self, file):
        try:
            rec = open(file, mode='r', encoding='utf-8')
            d = dict()
            tmp = rec.readline().split()
            tmp_len = int(tmp[-1])  # -1取最后一项
            if len(tmp) != tmp_len:
                raise Exception('Recovery Failed: length is not match !')
            for i in range(0, tmp_len, 2):
                d[tmp[i]] = tmp[i + 1]
            self.file_path = d.get('file_path')
            self.cur_city = d.get('cur_city')
            self.first_id = int(d.get('first_id'))
            self.repeat = bool(d.get('if_repeat'))
            self.https = bool(d.get('https'))
            self.prefix = d.get('prefix')
            self.midfix = d.get('midfix')
            self.tail = d.get('tail')
            self.totalPages = int(d.get('total'))
            self.numPrePage = int(d.get('numPrePage'))
            self.houseTotal = int(d.get('houseTotal'))
            self.houseNum = int(d.get('houseNum'))
            print('Recovery Complete!')
        except Exception as e:
            print(e, '\n in', file)

    def setDomain(self, https: bool = True, prefix: str = '', midfix: str = '',
                  domain: str = '', tail: str = ''):
        """
        用于设定网站相关信息，会在节点中补全符号，示例网址：https://bj.fang.lianjia.com/ershoufang/101106177942.html
        :param https: 是否使用https，Boolean类型
        :param prefix: 网站前缀,'bj'
        :param midfix: 网站中间名,'fang'
        :param domain: 网站域名,'lianjia.com'
        :param tail: 网页目录,'ershoufang'
        """
        self.https = https
        self.midfix = midfix
        self.tail = tail
        if prefix is '':
            self.prefix = self.cur_city
        else:
            self.prefix = prefix
        if domain is not '':
            self.domain = domain

    def setPath(self, file_path):
        assert type(file_path) is str, TypeError
        self.file_path = file_path
        return

    def setCity(self, name: str):
        self.cur_city = name
        self.prefix = name
        self.file_name = name + '.csv'
        self.repeat = False
        self.notFirst = True
        self.dictFlag = True

    def getWaitSecond(self):
        if self.latency:
            return random.randint(2, self.aWait)
        else:
            return 1

    def segmentCheck(self):
        """
        对当前参数进行类型和值检查，无返回值，有错误则直接中断程序运行
        """
        try:
            assert type(self.file_path) is str and self.file_path != '', ValueError
            assert type(self.cur_city) is str and self.cur_city != '', ValueError
            assert type(self.file_name) is str and self.file_name != '', ValueError
            assert type(self.first_id) is int, TypeError
            assert type(self.domain) is str, TypeError
            assert type(self.prefix) is str, TypeError
            assert type(self.totalPages) is int and self.totalPages >= 1, ValueError
            assert type(self.keyword) is list, TypeError
            assert type(self.kwLen) is int and self.kwLen >= 1, ValueError
            assert type(self.baseKey) is list and len(self.baseKey) >= 1, ValueError
        except AssertionError as err:
            print('Segment Check Failed:{0}'.format(err))
        except:
            print('Unknown Exceptions:', sys.exc_info())
            raise RuntimeError

    def takeanap(self):
        t = self.getWaitSecond()
        # print('Wait for', t, 'seconds to take a nap...')
        time.sleep(t)
        return

    def getHtml(self, url: str):
        """
        前往url，并返回一个得到的html字符串
        """
        headers = {  # 构造请求头
            'User-Agent': self.getUA(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
        }

        req = requests.get(url, headers=headers, timeout=self.timeout)
        sta_code = req.status_code
        if str(sta_code) != '200':
            for i in range(self.retry):
                sec = self.getWaitSecond()
                print('eh...seems there is something wrong with status code:', sta_code,
                      'and url', url, '\nwill retry after', sec, 'seconds...\n')
                req = requests.get(url, headers=headers, timeout=self.timeout)
                sta_code = req.status_code
                if str(sta_code) == '200':
                    break
        elif str(sta_code) == '200':
            return req.content.decode('utf-8')
        else:
            raise Exception("Unknown Error in getHtml function !")
        sys.exit(1)

    def getData(self, h_url: str):
        """
        用于爬取每一个房产页面中的有效信息，
        :param h_url: 要爬取的房产网址
        :return: 返回一个该房产所有信息的字典
        """
        # 访问并加载房产详情页面
        inf = dict()
        html = self.getHtml(h_url)
        page = etree.HTML(html)

        # 开始收集信息
        tmp = page.xpath('//div[@class="btnContainer  LOGVIEWDATA LOGVIEW"]')
        inf['id'] = tmp[0].get('data-lj_action_resblock_id')  # 房产ID
        tmp = page.xpath('//h1[@class="main"]')
        inf['title'] = ((tmp[0].text.strip()).replace('\n', '')).replace(',', '，')  # 房产标题
        tmp = page.xpath('//span[@class="total"]')
        inf['totalPrice'] = tmp[0].text  # 房产总价
        tmp = page.xpath('//span[@class="unitPriceValue"]')
        inf['unitPrice'] = tmp[0].text  # 房产每平方米单价
        # 12项基本信息
        tmp = page.xpath('//div[@class="base"]/div[@class="content"]/ul/li/span')
        for i in range(len(tmp)):  # 感谢链家极好的信息分类
            inf[tmp[i].text] = tmp[i].tail.replace('㎡', '')
        # 8项交易信息
        tmp = page.xpath('//div[@class="transaction"]/div[@class="content"]/ul/li/span')
        for i in range(0, len(tmp), 2):  # 再次感激链家，以后租房一定找你嗷
            inf[tmp[i].text] = (tmp[i + 1].text.strip()).replace('\n', '').replace(',', '，')
        # 7项房屋特色
        tmp = page.xpath('//div[@class="newwrap baseinform"]/div[@class="introContent showbasemore"]/div/div')
        for i in range(2, len(tmp), 2):
            inf[tmp[i].text] = (tmp[i + 1].text.strip()).replace('\n', '').replace(',', '，')
        # 差点把地铁忘了
        tmp = page.xpath('//div[@class="newwrap baxseinform"]/div[@class="introContent showbasemore"]/div/div/a')
        if len(tmp) > 1 and ('is_near_subway' in tmp[0].get('class', '')):
            inf['subway'] = 'True'
        else:
            inf['subway'] = 'False'
        # 完事了，返回字典
        return inf

    def getPage(self, p_url: str, half_url: str):
        """
        爬取一整页的所有房产的详情并返回一个包含房产信息字典的列表
        :param half_url: 房产地址的前部
        :param p_url: 要爬取的网页地址
        :return: 返回一个列表，元素为字典类型
        """
        h_url = half_url
        ans = list()
        self.takeanap()
        html = self.getHtml(p_url)
        page = etree.HTML(html)
        p_tmp = page.xpath('//ul[@class="sellListContent"]/li')
        print('\n')
        for i in range(len(p_tmp)):  # 逐项抓取房产对应的详情网页
            print('.', end='')
            curID = p_tmp[i].get('data-lj_action_housedel_id')
            ho_url = h_url + curID + self.file_type
            if not self.notFirst and self.first_id == int(curID):
                self.repeat = True  # 第一次抓的时候怎么办？？
            elif self.notFirst:
                self.notFirst = False  # 这样就可以了
            ans.append(self.getData(ho_url))
            self.takeanap()  # 延迟处理
        return ans

    def switchLatency(self, enable=True):
        assert type(enable) is bool, TypeError
        self.latency = enable

    def generateDict(self, half_url: str):
        p_url = half_url + str(self.first_id) + self.file_type
        self.keyword = self.baseKey
        html = self.getHtml(p_url)
        page = etree.HTML(html)
        tmp = page.xpath('//div[@class="base"]/div[@class="content"]/ul/li/span')  # 读取房屋基本信息标签
        for i in range(len(tmp)):
            self.keyword.append(tmp[i].text)
        tmp = page.xpath('//div[@class="transaction"]/div[@class="content"]/ul/li/span')  # 读取房屋交易属性
        for i in range(0, len(tmp), 2):
            self.keyword.append(tmp[i].text)
        tmp = page.xpath('//div[@class="newwrap baseinform"]/div[@class="introContent showbasemore"]/div/div')  #
        for i in range(2, len(tmp), 2):
            self.keyword.append(tmp[i].text)
        self.keyword.append('subway')  # 赶忙把地铁加上
        self.kwLen = len(self.keyword)
        self.dictFlag = False
        print('Done !')

    def csvWrite(self, input_list: list, csv_file: str):
        """
        将传入的列表中全部元素逐一写入csv文件中，每一项独占一行
        :param csv_file: 写入的csv文件指针
        :param input_list: 需要写入的列表
        :return : 当函数顺利运行完成时返回True
        """
        assert type(input_list) == list, TypeError
        len_list = len(input_list)
        if len_list < 1:  # 判断列表长度
            raise Exception('Error in csvWrite : length of input must larger than 0 !')
        try:
            file = open(csv_file, mode='a', encoding='utf-8')
            print('\n正在写入信息...')
            if type(input_list[0]) == dict:  # 如果是字典就按list中元素的顺序自动写入
                for item in range(len_list):
                    tmp = self.getItem(input_list[item], self.keyword)
                    for subject in tmp:
                        file.write(str(subject) + ',')
                    file.write('\n')
            else:
                for item in input_list:  # 将传入的列表写入
                    file.write(str(item) + ',')
                file.write('\n')
            print('写入完成！')
            file.close()
        except OSError as err:
            print('OSError in csvWrite: {0}'.format(err))
            raise
        except TypeError as err:
            print('TypeError in csvWrite: {0}'.format(err))
            raise
        except:
            print('Unexpected error:', sys.exc_info()[0])
            raise RuntimeError
        return True

    def setupSegment(self):
        print('可修改的参数：')
        print('# 1 等待延迟，当前值为：' + str(self.aWait) + '秒')
        print('tips：等待延迟作用在每一次访问网站的时候，用于防止被网站服务器封禁IP。'
              '延迟值越小，抓取速度越快，被封禁IP风险越高。')
        print('# 2 城市名称拼音首字母，当前值为：' + self.cur_city)
        print('tips：城市名称为网站开头的通用部分，如北京地区的网址为：https://bj.lianjia.com/。')
        while True:
            inp = input('输入要修改项的数字代号（输入q退出）： # ')
            if inp == '1':
                latency = int(input('修改延迟的值为（默认值：10）：'))
                self.aWait = latency
                print('修改完成，当前值为：' + str(self.aWait))
                continue
            elif inp == '2':
                self.setCity(input('修改城市名称简写为：'))
                print('修改完成，当前值为：' + self.cur_city)
                continue
            elif inp == 'q' or inp == 'Q':
                break
            print('没有找到对应项，请重试！')
        return

    def writeTitle(self, filePath: str):
        try:
            csvFile = open(filePath, mode='w', encoding='utf-8')
            for i in range(self.kwLen):
                csvFile.write(self.keyword[i] + ',')
            csvFile.write('\n')
            csvFile.close()
        except OSError as err:
            print('文件写入错误，请检查路径！{0}'.format(err))
        except:
            print('Unexpected Error: ', sys.exc_info())
            raise RuntimeError

    def welcome(self):
        cls()
        for i in range(30):
            print('-', end='')
        print('\nCrawler', version, '-zcy')
        print('当前要抓取的城市是：', self.cur_city)
        print('CSV文件保存路径为：', self.file_path + '/' + self.file_name)
        print('要访问的站点：', self.genUrl())
        print('目标网站目录：', self.domain + '/' + self.tail)
        print('访问延迟功能状态：', str(self.latency))
        if self.latency:
            print('延迟最大时间（秒）：', str(self.aWait))
        print('-' * 30)
        if self.noWelcome:
            return
        self.noWelcome = True
        inp = input('按回车键以当前设定开始运行\n输入q退出程序\n输入E编辑参数\n$ ')
        if inp == 'q' or inp == 'Q':
            # raise KeyboardInterrupt
            sys.exit('KeyboardInterrupt：用户终止了程序！')
        elif inp == 'E' or inp == 'e':
            self.setupSegment()
            self.segmentCheck()
            self.welcome()
        return

    def initRun(self, init_url):
        """
        运行前的初始化，根据网址第一页自动填充相关信息
        :param init_url: 如：https://bj.lianjia.com/
        :return: 0
        """
        url = init_url + 'pg1' + '/?_t=1'  # 第一页链接，如：https//bj.lianjia.com/pg1/?_t=1
        print('Current city:', self.cur_city, '\nUrl is', url, '\nConnecting...')
        html = self.getHtml(url)  # 得到当前城市第一页
        firstPage = etree.HTML(html)
        ttmp = firstPage.xpath('//h2[@class="total fl"]/span')  # 查找当前城市总房产数量字符串
        ttmp = ttmp[0].text.strip()
        firstHouse = firstPage.xpath('//li[@class="clear LOGVIEWDATA LOGCLICKDATA"]')
        self.numPrePage = len(firstHouse)
        self.houseTotal = int(ttmp)  # 设定总房产数目
        self.totalPages = math.ceil(self.houseTotal / self.numPrePage)  # 总的数量除以每一页显示的数量得到页数
        self.first_id = int(firstHouse[0].get('data-lj_action_housedel_id'))
        print('Total page count:', self.totalPages, 'and total houses count:', self.houseTotal)
        print('The first house ID is', self.first_id)
        print('Detecting keyword dictionary...')
        if self.dictFlag:
            print('Keyword dictionary not found! Generating...')
            self.generateDict(init_url)
        return 0

    def genUrl(self):
        """
        根据当前类的数据成员自动生成网址
        :return: 生成的网址
        """
        if self.https:
            pg_url = 'https://'
        else:
            pg_url = 'http://'
        if self.prefix is not '':
            pg_url += self.prefix + '.'
        if self.midfix is not '':
            pg_url += self.midfix + '.'
        pg_url += self.domain + '/'
        if self.tail is not '':
            pg_url += self.tail + '/'
        url = pg_url
        return url

    def run(self, welcome=True):
        """
        按照当前设定的参数开始运行爬虫程序
        """
        if welcome:
            self.welcome()

        assert self.file_path is not '' and self.file_name is not '', ValueError
        if self.file_path[-1] != '/':
            self.file_path += '/'
        fullPath = self.file_path + self.file_name
        try:
            csvFile = open(fullPath, mode='w', encoding='utf-8')
            csvFile.write('TEST OK!')
            csvFile.close()
        except OSError as err:
            print('文件写入错误：{0}'.format(err))
        except:
            print('文件IO出错！Unexpected Error:', sys.exc_info())
            raise RuntimeError

        # 构建网站链接，网站链接详情：pg_url:到房产网页的地址，house_url：到具体房产的地址
        house_url = self.genUrl()
        # 网址构建完成

        # 传入网址初始化第一页
        self.initRun(house_url)

        # 先写入标题
        self.writeTitle(fullPath)

        # 检查当前设定的值是否正常
        self.segmentCheck()

        # debugging
        # 开始获取当前城市的全部房产信息
        houseInfo = list()  # house中存放一整页的房产的全部信息，每一个房产为一个字典
        proc = tqdm(total=self.totalPages, desc='正在完成', ncols=0, unit='页')
        for i in range(self.totalPages):  # range(self.total)
            proc.update(1)
            p_url = house_url + 'pg' + str(i + 1) + '/?_t=1'  # 构建每一页的网址
            # print('\n正在抓取第', i + 1, '页的全部房产信息')  # 整个进度条
            houseInfo.extend(self.getPage(p_url, house_url))  # 获取该页的全部房产信息
            if self.repeat:  # 判断是否已经重复了，链家的网页小毛病
                print('发现信息重复！中断当前城市抓取...')
                break
            self.houseNum = (i + 1) * self.numPrePage  # 处理计数
            # 将爬取的信息写入到csv文件当中再处理详细的房产信息
            self.csvWrite(houseInfo, fullPath)
            houseInfo.clear()
            # print('按任意键中断')
            t = time.time()
            times = 0.1
            aWait = 0
            while time.time()-t < 5:
                if msvcrt.kbhit():
                    print('功能待完善，敬请期待')
                    pass  # 保存？继续？
                if str(aWait) in '0123456':
                    print('.', end='')
                aWait += times
                time.sleep(times)
        del proc

        # 至此该城市的全部数据爬取完成
        csvFile = open(fullPath, mode='a', encoding='utf-8')
        print('写入完成！文件已保存在', fullPath)
        csvFile.write('\n' + self.getDate())
        csvFile.close()

    @staticmethod
    def getItem(input_dict: dict, order_list: list):
        """
        用于按order_list中的元素顺序返回一个input_dict中元素的列表
        :param input_dict: 要读取的字典
        :param order_list: 包含字典中键的列表
        """
        assert type(input_dict) == dict and type(order_list) == list, TypeError
        len_dict = len(input_dict)
        len_list = len(order_list)
        if len_dict < 1 or len_list < 1:
            raise Exception('Error in getItem: length of dict and list must larger than 0 !')
        res = list()
        for item in order_list:
            res.append(input_dict.get(item))
        return res

    @staticmethod
    def getUA():
        """
        在UA库中随机选择一个UA
        :return: 返回一个库中的随机UA
        """
        UA_list = [
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 OPR/26.0.1656.60",
            "Opera/8.0 (Windows NT 5.1; U; en)",
            "Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50",
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 9.50",
            # Firefox
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
            "Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10",
            # Safari
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
            # chrome
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
            # 360
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
            # 淘宝浏览器
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11",
            # 猎豹浏览器
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)",
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E; LBBROWSER)",
            # QQ浏览器
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
            # sogou浏览器
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0",
            "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0)",
            # maxthon浏览器
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.4.3.4000 Chrome/30.0.1599.101 Safari/537.36",
            # UC浏览器
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 UBrowser/4.0.3214.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
            "Mozilla/5.0 (Windows; U; Windows NT 5.2) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.2.149.27 Safari/525.13",
            "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
            "Mozilla/5.0 (Macintosh; U; IntelMac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1Safari/534.50",
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
            "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
            "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"]
        return random.choice(UA_list)

    @staticmethod
    def getDate():
        tmp = time.asctime()
        return tmp
