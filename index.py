import os 
import flask
import math
import time
import random
import http.client
import pandas as pd
import logging
import io
import urllib
import json
import re
import yfinance as yf
import sys 
import datetime
import numpy as np
from IPython.core.display import HTML
from datetime import date, timedelta , datetime
from pandas_datareader import data as pdr
from flask import Flask, request, render_template
from concurrent.futures import ThreadPoolExecutor
from flask_googlecharts import LineChart
from flask_googlecharts import GoogleCharts
from openpyxl import load_workbook

os.environ['AWS_SHARED_CREDENTIALS_FILE']='./cred'

import boto3

yf.pdr_override()		
today = date.today()
decadeAgo = today - timedelta(days=3652)
data = pdr.get_data_yahoo('NFLX', start=decadeAgo, end=today)
data['Signal']=0
data['Type']=0

update1=[]
data1=[]
open1=[]
high1=[]
low1=[]
close1=[]
date1=[]
make1=[]
update_date1=[]
signal1=[]
type1=[]

for i in range(len(data)):   
    realbody=math.fabs(data.Open[i]-data.Close[i])
    bodyprojection=0.3*math.fabs(data.Close[i]-data.Open[i])
    
	# Hammer
    if data.High[i] >= data.Close[i] and data.High[i]-bodyprojection <= data.Close[i] and data.Close[i] > data.Open[i] and data.Open[i] > data.Low[i] and data.Open[i]-data.Low[i] > realbody:
        data.at[data.index[i], 'Signal'] = 1 
        data.at[data.index[i], 'Type'] = 1
        
    # Inverted Hammer
    if data.High[i] > data.Close[i] and data.High[i]-data.Close[i] > realbody and data.Close[i] > data.Open[i] and data.Open[i] >= data.Low[i] and data.Open[i] <= data.Low[i]+bodyprojection:
        data.at[data.index[i], 'Signal'] = 1
        data.at[data.index[i], 'Type'] = 2
                
    # Hanging Man
    if data.High[i] >= data.Open[i] and data.High[i]-bodyprojection <= data.Open[i] and data.Open[i] > data.Close[i] and data.Close[i] > data.Low[i] and data.Close[i]-data.Low[i] > realbody:
        data.at[data.index[i], 'Signal'] = 2
        data.at[data.index[i], 'Type'] = 3
        
    # Shooting Star
    if data.High[i] > data.Open[i] and data.High[i]-data.Open[i] > realbody and data.Open[i] > data.Close[i] and data.Close[i] >= data.Low[i] and data.Close[i] <= data.Low[i]+bodyprojection:
        data.at[data.index[i], 'Signal'] = 2
        data.at[data.index[i], 'Type'] = 4
 
for i in range(len(data)):
	if data.Signal[i]!=0:
		value1 = data.Open[i]
		open1 = np.append(open1,value1).tolist()
		value2 = data.High[i]
		high1 = np.append(high1,value2).tolist()
		value3 = data.Low[i]
		low1 = np.append(low1,value2).tolist()
		value4 = data.Close[i]
		close1 = np.append(close1,value4).tolist()
		value5 = data.index[i]
		date1 = np.append(date1,value5).tolist()
		value6 = data.Signal[i]
		signal1 = np.append(signal1,value6).tolist()
		value7 = data.Type[i]
		type1 = np.append(type1,value7).tolist()
		
open1=str(open1)
high1=str(high1)
low1=str(low1)
close1=str(close1)
signal1=str(signal1)
type1=str(type1)

for i in range(len(date1)):
	iso_date = date1[i].date()
	update_date=iso_date.isoformat()
	update_date1.append(update_date)

update_date1 = tuple(update_date1)
update_date2 = str(update_date1)

data1.append(open1)
data1.append(high1)
data1.append(low1)
data1.append(close1)
data1.append(update_date1)
data1.append(type1)

app = Flask(__name__)
charts=GoogleCharts(app)

def doRender(tname, values={}):
	if not os.path.isfile(os.path.join(os.getcwd(),'templates/' +tname)):
		return render_template('landing_page.htm')
	return render_template(tname, **values)
		
###########################################################################################################
########################     Getting Values from the User from 'form.htm' page  ###########################
###########################################################################################################
@app.route('/analysis', methods =['POST'])
def analysisHandler():
	import http.client
	if request.method == 'POST':
		res = request.form.get('resources')
		mini = request.form.get('minhistory')
		shots = request.form.get('shots')
		service = request.form.get('service')
		signal = request.form.get('signal')
		n_resources = int(res)
		runs = [value for value in range(n_resources)]
		if signal == "Buy":
			Tsignal = "1";
		else:
			Tsignal = "2";
		if res == '' or mini == '' or shots == '' or service == '' or signal == '':
			return doRender('results.htm',{'note': 'Please specify a number for each group!'}) 
		else :
			if(service == "Lambda"): ######## AWS Lambda Scalable Service Execution Block ########### 
				def getpage(id):
					awsC = http.client.HTTPSConnection("XXXXX-api.us-east-1.amazonaws.com")
					json_obj = '{"key1":"'+open1+'","key2":"'+high1+'","key3":"'+low1+'","key4":"'+close1+'","key5":"'+mini+'","key6":"'+shots+'","key7":"'+Tsignal+'","key8":"'+signal1+'","key9":"'+update_date2+'","key10":"'+type1+'"}'
					awsC.request("POST","/default/cw_lambda",json_obj)
					response = awsC.getresponse()
					data = response.read().decode('utf-8')
					res=json.loads(data)
					return res	
				def getpages():
					with ThreadPoolExecutor() as executor:
						results=executor.map(getpage,runs)
					return results
					
				initial_time = time.time()
				risk_analysis = getpages()
				totaltime=time.time()-initial_time
				cost = 1024*0.0000166667*totaltime
				invocationcost = ((float(res)*0.20))/10000000
				totalcost= cost +invocationcost
				
			else:	######## AWS EC2 Scalable Service Execution Block ########## 
				ec2 = boto3.resource('ec2',region_name='us-east-1')
				initial_time = time.time()
				instances = ec2.create_instances(
					ImageId ='ami-03a67edcfc6e055ee', #Amazon Linux 2 AMI - Kernel 5.10
					MinCount = n_resources,
					MaxCount = n_resources,
					InstanceType ='t2.micro',
					KeyName = 'academy-ssh-only',
					SecurityGroups = ['academy-ssh-SG'],
					)
				for i in instances:
					i.wait_until_running()	
					i.load()
				instance_id = ec2.instances.filter(Filters=[{'Name':'instance-state-name', 'Values':['running']}])
				id_list=[]
				for instance in instance_id:
					id_list.append(instance.id)
				dictionary_ec2 = {'Minhistory':mini,'shots':shots,'Signal':Tsignal,'Signal_Type':signal1}
				dictionary_ec2_url =urllib.parse.urlencode(dictionary_ec2)
				
				for i in id_list:
					host = i
					inst = http.client.HTTPConnection(host)
					inst.request("POST","/vipul_ec2_code.py",+dictionary_ec2_url)
					response = inst.getresponse()
					results1 = response.read().decode('utf-8')
					results.append(results1)
					
				totaltime=time.time()-initial_time
				cost = 0.0116*60*60*totaltime*float(res)
				totalcost= cost
				
			avg95_type1=[]
			avg99_type1=[]
			avg95_type2=[]
			avg99_type2=[]
			mean_95_type1=[]
			mean_99_type1=[]
			mean_95_type2=[]
			mean_99_type2=[]
			
			for i in risk_analysis:
				make1.append(i)
			new=[]
			for i in range(len(make1)):
				new1 = json.loads(make1[I].replace("'","'"))
				new.append(new1)
	
			list_95_type1 = []
			list_99_type1 = []
			list_95_type2 = []
			list_99_type2 = []
			date_flat1=[]
			date_flat2=[]
			for i in range(len(new)):
				list_95_t1 = new[i][0]['95%']
				list_99_t1 = new[i][0]['99%']
				list_95_t2 = new[i][1]['95%']
				list_99_t2 = new[i][1]['99%']
				list_95_type1.append(list_95_t1)
				list_99_type1.append(list_99_t1)
				list_95_type2.append(list_95_t2)
				list_99_type2.append(list_99_t2)
				date_flat1 = new[i][0]['Date']
				date_flat2 = new[i][1]['Date']

			main_list1 = [np.array(x) for x in list_95_type1]
			new_95_list_type1= [np.mean(k) for k in zip(*main_list1)]
			new_95_list_type1_str = [str(i) for i in new_95_list_type1]
				
			main_list2 = [np.array(x) for x in list_99_type1]
			new_99_list_type1= [np.mean(k) for k in zip(*main_list2)]
			new_99_list_type1_str = [str(i) for i in new_99_list_type1]
				
			main_list3 = [np.array(x) for x in list_95_type2]
			new_95_list_type2= [np.mean(k) for k in zip(*main_list3)]
			new_95_list_type2_str = [str(i) for i in new_95_list_type2]
				
			main_list4 = [np.array(x) for x in list_99_type2]
			new_99_list_type2= [np.mean(k) for k in zip(*main_list4)]
			new_99_list_type2_str = [str(i) for i in new_99_list_type2]
		
			for i in range(len(new)):
				avg_95_type1 = sum(new[i][0]['95%'])/len(new[i][0]['95%'])
				avg_99_type1 = sum(new[i][0]['99%'])/len(new[i][0]['99%'])
				avg_95_type2 = sum(new[i][1]['95%'])/len(new[i][1]['95%'])
				avg_99_type2 = sum(new[i][1]['99%'])/len(new[i][1]['99%'])
				avg95_type1.append(avg_95_type1)
				avg99_type1.append(avg_99_type1)
				avg95_type2.append(avg_95_type2)
				avg99_type2.append(avg_99_type2)

			mean_95_type1 = sum(avg95_type1)/len(avg95_type1)
			mean_99_type1 = sum(avg99_type1)/len(avg99_type1)
			mean_95_type2 = sum(avg95_type2)/len(avg95_type2)
			mean_99_type2 = sum(avg99_type2)/len(avg99_type2)
			Buy_95_avg = (mean_95_type1+mean_95_type2)/2
			Buy_99_avg = (mean_99_type1+mean_99_type2)/2

			if signal == "Buy" :
				percentage_table = pd.DataFrame({"95% Risk Value of Hammer Signal" : mean_95_type1, "99% Risk Value of Hammer Signal" : mean_99_type1, "95% Risk Value of Inverted Hammer Signal" : mean_95_type2, "99% Risk Value of Inverted Hammer Signal" : mean_99_type2,"Run Time":totaltime, "Cost":totalcost}, index=[1])
				percentage_table = percentage_table.T
				risk_final1 = pd.DataFrame({
					"Date" : date_flat1,
					"95% Risk Values on Hammer Signal": new_95_list_type1,
					"99% Risk Values on Hammer Signal": new_99_list_type1})
				risk_final2 = pd.DataFrame({
					"Date" : date_flat2,	
					"95% Risk Values on Inverted Hammer Signal": new_95_list_type2,
					"99% Risk Values on Inverted Hammer Signal": new_99_list_type2})
				audit_dict = {"Service":service,"Resources":res,"History":res,"Shots":shots,"Signal":signal,"95% Type1":mean_95_type1,"99% Type1":mean_99_type1,"95% Type2":mean_95_type2,"99% Type2":mean_99_type2,"runtime":totaltime,"cost":totalcost}
				audit_pd = pd.DataFrame(audit_dict,index=list(range(len(audit_dict['Service']))))
			else:
				percentage_table = pd.DataFrame({"95% Risk Value of Shooting Star Signal" : mean_95_type1, "99% Risk Value of Shooting Star Signal" : mean_99_type1, "95% Risk Value of Hanging Man Signal" : mean_95_type2, "99% Risk Value of Hanging Man Signal" : mean_99_type2,"Cost":totalcost},index=[1])	
				percentage_table = percentage_table.T	
				risk_final1 = pd.DataFrame({
					"Date" : date_flat1,
					"95% Risk Values on Hanging Man Signal": new_95_list_type1,
					"99% Risk Values on Hanging Man Signal": new_99_list_type1})
				risk_final2 = pd.DataFrame({
					"Date" : date_flat2,
					"95% Risk Values on Shooting Star Signal": new_95_list_type2,
					"99% Risk Values on Shooting Star": new_99_list_type2})
				audit_dict = {"Service":service,"Resources":res,"History":res,"Shots":shots,"Signal":signal,"95% Type1":mean_95_type1,"99% Type1":mean_99_type1,"95% Type2":mean_95_type2,"99% Type2":mean_99_type2,"runtime":totaltime,"cost":totalcost}
				audit_pd = pd.DataFrame(audit_dict,index=list(range(len(audit_dict['Service']))))
				
			s3 = boto3.client('s3')
			history_file = s3.get_object(Bucket='ccvipulbucket',Key='history.xlsx')
			audit = history_file['Body'].read()
			writer = pd.ExcelWriter(io.BytesIO(audit),engine='openpyxl')
			writer.book = load_workbook(io.BytesIO(audit))
			writer.sheets =dict((ws.title,ws) for ws in writer.book.worksheets)
			read = pd.read_excel(io.BytesIO(audit))
			audit_pd.to_excel(writer,sheet_name="Sheet1",index=False,startrow=len(read)+1)
			writer.save()
			
			return doRender('results.htm',{'note':HTML(percentage_table.to_html(header='True',index='True')),'data':','.join(new_95_list_type1_str)+'|'+','.join(new_99_list_type1_str) +'|'+','.join(new_95_list_type2_str) +'|'+','.join(new_99_list_type2_str),'note1':HTML(risk_final1.to_html(header='True',index='True')),'note2':HTML(risk_final2.to_html(header='True',index='True'))})
				
	return 'Should not ever get here'

@app.route('/audit', methods =['POST'])
def auditHandler():	
	if request.method == 'POST':
		s3 = boto3.client('s3')
		data = s3.get_object(Bucket='<bucketname>', Key='history.xlsx')
		contents = data['Body'].read()
		reader = pd.read_excel(io.BytesIO(contents))
		return doRender('history.htm', {'note':HTML(reader.to_html())})

@app.route('/terminate', methods =['POST'])
def terminateHandler():
	if request.method == 'POST':
		ec2 = boto3.resource('ec2',region_name='us-east-1')
		id_list=[]
		instance_id = ec2.instances.filter(Filters=[{'Name':'instance-state-name', 'Values':['running']}])
		for instance in instance_id:
			id_list.append(instance.id)
		ec2.instances.filter(InstanceIds=id_list).terminate()
		return doRender('landing_page.htm',{'note':"Instance Terminated"})

@app.route('/cacheavoid/<name>')
def cacheavoid(name):
	#file exists?
	if not os.path.isfile( os.path.join(os.getcwd(), 'static/'+name) ):
		return('No such file' + os.path.join(os.getcwd(), 'static/'+name))
	f = open(os.path.join(os.getcwd(),'static/'+name))
	contents = f.read()
	f.close()
	return contents 
	
# catch all other page requests - doRender checks if a page is available(shows it) or not (index)
@app.route('/', defaults={'path' : ''})
@app.route('/<path:path>')
def mainPage(path):
	return doRender(path)

@app.errorhandler(500)
def server_error(e):
	logging.exception('ERROR!')
	return """
	An error occurred: <pre>{}</pre>
	""".format(e), 500

if __name__ == '__main__' :
	app.run(host='127.0.0.1',port=8080, debug=True)
	
	
