#coding=utf-8
'''
Created on 2014-11-1

@author: aveenzhou
'''
import urllib3
import json
import hashlib
import hmac
import urllib
import urllib2
from conf import *
http=urllib3.PoolManager(500)
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
    
    dict_data=json.loads(data)
    return dict_data


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
    if req_args.get('productId',None):
        req_args['productId']=str(req_args['productId'])
    if req_args.get('productIds',None):
        req_args['productIds']=str(req_args['productIds'])
    
    req_url='/'.join((OPEN_API_URL,urlPath))
    res=http.request('POST',req_url,req_args)#POST GET有长度限制
    data=res.data
    
    return data