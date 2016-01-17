# -*- coding: utf-8 -*-
base = 100000
symbols = ['EURUSD']
start = '2015-01-01'
end = '2015-12-01'
timeframe = 'M30'

def handle(slowlength=20, fastlength=10, lots=100):
	def max(price,len):
		max = 0
		for index in range(len):
			if price[index+1]>max:
				max = price[index+1]
		return(max)
	def min(price,len):
		min = 99999999
		for index in range(len):
			if price[index+1]<min:
				min = price[index+1]
		return(min)

	print('%s:(h:%s,l:%s,ATR:%s)' % (barnum, high[0], low[0], ATR()))
	if barnum > slowlength:
		symbol = symbols[0]
		position = marketposition.get(symbol,None)
		if position == 0:
			if close[0]>=max(high,slowlength):
				buy(symbol,lots)
			if close[0]<=min(low,slowlength):
				short(symbol,lots)
		elif marketposition[symbol] > 0:
			if close[0]<=min(low,fastlength):
				sell(symbol,lots)
		elif marketposition[symbol] < 0:
			if close[0]>=max(high,fastlength):
				cover(symbol,lots)
