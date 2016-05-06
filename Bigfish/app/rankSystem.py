# -*- coding: utf-8 -*-
"""
比赛回测排名
"""
import traceback
import pymysql
import os
import codecs
import operator
from Bigfish.app import backtest as bt
from Bigfish.store.connection import conn


strategyPath="G:/参赛策略"
scorePath="G:/回测成绩"
userInfoPath="G:/用户信息"
stperiod={"EURUSD":[],"GBPUSD":[],"USDCAD":[],"USDJPY":[],"USDCHF":[],"AUDUSD":[]}
enperiod={"EURUSD":[],"GBPUSD":[],"USDCAD":[],"USDJPY":[],"USDCHF":[],"AUDUSD":[]}
userInfo={}

def setTestPeriod():
    """
    设置回测时间段，每个品种各选5个。
    :return:
    """
    global stperiod,enperiod

    #欧元美元测评
    stperiod["EURUSD"].append("2014-02-09")
    enperiod["EURUSD"].append("2014-05-09")

    stperiod["EURUSD"].append("2014-06-30")
    enperiod["EURUSD"].append("2014-09-30")

    stperiod["EURUSD"].append("2014-10-05")
    enperiod["EURUSD"].append("2015-01-05")

    stperiod["EURUSD"].append("2015-02-27")
    enperiod["EURUSD"].append("2015-05-27")

    stperiod["EURUSD"].append("2015-12-06")
    enperiod["EURUSD"].append("2016-03-06")

     #英镑美元测评
    stperiod["GBPUSD"].append("2014-02-09")
    enperiod["GBPUSD"].append("2014-05-09")

    stperiod["GBPUSD"].append("2014-06-30")
    enperiod["GBPUSD"].append("2014-09-30")

    stperiod["GBPUSD"].append("2014-10-05")
    enperiod["GBPUSD"].append("2015-01-05")

    stperiod["GBPUSD"].append("2015-02-27")
    enperiod["GBPUSD"].append("2015-05-27")

    stperiod["GBPUSD"].append("2015-12-06")
    enperiod["GBPUSD"].append("2016-03-06")

     #美元加元测评
    stperiod["USDCAD"].append("2014-02-09")
    enperiod["USDCAD"].append("2014-05-09")

    stperiod["USDCAD"].append("2014-06-30")
    enperiod["USDCAD"].append("2014-09-30")

    stperiod["USDCAD"].append("2015-01-25")
    enperiod["USDCAD"].append("2015-04-25")

    stperiod["USDCAD"].append("2015-08-21")
    enperiod["USDCAD"].append("2015-11-21")

    stperiod["USDCAD"].append("2015-12-21")
    enperiod["USDCAD"].append("2016-03-21")

     #美元日元测评
    stperiod["USDJPY"].append("2014-04-15")
    enperiod["USDJPY"].append("2014-07-15")

    stperiod["USDJPY"].append("2014-07-31")
    enperiod["USDJPY"].append("2014-10-31")

    stperiod["USDJPY"].append("2014-11-27")
    enperiod["USDJPY"].append("2015-02-27")

    stperiod["USDJPY"].append("2015-05-17")
    enperiod["USDJPY"].append("2015-08-17")

    stperiod["USDJPY"].append("2016-01-25")
    enperiod["USDJPY"].append("2016-04-25")

     #美元瑞郎测评
    stperiod["USDCHF"].append("2014-01-19")
    enperiod["USDCHF"].append("2014-04-19")

    stperiod["USDCHF"].append("2014-05-06")
    enperiod["USDCHF"].append("2014-08-06")

    stperiod["USDCHF"].append("2015-01-08")
    enperiod["USDCHF"].append("2015-04-08")

    stperiod["USDCHF"].append("2015-08-21")
    enperiod["USDCHF"].append("2015-11-21")

    stperiod["USDCHF"].append("2015-12-21")
    enperiod["USDCHF"].append("2016-03-21")

     #澳元美元测评
    stperiod["AUDUSD"].append("2014-04-01")
    enperiod["AUDUSD"].append("2014-07-01")

    stperiod["AUDUSD"].append("2014-09-07")
    enperiod["AUDUSD"].append("2014-12-07")

    stperiod["AUDUSD"].append("2015-02-03")
    enperiod["AUDUSD"].append("2015-05-03")

    stperiod["AUDUSD"].append("2015-08-21")
    enperiod["AUDUSD"].append("2015-11-21")

    stperiod["AUDUSD"].append("2015-12-21")
    enperiod["AUDUSD"].append("2016-03-21")

def codeDownload():
    """
    下载所有参赛策略
    """
    global strategyPath
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select * from strategy_competition")
    row=cur.fetchall()
    for line in row:
        filename=str(line["name"])+"&"+str(line["id"])+"&"+str(line["user_id"])+".py"
        content=line["content"]
        outFilePath=strategyPath+"/"+filename
        output=open(outFilePath, "w")
        output.write(content)
        output.close()
    print("下载完毕，策略总数：",len(row))

def userInfoDownload():
    """
    下载用户信息
    :return:
    """
    global userInfoPath
    conn=pymysql.connect(host='121.42.180.122', user='xinger', passwd='ShZh_forex_4', db='jfinalbbs',charset='utf8')
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select * from user")
    row=cur.fetchall()
    for line in row:
        outFilePath=userInfoPath+"/"+"用户信息.csv"
        output= open(outFilePath,"a")
        output.write("%s,%s,%s,%s,%s\n"% (line["id"],line["nickname"],line["email"],line["fdt_id"],line["phone"]))
        output.close()

def getUserInfo():
    """
    获取用户信息并输出到文件
    :return:
    """
    global userInfo,userInfoPath
    inFilePath=userInfoPath+"/"+"用户信息.csv"
    input=open(inFilePath,"r")
    row = input.readlines()#读取文件
    for line in row:
        id,nickname,email,fdt_id,phone=line.split(",")
        userInfo[id]={}
        userInfo[id]["nickname"]=nickname
        userInfo[id]["email"]=email
        userInfo[id]["fdt_id"]=fdt_id
        userInfo[id]["phone"]=phone
    input.close()

def getInfo(info):
    """
    解析出策略的名称、品种、时间尺度、策略id、用户id
    :param info:
    :return:
    """
    s1,strategy_id,user_id=info.split("&")
    symbol=s1.split("_")[-2]
    timeframe=s1.split("_")[-1]
    name=s1[0:s1.find(symbol)-1]
    return(name,symbol,timeframe,strategy_id,user_id)


def getScore(filePath,symbol,timeframe,start,end):
    """
    回测&评定绩效
    :param filePath:
    :return:
    """

    print("当前运行策略：",filePath)
    print("测试起始时间：%s;测试终止时间：%s"%(start,end))
    try:
        "读取策略代码"
        input=open(filePath,"r")
        code=input.read()
    #    with codecs.open(filePath, 'r', 'utf-8') as input:
     #       code = input.read()
        input.close
        backtest = bt.Backtesting()
        backtest.set_code(code)
        config = dict(user="test", name='test', symbols=[symbol], time_frame=timeframe, start_time=start,
                      end_time=end)
        backtest.set_config(**config)
        backtest.start()
        performance = backtest.get_performance()  # 获取策略的各项指标
        mark=performance.optimize_info["夏普比率"]
      #  profit=backtest.get_profit_records()  # 获取浮动收益曲线

      #  print("profit_info:\n%s"% profit)
    #    print('optimize_info:\n%s' % performance.optimize_info)
        # print(backtest.get_parameters())  # 获取策略中的参数（用于优化）
        # print(performance._dict_name)
        # for k, v in performance.__dict__.items():
        #     print("%s\n%s" % (k, v))
        # print('trade_info:\n%s' % performance._manager.trade_info)
        # print('trade_summary:\n%s' % performance.trade_summary)
    #    print('trade_details:\n%s' % performance.trade_details)
        # print(translator.dumps(performance._manager.trade_info))
        # print(translator.dumps(performance.trade_details))
        # print('strategy_summary:\n%s' % performance.strategy_summary)
    except:
        output=open("G:/评测错误日志/评测错误日志.txt","a")
        info = traceback.format_exc()
        output.write("出错脚本：%s；错误原因：\n %s\n"% (filePath, info))
        output.close()

        print("代码运行出错\n")
        return(-99999)
    else:
        print("得分：",mark,"\n")
        return(mark)

def getPerfomance():
    """
    计算所有选手成绩
    """
    global strategyPath,scorePath,stperiod,enperiod,userInfo

    score=[]#记录选手得分
    count=0

    list=os.listdir(strategyPath)
    for line in list:
        score.append({})
        info=line.replace(".py","")
        name,symbol,timeframe,strategy_id,user_id=getInfo(info)
        score[count]["name"]=name
        score[count]["symbol"]=symbol
        score[count]["timeframe"]=timeframe
        score[count]["strategy_id"]=strategy_id
        score[count]["user_id"]=user_id
        score[count]["nickname"]=userInfo[user_id]["nickname"]
        score[count]["fdt_id"]=userInfo[user_id]["fdt_id"]
        score[count]["email"]=userInfo[user_id]["email"]
        score[count]["phone"]=userInfo[user_id]["phone"]
        filePath=strategyPath+"/"+line

        #五点取样，测评该策略分数
        mark=0
        for i in range(len(stperiod[symbol])):
            start=stperiod[symbol][i]
            end=enperiod[symbol][i]
            mark+=0.2*getScore(filePath,symbol,timeframe,start,end)
        score[count]["mark"]=mark

        count+=1

    #按得分排序并输出到文件
    score.sort(key=operator.itemgetter("mark"),reverse=True)  #默认为升序， reverse=True为降序
    output=open(scorePath+"/成绩排名.csv","a")
    output.write("nickname,mark,strategy_name,symbol,timeframe,fdt_id,email,phone\n")
    for rank in score:
        output.write("%s,%s,%s,%s,%s,%s,%s,%s"%(rank["nickname"],rank["mark"],rank["name"],rank["symbol"],rank["timeframe"],rank["fdt_id"],rank["email"],rank["phone"]))
    output.close()

#codeDownload()
# userInfoDownload()
setTestPeriod()
getUserInfo()
getPerfomance()