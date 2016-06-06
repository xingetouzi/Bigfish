# -*- coding:utf-8 -*-
def init():
	bollingerLengths=33
	trendLiqLength=41
	upnumStdDevs=1
	dnnumStdDevs=0.9
	swingPrcnt1=0.9
    swingPrcnt2=1.8
	atrLength=34
	swingTrendSwitch=20
	trendLok=2
	choppyLength=30
    swingpoint=4
	
	cmiVal=0
	buyEasierDay=0
	sellEasierDay=0
	trendLokBuy=0
	trenLokSsell=0
	keyOfDay=0
	swingBuyPt=0
	swingSellPt=0
	trendBuyPt=0
	trendSellPt=0
	swingProtStop=0
	Atrs=0
    Mas=0
    MasH=0
    MasL=0
	entranceprice=0
	liqprice=0
	currTrade=0
	HH=0
	LL=0
    N=1
def handle():    
    Boll=Bolling(bollingerLengths,Close,offset=1)
    Atrs=ATR(atrLength,offset=1)
    Mas=MA(trendLiqLength,Close,offset=1)
    MasH=MA(trendLok,High,offset=1)
    MasL=MA(trendLok,Low,offset=1)
	swingProtStop=swingpoint*Atrs
    Export(LTT)
    LTT[0] = round(0.9*Cap.available/2500,0)
    if (Boll is not None):
		trendBuyPt=MA(bollingerLengths,Close,offset=1)+upnumStdDevs*Boll.std
		trendSellPt=MA(bollingerLengths,Close,offset=1)-dnnumStdDevs*Boll.std
		buyEasierDay=0
		sellEasierDay=0
		keyOfDay=(High[1]+Low[1]+Close[1])/3
		if (Close[1]>keyOfDay):
			buyEasierDay = 0
			sellEasierDay = 1
		else:
			buyEasierDay = 1
			sellEasierDay = 0
		if(buyEasierDay == 1):
			swingBuyPt = Open[0] + swingPrcnt1*Atrs
			swingSellPt = Open[0] - swingPrcnt2*Atrs
    	if(sellEasierDay == 1):
			swingBuyPt = Open[0] + swingPrcnt2*Atrs
			swingSellPt = Open[0] - swingPrcnt1*Atrs
		trendLokBuy = MasL
		trendLokSell = MasH
		swingBuyPt = max(swingBuyPt,trendLokBuy)
		swingSellPt = min(swingSellPt,trendLokSell)
		liqprice=Mas
		HH=Highest(choppyLength,High,offset=1)
		LL=Lowest(choppyLength,Low,offset=1)
		if (HH!=LL):
			cmiVal=100*abs(Close[1]-Close[choppyLength])/(HH-LL)
		if (cmiVal<swingTrendSwitch and cmiVal!=0):
			if (MarketPosition!=1 and High[0]>swingBuyPt and Low[0]<swingBuyPt):
				Buy(Symbol,LTT[0])
				entranceprice=Close[0]
				currTrade=1
			if (MarketPosition!=-1 and High[0]>swingSellPt and Low[0]<swingSellPt):
				SellShort(Symbol,LTT[0])
				entranceprice=Close[0]
				currTrade=1
		else:
			if (MarketPosition!=1 and Close[0]>trendBuyPt and Low[0]<trendBuyPt and (High[0]-liqprice)*(Low[0]-liqprice)>0 and Open[1]<trendBuyPt and Open[2]<trendBuyPt):
				Buy(Symbol,LTT[0])
				currTrade=2
			if (MarketPosition!=-1 and High[0]>trendSellPt and Close[0]<trendSellPt and (High[0]-liqprice)*(Low[0]-liqprice)>0 and Open[1]>trendSellPt and Open[2]>trendSellPt):
				SellShort(Symbol,LTT[0])
				currTrade=2
                print(Datetime[0],trendSellPt)
			if (MarketPosition==1 and High[0]>liqprice and Low[0]<liqprice and currTrade==2):
				Sell(Symbol,CurrentContracts)
			if (MarketPosition==-1 and High[0]>liqprice and Low[0]<liqprice and currTrade==2):
				BuyToCover(Symbol,CurrentContracts)
			if (MarketPosition==1 and High[0]>entranceprice-swingProtStop and Low[0]<entranceprice-swingProtStop and currTrade==1):
				Sell(Symbol,CurrentContracts)
			if (MarketPosition==-1 and High[0]>entranceprice+swingProtStop and Low[0]<entranceprice+swingProtStop and currTrade==1):
				BuyToCover(Symbol,CurrentContracts)