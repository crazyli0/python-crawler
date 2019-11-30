# import something here
from spider import *
import re

cls()
print('正在完成设定初始化...')
c = input('输入要抓取的城市的拼音小写首字母(如广州：gz)：')
inp = c.lower()
inp = re.split(r'(?:,|;|\s|\t)\s*', inp)
s = spider()
path = input('保存文件的路径(如：C:/Users/a8135/Desktop/)：')
s.setPath(path)
# t = input('输入要抓取的房产类别拼音（如二手房：ershoufang)：')
t = 'ershoufang'
s.setDomain(tail=t)
cls()
for item in inp:
    s.setCity(item)
    s.run()
    print('-'*30 + '\n已完成城市： ', item, '\n' + '-'*30)
print('已抓取：', end=' ')
for item in inp:
    print(item, end='')
input('运行完成！按任意键退出...')
