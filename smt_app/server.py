#coding=utf-8
'''
Created on 2014-10-31

@author: Administrator
'''
from web import httpserver
from main import application

httpserver.runsimple(application, ('0.0.0.0', 8080))