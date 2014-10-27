﻿#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''

import urllib3
import json
import hashlib
import hmac
import web
import urllib
import urllib2

OPEN_API_URL="http://gw.api.alibaba.com/openapi"

AUTH_URL="http://gw.api.alibaba.com/auth/authorize.htm"

APP_KEY="1067520"
APP_SECRET="PUpMcxJ5om"

TOKEN_URL="https://gw.api.alibaba.com/openapi/http/1/system.oauth2/getToken/"+APP_KEY
LOCAL_APP_URL="http://127.0.0.1:8080/index"

def get_alibba_auth_url():
    auth_args={
               "client_id":APP_KEY,
               "site":"aliexpress",
               "redirect_uri":LOCAL_APP_URL,
               "state":'test'
               }
    
    def create_sign_str(args):
        '''
                        构造认证请求签名字符串
        '''
        keys=args.keys()
        sorted_keys=sorted(keys)
        temp=[]
        for key in sorted_keys:
            temp.append(''.join((key,str(auth_args[key]))))
        
        sign_str=''.join(temp)
        encry_sign_str=hmac.new(APP_SECRET, sign_str, digestmod=hashlib.sha1).hexdigest().upper() #hmac_sha1加密算法
        return encry_sign_str
    auth_args['_aop_signature']=create_sign_str(auth_args)
    
    url= '?'.join((AUTH_URL,urllib.urlencode(auth_args)))
    return url

def get_token_by_code(code):
    req_args={
              "grant_type":"authorization_code",
              "need_refresh_token":"true",
              "client_id":APP_KEY,
              "client_secret":APP_SECRET,
              "redirect_uri":LOCAL_APP_URL,
              "code":code
              }
    #have 3 methods for request url with post
    params = urllib.urlencode(req_args)
#1
    res =urllib.urlopen(TOKEN_URL, params)
    data=res.read()
#2
#    req=urllib2.Request(TOKEN_URL,params)
#    res = urllib2.urlopen(req)
    
#3
#    http=urllib3.PoolManager()
#    res=http.request('POST',TOKEN_URL,req_args,encode_multipart=False)
#    data=res.data
    
    json_data=json.loads(data)
    return json_data


def get_alidata_by_api(api_name,
                       access_token,
                       protoc_format="param2",
                       api_version="1",
                       api_namspace="aliexpress.open",
                       **api_args):
    '''
        根据接口名和access_token以及接口具体调用相关的参数,
        调用接口,其它参数默认
    '''
    req_args=dict(
                  access_token=access_token,
                  **api_args
                  )
    urlPath='/'.join((protoc_format,api_version,api_namspace,api_name,APP_KEY))
    def create_sign_str():
        '''
                            构造API签名字符串
        '''
        sorted_keys=sorted(req_args.keys())
        temp=[]
        for key in sorted_keys:
            temp.append(''.join((key,str(req_args[key]))))
        req_args_str=''.join(temp)
        sign_str=''.join((urlPath,req_args_str))
        encry_sign_str=hmac.new(APP_SECRET, sign_str, digestmod=hashlib.sha1).hexdigest().upper() #hmac_sha1加密算法

        return encry_sign_str
    
    req_args['_aop_signature']=create_sign_str()
    
    req_url='/'.join((OPEN_API_URL,urlPath))
    
    http=urllib3.PoolManager()
    res=http.request('GET',req_url,req_args)
    data=res.data
    
    return json.loads(data)
    
    
        
web.config.alibba_auth_url=get_alibba_auth_url()


########################################
urls=(
      '/auth','Auth',
      '/index','Index'
      )

class Auth(object):
    def GET(self):
        redirect_url=web.config.alibba_auth_url
        web.seeother(redirect_url, absolute=True)
    

class Index(object):
    def GET(self):
        input= web.input()
        code=input.get('code','') #临时授权码
        if not code:
            return web.seeother('/auth')
            
        token_data=get_token_by_code(code)    
        
        web.config.token_data=web.storage(token_data)
#        token_data的的字段有
#        u'aliId
#        u'resource_owner
#        u'access_token
#        u'expires_in
#        u'refresh_token
#        u'refresh_token_timeout
        if web.config.token_data.get('error',None):
            return web.seeother('/auth')
        
        access_token=web.config.token_data.access_token
        res_data=get_alidata_by_api(
                           "api.getProductGroupList",
                           access_token
                           )
        
        
        return  res_data
        



app = web.application(urls, globals())
application=app.wsgifunc()

if __name__=="__main__":
    app.run()

    
    
    
    